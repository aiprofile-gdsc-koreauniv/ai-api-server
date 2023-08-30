import os
import io
from PIL import Image
from typing import List
import httpx
import base64
from logger import logger
from config import TIMEOUT_SEC, PRESET_DIR
import random
from fastapi import HTTPException


# @@ Utils ############################
def convertStr2Img(img_str):
    # Base64 문자열에서 데이터 추출
    image_data = img_str.split(',')[1]
    image_bytes = base64.b64decode(image_data)

    # BytesIO를 사용하여 이미지 데이터를 메모리에 로드
    image_io = io.BytesIO(image_bytes)

    # PIL 이미지 객체 생성
    return Image.open(image_io)


def convertStrList2Img(img_str_list: List[str]) -> List[Image.Image]:
    res = []
    for img_str in img_str_list:
        res.append(convertStr2Img(img_str))
    return res


async def requestGetAsync(url):
    async with httpx.AsyncClient() as client:
        try:
            # Send async GET request to the external API
            response = await client.get(url)

            # Check if the request was successful (status code 200)
            if response.status_code // 100 == 2:
                data = response.json()  # Parse JSON response
                return data
            else:
                return {"error": "Failed to retrieve data from external API"}
        except httpx.RequestError as e:
            return {"error": f"Request error: {e}"}


async def requestPostAsync(url, payload):
    async with httpx.AsyncClient() as client:
        try:
            # Send async POST request to the external API
            response = await client.post(url, json=payload, timeout=httpx.Timeout(TIMEOUT_SEC))

            # Check if the request was successful (status code 200)
            if response.status_code // 100 == 2:
                data = response.json()  # Parse JSON response
                return (True, data)
            else:
                logger.error("Error-"+"POST-" + "url:" + url + "-" +"detail:"+str(response))
                return (False, response.json())
        except httpx.RequestError as e:
            logger.error("Error-"+"POST-" + "url:" + url + "-" +"detail:"+str(e))
            return (False, e)


def loadPresetImages(is_male: bool, is_black: bool, univ: str, cnt:int ) -> List[Image.Image]:
    target_dir = PRESET_DIR  # 해당 폴더 경로로 바꿔주세요
    target_dir_white = PRESET_DIR
    
    result = []
    
    if cnt == 0:
        logger.error(f"Error - load_image - InvalidCnt: {cnt}")
        raise HTTPException(status_code=400, detail={"message":"Invalid cnt", "cnt":cnt})

    if is_male:
        target_dir =os.path.join(target_dir, "male")
        target_dir_white =os.path.join(target_dir, "male")
    else:
        target_dir =os.path.join(target_dir, "female")
        target_dir_white =os.path.join(target_dir, "female")
    
    if is_black:
        target_dir =os.path.join(target_dir, "black")
        target_dir_white =os.path.join(target_dir, "black")
    else:
        target_dir =os.path.join(target_dir, "white")
        target_dir_white =os.path.join(target_dir, "white")
    
    if univ == "korea":
        target_dir =os.path.join(target_dir, "red")
        target_dir_white =os.path.join(target_dir, "red")
    elif univ == "yonsei":
        target_dir =os.path.join(target_dir, "blue")
        target_dir_white =os.path.join(target_dir, "blue")
    else:
        logger.error(f"Error - load_image - InvalidUnivIdx: {univ}")
        raise HTTPException(status_code=400, detail={"message":"Invalid Univ", "idx":univ})

    # 모든 .png 파일 찾기
    png_files = []
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.lower().endswith(".png"):
                png_files.append(os.path.join(root, file))

    for root, dirs, files in os.walk(target_dir_white):
        for file in files:
            if file.lower().endswith(".png"):
                png_files.append(os.path.join(root, file))

    # .png 파일이 없는 경우
    if not png_files:
        logger.error(f"Error - load_image - NoPresetImage: male={is_male}, b={is_black}, univ={univ}")
        raise HTTPException(status_code=400, detail={"message":"No Preset Image","is_male:" : is_male, "is_black":is_black, "univ": univ })
    else:
        # 랜덤으로 하나의 .png 파일 선택
        try:
            result_img_path = []
            dbg_len = len(png_files)
            for _ in range(cnt):
                selected_png = random.choice(png_files)
                result_img_path.append(selected_png)
                png_files.remove(selected_png)
        except Exception as e:
            logger.error(f"Error - load_image - NotEnoughPreset: requested {cnt} has {dbg_len} - detail: {e}")
            raise HTTPException(status_code=400, detail={"message":"TooManyImgRequested","cnt:" : cnt })
    
        # 선택한 .png 이미지 열기
        try:
            for _ in range(cnt):
                result.append(Image.open(result_img_path.pop(0)))
        except Exception as e:
            logger.error(f"Error - load_image - CanNotOpenImg: {selected_png} - detail: {e}")
            raise HTTPException(status_code=500, detail={"message":"CanNotOpenImg","path:" : selected_png })
    return result


def encodeImg2Base64(img: Image.Image) -> str:
    image_bytes = io.BytesIO()
    img.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    return base64.b64encode(image_bytes.read()).decode("utf-8")


def decodeBase642Img(base64_str: str)-> Image.Image:
    decoded_bytes = base64.b64decode(base64_str)
    image_bytes_io = io.BytesIO(decoded_bytes)
    return Image.open(image_bytes_io)