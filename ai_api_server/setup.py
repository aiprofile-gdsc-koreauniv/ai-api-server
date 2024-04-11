import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
import torch
from ai_api_server.cloud_utils import download_face_model
from ai_api_server.face_preprocess import HeadSegmenter, FaceDetector, face_detector, head_segmenter

from ai_api_server.rmq_app import setup_queue
from face_preprocess import FaceDetector

async def on_startup(loop):
    # TODO: Preprocess Model Load
    global face_detector, head_segmenter
    download_face_model()
    face_detector = FaceDetector('yolov8n-face.onnx')
    head_segmenter = HeadSegmenter('cuda')
    task = asyncio.create_task(setup_queue(loop))


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