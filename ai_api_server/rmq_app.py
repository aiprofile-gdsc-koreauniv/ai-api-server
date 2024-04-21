import asyncio
import aio_pika
import json
import datetime
from api import AlwaysOnScripts, ControlNetArgs, ReactorArgs, ScriptArgs, T2IArgs
import cloud_utils
from cloud_utils import db_client
from face_preprocess import preprocess_image, head_segmenter, face_detector
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
            # TODO: preprocess
            #   O Download Images -> Select Pose? IP?
            #   X Detect, Seg Face
            #   O Convert to base64
            #   Send to WEBUI
            succ, src_imgs = cloud_utils.download_image_from_gcs(req_payload.imagePaths)
            if not succ:
                logger.error(f"Error:{req_id}::detail:DownloadFail")
                raise Exception("DownloadFail")

            processed_images =  preprocess_image(src_imgs, face_detector, head_segmenter)

            # TODO: preprocess selection logic
            selected_img = processed_images[0]
            selected_img.save("selected_img.png")
            image_str = utils.encodeImg2Base64(selected_img)

            t2i_url = WEBUI_URL + "/sdapi/v1/txt2img"
            controlnet_args = ScriptArgs(args=[ControlNetArgs(image=image_str)])
            reactor_args = ScriptArgs(args=ReactorArgs(src_img=image_str, swap_in_generated_img=False).to_list())
            script_config = AlwaysOnScripts(ControlNet=controlnet_args, reactor=reactor_args)
            t2i_payload = T2IArgs(prompt="((realistic, photo by canon film camera)), portrait of a korean man, detailed skin, portrait:1.5, ((white shirts)), ID photo, upper body, ((simple crimson background:1.5)), looking at viewer, neck, black hair, medium-shot, upper body, canon eos, crewneck t shirt",
                                    negative_prompt="tattoo, phone, small person, Drawings, abstract art, cartoons, surrealist painting, conceptual drawing, graphics, (low resolution:1.4), ((blurry:1.3)), (worst quality:1.3), (low quality:1.3), huge breasts, (NSFW:1.5), blurry, messy drawing, hand, finger, naked, nude,(long body :1.3), (mutation, poorly drawn :1.2),text font ui, error, long neck, blurred, lowers, low res, bad shadow, disappearing thigh, old photo, low res, black and white, black and white filter, colorless, nipple:1.5, muscle, text:1.5, text symbol:1.5, cap, hat, helmet, logo:1.5, grey, strap, cartoon,CGI, render, illustration, painting, drawing logo, stripe pattern, hand, backpack:1.7, necklace:1.3, turtleneck:1.3, muffler:1.3, scalf:1.3, stripes pattern, polka dots pattern, plaid pattern, checkered pattern, chevron pattern, cardigan:1.3, uniform, apron:1.5, vest:1.5, hand, see through, sheer top",
                                    alwayson_scripts=script_config
                                    )
            succ, response = await utils.requestPostAsync(t2i_url, t2i_payload.dict())
            if not succ:
                logger.error(f"Error:{req_id}::detail:RequestFail")
                return {"error": response}
            images = [utils.decodeBase642Img(img_str) for img_str in response["images"]]

            # TODO: postprocess image
            #   X Image Merge
            #   O Upload Image
            img_names = [f"{req_id}/{i}.png" for i in range(1,len(images)+1)]
            upload_succ = cloud_utils.upload_image_to_gcs(images, img_names)
            if not upload_succ:
                logger.error(f"Error:{req_id}::detail:UploadFail")
                raise Exception("UploadFail")
            
            # DB
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
                logger.error(f"Error:{req_payload.id}::detail:{e}")
                response = ProcessErrorParam(id=req_payload.id, 
                                            createdAt=datetime.datetime.now(),
                                            error=str(e) if e is not None else "Unknown",)
                await db_client.collection("profile_errors").document(req_id).set(response.dict())
                await utils.requestPostAsyncData("https://ntfy.sh/horangstudio-engine",
                    payload=f"ProcessException id: {req_payload.id} 🔥\ndetail: {e}".encode(encoding='utf-8'))
            else:
                logger.error(f"Error:InvalidMsgFmt::detail:{message.body}")
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

        consumer = await queue.consume(process_message)
    except Exception as e:
        datetime_str = datetime.now().strftime("%Y%m%d-%H:%M:%S")
        logger.exception(f"{datetime_str} SetupRMQ", exc_info=e)

    try:
        await asyncio.Future()
    finally:
        print("Closing RMQ Connection")
        await connection.close()


if __name__ == "__main__":
    asyncio.run(setup_queue())