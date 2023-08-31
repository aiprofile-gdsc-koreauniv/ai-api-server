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
    univ: str


class UploadImgParam(BaseModel):
    id: str
    idx: int
    image: str


class DownloadImgParam(BaseModel):
    image_path: str


class APIPresetParam(BaseModel):
    is_male: bool
    is_black: bool


class UpdateUrlParam(BaseModel):
    url: str
    k: str
    
class AuthorizedParam(BaseModel):
    k: str


class ProcessRequestParam(BaseModel):
    id: str
    param: APIPresetParam
    image_paths: List[str]


class ProcessResponse(BaseModel):
    id: str
    image_paths: List[str]