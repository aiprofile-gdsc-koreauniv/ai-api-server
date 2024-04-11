import os
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
from api import AlwaysOnScripts, ControlNetArgs, ReactorArgs, ScriptArgs, T2IArgs
from logger import logger
from setup import lifespan
import utils as utils
import cloud_utils as cloud_utils
from dto import BaseResponse, ProcessRequestParam, ProcessData, ProcessResponse, StatusData, StatusResponse, UpdateUrlParam
from config import BUCKET_PREFIX, WEBUI_URL
import config as config
from face_preprocess import head_segmenter, face_detector, preprocess_image

app = FastAPI(
    title="AI-Profile-Diffusion-Server",
    description="ai-profile 프로젝트의 AI-API Server입니다.\n\n 서비스 URL: [호랑이 사진관](https://horangstudio.com)",
    contact={
        "name": "Kyumin Kim",
        "email": "dev.kyoomin@gmail.com",
    },
    lifespan=lifespan
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
        # TODO: preprocess
        #   O Download Images -> Select Pose? IP?
        #   X Detect, Seg Face
        #   O Convert to base64
        #   Send to WEBUI
        succ, src_imgs = cloud_utils.download_image_from_gcs(req_payload.image_paths)
        if not succ:
            logger.error(f"Error::id:{req_id}::detail:DownloadFail")
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
            logger.error(f"Error::id:{req_id}::detail:RequestFail")
            return {"error": response}
        images = [utils.decodeBase642Img(img_str) for img_str in response["images"]]

        # TODO: postprocess image
        #   X Image Merge
        #   O Upload Image
        img_names = [f"{req_id}/{i}.png" for i in range(1,len(images)+1)]
        cloud_utils.upload_image_to_gcs(images, img_names)

        return JSONResponse(
                status_code=200,
                content=ProcessResponse(message=f"Success created for ID:{req_id}", 
                                        data=ProcessData(id=req_id, 
                                                         image_paths=[f"{BUCKET_PREFIX}/{img_name}" for img_name in img_names]).dict()
                ).dict())
    except Exception as e:
        logger.error(f"Error::id:{req_id}::detail:{e}")
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


