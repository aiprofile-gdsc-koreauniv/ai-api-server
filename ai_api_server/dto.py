import datetime
from pydantic import BaseModel
from typing import List, Optional


# @@ Dto ############################
class APIPresetParam(BaseModel):
    is_male: bool
    is_black: bool
    is_blonde: bool

class UpdateUrlParam(BaseModel):
    url: str
    k: str

class AuthorizedParam(BaseModel):
    k: str


class BaseResponse (BaseModel):
    message: str = ""
    data: dict = {}

class ProcessData(BaseModel):
    id: str
    image_paths: List[str]

class ProcessResponse(BaseResponse):
    data : ProcessData

class StatusData(BaseModel):
    webui_status: bool
    webui_url: str
    time: str

class StatusResponse(BaseResponse):
    data: StatusData

class OverrideParam(BaseModel):
    prompt: Optional[str] 
    negative_prompt: Optional[str] 
    # alwayson_scripts: Optional[]  # TODO
    sampler_name: Optional[str] 
    batch_size: Optional[int] 
    cfg_scale: Optional[int] 
    seed: Optional[int] 
    seed_enable_extras: Optional[bool] 
    seed_resize_from_h: Optional[int] 
    seed_resize_from_w: Optional[int] 
    steps: Optional[int] 
    height: Optional[int] 
    width: Optional[int] 
    comments: Optional[dict] 
    disable_extra_networks: Optional[bool] 
    do_not_save_grid: Optional[bool] 
    do_not_save_samples: Optional[bool] 
    enable_hr: Optional[bool] 
    hr_negative_prompt: Optional[str] 
    hr_prompt: Optional[str] 
    hr_resize_x: Optional[int] 
    hr_resize_y: Optional[int] 
    hr_scale: Optional[int] 
    hr_second_pass_steps: Optional[int] 
    hr_upscaler: Optional[str] 
    n_iter: Optional[int] 
    override_settings: Optional[dict] 
    override_settings_restore_afterwards: Optional[bool] 
    restore_faces: Optional[bool] 
    s_churn: Optional[float] 
    s_min_uncond: Optional[int] 
    s_noise: Optional[float] 
    s_tmax: Optional[int] 
    s_tmin: Optional[float] 
    script_args: Optional[list] 
    script_name: Optional[str] 
    styles: Optional[list] 
    subseed: Optional[int] 
    subseed_strength: Optional[int] 
    tiling: Optional[bool] 

class ProcessRequestParam(BaseModel):
    id: str
    # param: APIPresetParam
    email: str
    userId: str
    imagePaths: List[str]
    requestedAt: str
    title: str
    override_webui: Optional[OverrideParam]

class ProcessResponseParam(BaseModel):
    id: str
    email: str
    imagePaths: List[str]
    requestedAt: str
    createdAt: datetime.datetime
    title: str
    userId: str

class ProcessErrorParam(BaseModel):
    id: str
    error: str
    createdAt: datetime.datetime
