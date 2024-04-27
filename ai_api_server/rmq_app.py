import asyncio
import traceback
import aio_pika
import json
import datetime
from api import webui_t2i
import cloud_utils
from cloud_utils import db_client
import face_preprocess
import utils
from dto import ProcessErrorParam, ProcessRequestParam, ProcessResponseParam
from aiormq import DeliveryError
from logger import logger
from config import BUCKET_PREFIX, RMQ_HOST, RMQ_PORT, RMQ_PWD, RMQ_QUEUE, RMQ_USER, WEBUI_URL
CONCUR_LIMIT = 1

async def process_message(
    message: aio_pika.IncomingMessage,
) -> None:
    async with message.process(ignore_processed=True, reject_on_redelivered=True):
        logger.debug(f"RECV: {message.body}")
        try:
            json_body = json.loads(message.body)
            print(json_body, "requestAt:", json_body['requestedAt'])
            req_payload = ProcessRequestParam.validate(json_body)
            req_id = req_payload.id
            # TODO: override webui params

            # GCS get images
            succ, src_imgs = cloud_utils.download_image_from_gcs(req_payload.imagePaths)
            if not succ:
                logger.error(f"Error::id:{req_id}::detail:DownloadFail")
                raise Exception("DownloadFail")

            # Preprocess images
            processed_images =  face_preprocess.preprocess_image(images=src_imgs, 
                                                bg_color=req_payload.param.background,
                                                face_detector=face_preprocess.face_detector, 
                                                head_segmenter=face_preprocess.head_segmenter)

            sampled_img_str_list = utils.sample_imgs([utils.encodeImg2Base64(img) for img in processed_images])
            succ, result = await webui_t2i(gender=req_payload.param.gender, 
                                        background=req_payload.param.background, 
                                        ip_imgs=sampled_img_str_list, 
                                        reactor_img=utils.sample_one_img(sampled_img_str_list))
            if not succ:
                logger.error(f"Error::id:{req_id}::detail:{result}")
                raise Exception(f"{result}")

            # TODO: postprocess image
            #   X Image Merge

            # GCS upload images
            img_names = [f"{req_id}/{i}.png" for i in range(1,len(result)+1)]
            upload_succ = cloud_utils.upload_image_to_gcs(result, img_names)
            if not upload_succ:
                logger.error(f"Error:{req_id}::detail:UploadFail")
                raise Exception("UploadFail")

            # DB response
            FORMAT_DATE = datetime.date.today().strftime("%Y-%m-%d")
            response = ProcessResponseParam(id=req_id, 
                                   email=req_payload.email, 
                                   imagePaths=[ f"{BUCKET_PREFIX}/{FORMAT_DATE}/{img}" for img in img_names],
                                   requestedAt=req_payload.requestedAt,
                                   createdAt=datetime.datetime.now(),
                                   title=req_payload.title,
                                   userId=req_payload.userId)
            await db_client.collection("profile_responses").document(req_id).set(response.dict())
            logger.info(f"Success:{req_id}")

        except Exception as e:
            await message.reject(requeue=False)
            if req_id is not None:
                logger.error(f"Error:{req_payload.id}::detail:{e} : {traceback.format_exc()}")
                response = ProcessErrorParam(id=req_payload.id, 
                                            createdAt=datetime.datetime.now(),
                                            error=str(e) if e is not None else "Unknown",)
                await db_client.collection("profile_errors").document(req_id).set(response.dict())
                await utils.requestPostAsyncData("https://ntfy.sh/horangstudio-engine",
                    payload=f"ProcessException id: {req_payload.id} 🔥\ndetail: {e}".encode(encoding='utf-8'))
            else:
                logger.error(f"Error:InvalidMsgFmt::detail:{message.body} : {traceback.format_exc()}")
                await utils.requestPostAsyncData("https://ntfy.sh/horangstudio-engine",
                    payload=f"ProcessException id: unknown 🔥\ndetail: {e}".encode(encoding='utf-8'))
        except:
            await message.reject(requeue=False)
            await utils.requestPostAsyncData("https://ntfy.sh/horangstudio-engine",
                payload=f"ProcessError id: {req_id} 🔥\ndetail: unknown".encode(encoding='utf-8'))
        # @ TODO @@ Inner catch does not on occur outer exception
        # @ TODO @@ Issue publish_message not working 



async def publish_message(channel: aio_pika.abc.AbstractRobustChannel,body: str, retry: int) -> None:
        try:
            print(body, retry)
            confirm = await channel.default_exchange.publish(
                aio_pika.Message(body=body, 
                                headers={"x-retry-count": retry}, 
                                delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                routing_key="ai-profile",
            )
            print("requeue:", confirm)
        except DeliveryError as e:
            print(f"Delivery of  failed with exception: {e}")
        except TimeoutError:
            print(f"Timeout occured for")
        else:
            print("Unhandled error")



async def setup_queue(loop: asyncio.AbstractEventLoop) -> None:
    try:
        connection = await aio_pika.connect_robust(
            host=RMQ_HOST,
            port=RMQ_PORT,
            login=RMQ_USER,
            password=RMQ_PWD,
            loop=loop
        )
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=CONCUR_LIMIT)
        queue = await channel.declare_queue(RMQ_QUEUE, auto_delete=False, durable=True)
        logger.info(f"Connected to RMQ: {RMQ_HOST}:{RMQ_PORT}:{RMQ_QUEUE}")
        await queue.consume(process_message)

    except Exception as e:
        datetime_str = datetime.now().strftime("%Y%m%d-%H:%M:%S")
        logger.error(f"{datetime_str} SetupRMQ: {e} {traceback.format_exc()}")

    try:
        await asyncio.Future()
    finally:
        logger.info(f"Closing connection to RMQ: {RMQ_HOST}:{RMQ_PORT}:{RMQ_QUEUE}")
        await connection.close()


if __name__ == "__main__":
    asyncio.run(setup_queue())