from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import io
import uvicorn
from datetime import datetime
import base64
import time
from typing import List
from PIL import Image
from ai_api_server.logger import logger
import ai_api_server.utils as utils
import ai_api_server.cloud_utils as cloud_utils
from ai_api_server.models import FaceListPayload, FaceSwapPayload, PresetParam, UploadImgParam, DownloadImgParam, ProcessRequestParam, UpdateUrlParam, AuthorizedParam, ProcessResponse
from ai_api_server.config import WEBUI_URL, CONFIG_KEY, HOST_NAME, BATCH_NO
import ai_api_server.config as config
import requests
import random

app = FastAPI(
    title="AI-Profile-Diffusion-Server",
    description="ai-profile 프로젝트의 AI-API Server입니다.\n\n 서비스 URL: [호랑이 사진관](https://horangstudio.com)",
    contact={
        "name": "Kyumin Kim",
        "email": "dev.kyoomin@gmail.com",
    },
)


# @@ APIHandler ############################
@app.get("/api/status", tags=["API"])
async def checkStatus():
    current_time = datetime.now()
    time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    webui_status = await utils.simpleRequestGetAsync(f"{WEBUI_URL}/user")
    if webui_status:
        return JSONResponse(
            status_code=200,
            content={"status": "200", "webui_status": "Connected", "datetime": time_str, "host": HOST_NAME}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"status": "500", "webui_status": "Not Connected", "datetime": time_str}
        )


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


@app.post("/api/img/process", tags=["API"]) 
async def getBuildFaceModel(item: ProcessRequestParam)-> ProcessResponse:
    logger.info("")
    logger.info(f"*********************")
    logger.info(f"Request: {item.id} start")
    
    webui_status = await utils.simpleRequestGetAsync(f"{WEBUI_URL}/user")
    if not webui_status:
        logger.error("Error - webui_status: Not Connected")
        return JSONResponse(
            status_code=500,
            content={"status": "500", "webui_status": "Not Connected"}
        )
    
    start_time = time.time()
    
    src_imgs: List[Image.Image] = []
    result_urls: List[str] = []
    
    for image_path in item.image_paths:
        src_imgs.append(cloud_utils.download_image_from_gcs(image_path))
    logger.info(f"gcs-recieved: {len(src_imgs)} images")
    
    start_time_build = time.time()
    face_model = await buildFaceModel(req_id=item.id, img_list=src_imgs)
    end_time_build = time.time()
    
    start_time_swap = time.time()
    for idx in range(BATCH_NO):
        # Get Preset
        preset_img_list = utils.loadPresetImages(is_male=item.param.is_male, is_black=item.param.is_black, univ="korea", cnt=2, is_blonde=item.param.is_blonde) + utils.loadPresetImages(is_male=item.param.is_male, is_black=item.param.is_black, univ="yonsei", cnt=1, is_blonde=item.param.is_blonde)
        # korea-0
        portrait_img_str = await swapFaceApi(req_id=item.id, face_model=face_model, src_img=preset_img_list.pop(0), is_male=item.param.is_male)
        result_img = utils.merge_frame(image=utils.decodeBase642Img(portrait_img_str), frame=utils.getFrame(0, "red"), frame_number=0)
        file_url = cloud_utils.upload_image_to_gcs(result_img, f"{item.id}/{idx}-0.png")
        result_urls.append(file_url)
        logger.info(f"{(idx*3)+1}/{BATCH_NO*3} Done!")
        
        # korea - random set
        frame_idx = random.choice([1, 2, 3, 4])
        
        portrait_img_str = await swapFaceApi(req_id=item.id, face_model=face_model, src_img=preset_img_list.pop(0), is_male=item.param.is_male)
        result_img = utils.merge_frame(image=utils.decodeBase642Img(portrait_img_str), frame=utils.getFrame(frame_idx, "red"), frame_number=frame_idx)
        file_url = cloud_utils.upload_image_to_gcs(result_img, f"{item.id}/{idx}-1.png")
        logger.info(f"{(idx*3)+2}/{BATCH_NO*3} Done!")
        result_urls.append(file_url)
        
        # yonsei - random set
        portrait_img_str = await swapFaceApi(req_id=item.id, face_model=face_model, src_img=preset_img_list.pop(0), is_male=item.param.is_male)
        result_img = utils.merge_frame(image=utils.decodeBase642Img(portrait_img_str), frame=utils.getFrame(frame_idx, "blue"), frame_number=frame_idx)
        file_url = cloud_utils.upload_image_to_gcs(result_img, f"{item.id}/{idx}-2.png")
        logger.info(f"{(idx*3)+3}/{BATCH_NO*3} Done!")
        result_urls.append(file_url)

    
    end_time_swap = time.time()
    
    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f"Done id: {item.id}")
    logger.info(f"Build time: {(end_time_build-start_time_build):.2f} seconds")
    logger.info(f"Swap time: {(end_time_swap-start_time_swap):.2f} seconds")
    logger.info(f"Total time: {execution_time:.2f} seconds")
    logger.info(f"*********************")
    time_str = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    requests.post("https://ntfy.sh/horangstudio-engine",
        data=f"생성 완료! id:{item.id}😀\ndate:{time_str}".encode(encoding='utf-8'))
    return {"id": item.id, "image_paths" : result_urls}


@app.post("/test/webui/build", tags=["Test"])
async def getFaceModel(item: FaceListPayload):
    result = await buildFaceModel(req_id="123id", img_str_list=item.img_list)
    return {"result": result}


@app.post("/test/webui/swap", tags=["Test"])
async def getSwappedFace(item: FaceSwapPayload):
    result = await swapFaceApi(req_id="123id", face_model=item.face_model, src_img=item.src_img)
    return {"result": result}


@app.get("/test/img/preset", tags=["Test"])
async def getImagePreset(item: PresetParam):
    result_imgs = utils.loadPresetImages(is_male=item.is_male, is_black=item.is_black, univ=item.univ, cnt=100)
    image_bytes = io.BytesIO()
    result_imgs[0].save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return StreamingResponse(content=image_bytes, media_type="image/png")


@app.post("/test/img/upload", tags=["Test"])
async def uploadImage(item: UploadImgParam):
    decoded_bytes = base64.b64decode(item.image)
    image_bytes_io = io.BytesIO(decoded_bytes)
    pil_image = Image.open(image_bytes_io)
    
    cloud_utils.upload_image_to_gcs(pil_image, f"{item.id}/{item.idx}.png")
    return {"status":"done"}


@app.get("/test/img/download", tags=["Test"])
async def downloadImage(item: DownloadImgParam):
    result_img = cloud_utils.download_image_from_gcs(item.image_path)
    image_bytes = io.BytesIO()
    result_img.save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return StreamingResponse(content=image_bytes, media_type="image/png")


# @@ WebUI_API ############################
async def buildFaceModel(req_id:str, img_list: List[Image.Image]) -> str | None:
    try:
        face_build_url = WEBUI_URL + "/faceswaplab/build"
        img_str_list = []
        for img in img_list:
            img_str_list.append(utils.encodeImg2Base64(img))
        (is_succ ,response) = await utils.requestPostAsync(face_build_url, img_str_list)

        # TODO: upload intermediate base64_safetensors to bucket
        if is_succ:
            logger.info(f"Success - build_face - req_id: {req_id}")
            return response
        else:
            logger.error(f"Error - build_face - req_id: {req_id} - detail: RequestFail")
            return
    except Exception as e:
        logger.error(f"Error - build_face - req_id: {req_id} - detail: {e}")
        return
    except:
        requests.post("https://ntfy.sh/horangstudio-engine",
            data=f"ProcessError id: {req_id} 🔥\ndetail: build-face".encode(encoding='utf-8'))
        return


async def swapFaceApi(req_id: str, face_model: str, src_img: Image.Image, is_male: bool)-> str:
    try:
        if is_male: 
            gender = "man"
        else:
            gender = "woman"
        face_swap_url = WEBUI_URL + "/faceswaplab/swap_face"
        src_img_base64 = utils.encodeImg2Base64(src_img)
        swap_api_payload = dict({
        "image": src_img_base64,
        "units": [
                {
                    "source_face": face_model,
                    "same_gender": False,
                    "faces_index": [
                        0
                    ],
                    "swapping_options": {
                        "face_restorer_name": "CodeFormer",
                        "upscaler_name": "R-ESRGAN 4x+",
                        "improved_mask": False,
                        "sharpen": False
                    }
                }
            ],
            "postprocessing": {
                "upscaler_name": "Nearest",
                "scale": 1,
                "upscaler_visibility": 1,
                "inpainting_when": "After All",
                    "inpainting_options": {
                        "inpainting_denoising_strengh": 0.2,
                        "inpainting_prompt": f"Portrait of a {gender}",
                        "inpainting_negative_prompt":"blurry",
                        "inpainting_steps": 20,
                        "inpainting_sampler": "DPM++ 2M SDE Karras",
                        "inpainting_model": "Current",
                        "inpainting_seed": -1
                    }
            }
        })
        (is_succ, response) = await utils.requestPostAsync(face_swap_url, swap_api_payload)
        if is_succ:
            logger.info(f"Success-swap_face-req_id:{req_id}")
            return response["images"][0]
        else:
            logger.error("Error - swap_face - req_id: {req_id} - detail: RequestFail")
            return {"error": response}
    except Exception as e:
        logger.error(f"Error - swap_face - req_id: {req_id} - detail: {e}")
        return {"error" :e}
    except:
        requests.post("https://ntfy.sh/horangstudio-engine",
            data=f"ProcessError id: {req_id} 🔥\ndetail: swap-face".encode(encoding='utf-8'))
        return


@app.middleware("http")
async def catch_exceptions(request, call_next):
    try:
        
        return await call_next(request)
    except Exception as e:
        time_str = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        is_id = False
        idx = 0
        for i in range(len(request.headers.raw)):
            if request.headers.raw[i][0] == b'id':
                idx = i
                is_id = True
                break
        if is_id:
            requests.post("https://ntfy.sh/horangstudio-engine",
            data=f"ProcessError id:{request.headers.raw[i][1].decode('utf-8')} - date:{time_str}🔥🔥\ndetail: {e}".encode(encoding='utf-8'))
        else:
            requests.post("https://ntfy.sh/horangstudio-engine",
            data=f"ProcessError id: Unknown - date:{time_str} 🔥🔥\ndetail: {e}".encode(encoding='utf-8'))
    except:
        time_str = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        is_id = False
        idx = 0
        for i in range(len(request.headers.raw)):
            if request.headers.raw[i][0] == b'id':
                idx = i
                is_id = True
                break
        if is_id:
            requests.post("https://ntfy.sh/horangstudio-engine",
            data=f"ProcessError id:{request.headers.raw[i][1].decode('utf-8')} - date:{time_str}🔥🔥\ndetail: Unknown".encode(encoding='utf-8'))
        else:
            requests.post("https://ntfy.sh/horangstudio-engine",
            data=f"ProcessError id:{request.headers.raw[i][1].decode('utf-8')}  - date:{time_str} 🔥🔥\ndetail: {e}".encode(encoding='utf-8'))

def run():
    import os 
    port = int(os.getenv("PORT", "9001"))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)


