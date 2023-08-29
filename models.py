from enum import Enum
from typing import List
from pydantic import BaseModel


# @@ Models ############################
class Item(BaseModel):
    name: str
    content: str


class FaceListPayload(BaseModel):
    img_list: List[str]


class FaceSwapPayload(BaseModel):
    src_img: str
    face_model: str


class Status(Enum):
    READY = 1
    WEBUI_FAILURE = 2
    IN_PROGRESS = 3
    INTERNAL_ERROR = 4


class Color(Enum):
    RED = 1
    BLUE = 2
    WHITE = 3


class PresetParam(BaseModel):
    is_male: bool
    is_black: bool
    color: int


class UploadImgParam(BaseModel):
    id: str
    idx: int
    image: str


class getBuildFaceModelPayload(BaseModel):
    id: str
    idx: int
    param: PresetParam
    image_list: List[str]