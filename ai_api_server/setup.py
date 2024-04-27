import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import torch
from cloud_utils import download_face_model
import face_preprocess
from rmq_app import setup_queue

async def on_startup(loop):
    download_face_model()
    face_preprocess.face_detector = face_preprocess.FaceDetector('yolov8n-face.onnx')
    face_preprocess.head_segmenter = face_preprocess.HeadSegmenter('cuda')
    asyncio.create_task(setup_queue(loop))


def on_shutdown():
    global face_detector, head_segmenter
    del face_detector, head_segmenter
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await on_startup(loop)
    yield
    on_shutdown()