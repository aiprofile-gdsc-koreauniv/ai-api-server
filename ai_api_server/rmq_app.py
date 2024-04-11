import asyncio
import aio_pika
import json
from datetime import datetime

from aiormq import DeliveryError
from logger import logger
from config import RMQ_HOST, RMQ_PORT, RMQ_QUEUE
CONCUR_LIMIT = 1

async def process_message(
    message: aio_pika.IncomingMessage,
) -> None:
    async with message.process(ignore_processed=True, reject_on_redelivered=True):
        try:
            time_str = datetime.now().strftime("%Y%m%d-%H:%M:%S") 
            json_dict = json.loads(message.body)
            
            print(time_str, "header:", message.headers,"parsed:", json_dict)
            
            await asyncio.sleep(1)
            if json_dict["msg"] == "q":
                # @ TODO @@ Inner catch does not on occur outer exception
                # @ TODO @@ Issue publish_message not working 
                if message.headers["x-retry-count"] > 3:
                    await message.reject(requeue=False)
                else:
                    message.headers["x-retry-count"] += 1
                    await publish_message(message.channel, message.body, message.headers["x-retry-count"])
                    await message.reject(requeue=False)
        except Exception as e:
            await message.reject(requeue=False)


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