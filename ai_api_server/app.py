import os
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
import face_preprocess
from api import webui_t2i
from logger import logger
import setup
import utils as utils
import cloud_utils as cloud_utils
from dto import BaseResponse, ProcessRequestParam, ProcessData, ProcessResponse, StatusData, StatusResponse, UpdateUrlParam
from config import BUCKET_PREFIX, WEBUI_URL
import config as config
from face_preprocess import preprocess_image
import traceback

app = FastAPI(
    title="AI-Profile-Diffusion-Server",
    description="ai-profile 프로젝트의 AI-API Server입니다.\n\n 서비스 URL: [호랑이 사진관](https://horangstudio.com)",
    contact={
        "name": "Kyumin Kim",
        "email": "dev.kyoomin@gmail.com",
    },
    lifespan=setup.lifespan
)

# @@ APIHandler ############################
@app.get("/api/health", tags=["API"])
def healthCheck()-> BaseResponse:
    return JSONResponse(
            status_code=200,
            content=StatusResponse(message="ai-api-server is running", 
                                data=StatusData(webui_status=True,
                                                webui_url = WEBUI_URL, 
                                                time = datetime.now().strftime("%Y%m%d-%H:%M:%S")).dict()
                                ).dict())

@app.get("/api/status", tags=["API"])
async def checkStatus():
    webui_status = await utils.checkSuccessGetAsync(f"{WEBUI_URL}/user")
    if webui_status:
        return JSONResponse(
                status_code=200,
                content=StatusResponse(message="ai-api-server is connected to webui", 
                                        data=StatusData(webui_status=True,
                                                        webui_url = WEBUI_URL,
                                                        time = datetime.now().strftime("%Y%m%d-%H:%M:%S")).dict()
                ).dict())
    else:
        return JSONResponse(
                status_code=200,
                content=StatusResponse(message="ai-api-server is NOT connected to webui", 
                                        data=StatusData(webui_status=False,
                                                        webui_url = WEBUI_URL,
                                                        time = datetime.now().strftime("%Y%m%d-%H:%M:%S"))
                ).dict())

@app.post("/api/process", tags=["API"])
async def process(req_payload: ProcessRequestParam):
    try:
        req_id = req_payload.id
        # TODO: override webui params
        succ, src_imgs = cloud_utils.download_image_from_gcs(req_payload.imagePaths)
        if not succ:
            logger.error(f"Error::id:{req_id}::detail:DownloadFail")
            raise Exception("DownloadFail")

        processed_images =  preprocess_image(images=src_imgs, 
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
        img_names = [f"{req_id}/{i}.png" for i in range(1,len(result)+1)]
        cloud_utils.upload_image_to_gcs(result, img_names)

        return JSONResponse(
                status_code=200,
                content=ProcessResponse(message=f"Success created for ID:{req_id}", 
                                        data=ProcessData(id=req_id, 
                                                         image_paths=[f"{BUCKET_PREFIX}/{img_name}" for img_name in img_names]).dict()
                ).dict())
    except Exception as e:
        logger.error(f"Error::id:{req_id}::detail:{e} :: : {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"error":str(e)})
    except:
        if os.getenv("ENV") == "prod":
            requests.post("https://ntfy.sh/horangstudio-engine",
                data=f"ProcessError id: {req_id} 🔥\ndetail: swap-face".encode(encoding='utf-8'))
        return JSONResponse(status_code=500, content={"error":"UnknownError"})

@app.patch("/api/url", tags=["Config"])
async def update_url(item: UpdateUrlParam):
    global WEBUI_URL
    new_url = item.url
    config.WEBUI_URL = new_url
    WEBUI_URL = new_url
    return {"message": "WEBUI_URL updated successfully", "detail":{"1": config.WEBUI_URL, "2": WEBUI_URL}}

@app.get("/api/url", tags=["Config"])
async def get_url():
    return {"message": "WEBUI_URL", "detail": {"1": config.WEBUI_URL, "2": WEBUI_URL}}

# @@ Run ############################

def run():
    import os 
    port = int(os.getenv("PORT", "9001"))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)


