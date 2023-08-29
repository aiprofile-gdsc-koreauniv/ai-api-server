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


def loadPresetImage(is_male: bool, is_black: bool, color: int) -> Image.Image:
    target_dir = PRESET_DIR  # 해당 폴더 경로로 바꿔주세요

    if is_male:
        target_dir =os.path.join(target_dir, "male")
    else:
        target_dir =os.path.join(target_dir, "female")
    
    if is_black:
        target_dir =os.path.join(target_dir, "black")
    else:
        target_dir =os.path.join(target_dir, "white")
    
    if color == 0:
        target_dir =os.path.join(target_dir, "red")
    elif color == 1:
        target_dir =os.path.join(target_dir, "blue")
    elif color == 2:
        target_dir =os.path.join(target_dir, "white")
    else:
        logger.error("Error-"+"load_image-" + "InvalidColorIdx:" + str(color))
        raise HTTPException(status_code=400, detail={"message":"Invalid Color", "idx":color})

    # 모든 .png 파일 찾기
    png_files = []
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.lower().endswith(".png"):
                png_files.append(os.path.join(root, file))

    # .png 파일이 없는 경우
    if not png_files:
        print("No .png files found.")
        logger.error("Error-"+"load_image-" + "NoPresetImage:" + str(color))
        raise HTTPException(status_code=500, detail={"message":"No Preset Image","is_male:" : is_male, "is_black":is_black, "color":color })
    else:
        # 랜덤으로 하나의 .png 파일 선택
        selected_png = random.choice(png_files)
        
        # 선택한 .png 이미지 열기
        try:
            img = Image.open(selected_png)
        except Exception as e:
            logger.error("Error-"+"load_image-" + "CanNotOpenImg:" + selected_png)
            raise HTTPException(status_code=500, detail={"message":"CanNotOpenImg","path:" : selected_png })
    return img


def encodeImg2Base64(img: Image.Image) -> str:
    image_bytes = io.BytesIO()
    img.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    # Encode the bytes to Base64
    return base64.b64encode(image_bytes.read()).decode("utf-8")

