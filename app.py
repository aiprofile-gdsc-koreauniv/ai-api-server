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
from logger import logger
import utils
import cloud_utils
from models import FaceListPayload, FaceSwapPayload, PresetParam, UploadImgParam, DownloadImgParam, getBuildFaceModelPayload
from config import WEBUI_URL


app = FastAPI()


# @@ APIHandler ############################
@app.get("/api/status/")
async def checkStatus():
    current_time = datetime.now()
    time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    webui_status = await utils.simpleRequestGetAsync(f"{WEBUI_URL}/user")
    if webui_status:
        return JSONResponse(
            status_code=200,
            content={"status": "200", "webui_status": "Connected", "datetime": time_str}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"status": "500", "webui_status": "Not Connected", "datetime": time_str}
        )


@app.post("/test/webui/build")
async def getFaceModel(item: FaceListPayload):
    result = await buildFaceModel(req_id="123id", img_str_list=item.img_list)
    return {"result": result}


@app.post("/test/webui/swap")
async def getSwappedFace(item: FaceSwapPayload):
    result = await swapFaceApi(req_id="123id", face_model=item.face_model, src_img=item.src_img)
    return {"result": result}


@app.get("/test/img/preset")
async def getImagePreset(item: PresetParam):
    result_imgs = utils.loadPresetImages(is_male=item.is_male, is_black=item.is_black, univ=item.univ, cnt=1)
    image_bytes = io.BytesIO()
    result_imgs[0].save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return StreamingResponse(content=image_bytes, media_type="image/png")


@app.post("/test/img/upload")
async def uploadImage(item: UploadImgParam):
    decoded_bytes = base64.b64decode(item.image)
    image_bytes_io = io.BytesIO(decoded_bytes)
    pil_image = Image.open(image_bytes_io)
    
    cloud_utils.upload_image_to_gcs(pil_image, f"{item.id}/{item.idx}.png")
    return {"status":"done"}


@app.get("/test/img/download")
async def downloadImage(item: DownloadImgParam):
    result_img = cloud_utils.download_image_from_gcs(item.image_path)
    image_bytes = io.BytesIO()
    result_img.save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return StreamingResponse(content=image_bytes, media_type="image/png")


@app.post("/api/img/process")
async def getBuildFaceModel(item: getBuildFaceModelPayload):
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

    preset_img_list_kor = utils.loadPresetImages(is_male=item.param.is_male, is_black=item.param.is_black, univ="korea", cnt=2)
    preset_img_list_yon = utils.loadPresetImages(is_male=item.param.is_male, is_black=item.param.is_black, univ="yonsei", cnt=1)
    preset_img_list = preset_img_list_kor + preset_img_list_yon
    
    start_time_swap = time.time()
    for idx in range(3):
        result_img_str = await swapFaceApi(req_id=item.id, face_model=face_model, src_img=preset_img_list[idx])
        result_img = utils.decodeBase642Img(result_img_str)

        # @@ TODO : OpenCV -> result_img modification
        # @@ 0 idx : crimson fix
        # @@ 1 idx / 2 idx : tuple(korea, yonsei)
        # @@ FrameFolder -> dockerfile fix / Load Frame / Concat frame&img

        file_url = cloud_utils.upload_image_to_gcs(result_img, f"{item.id}/{idx}.png")
        result_urls.append(file_url)
        logger.info(f"{idx+1}/3 Done!")
    end_time_swap = time.time()
    
    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f"Done id: {item.id}")
    logger.info(f"Build time: {(end_time_build-start_time_build):.2f} seconds")
    logger.info(f"Swap time: {(end_time_swap-start_time_swap):.2f} seconds")
    logger.info(f"Total time: {execution_time:.2f} seconds")
    logger.info(f"*********************")
    
    return {"id": item.id, "image_paths" : result_urls}


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


async def swapFaceApi(req_id: str, face_model: str, src_img: str)-> str:
    try:
        face_swap_url = WEBUI_URL + "/faceswaplab/swap_face"
        src_img_base64 = utils.encodeImg2Base64(src_img)
        swap_api_payload = dict({
        "image": src_img_base64,
        "units": [
                {
                    "source_face": face_model,
                    "same_gender": True,
                    "faces_index": [
                        0
                    ]
                }
            ]
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


class ErrorResponse(BaseModel):
    detail: str


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail":"Internal server error", "exception": exc}
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
