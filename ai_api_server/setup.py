import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_api_server.rmq_app import setup_queue

async def on_startup(loop):
    # TODO: Preprocess Model Load
    task = asyncio.create_task(setup_queue(loop))


def on_shutdown():
    # TODO: Preprocess Model Cleanup
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await on_startup(loop)
    yield
    on_shutdown()