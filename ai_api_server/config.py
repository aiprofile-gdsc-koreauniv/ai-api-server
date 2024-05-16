import json
import os
import datetime 
from dotenv import load_dotenv
import socket

# load .env
load_dotenv()

mySecret = os.environ.get('MySecret')

current_date = datetime.date.today()
FORMAT_DATE = current_date.strftime("%Y-%m-%d")

# @@ Config ############################
WEBUI_URL = os.environ.get('WEBUI_URL')
API_BASE_URL = os.environ.get('API_BASE_URL')
TIMEOUT_SEC = 240
LOG_PATH = os.environ.get('LOG_PATH')
PRESET_DIR = os.environ.get('PRESET_DIR')
BUCKET_PREFIX = os.environ.get('BUCKET_PREFIX')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
GCP_CREDENTIAL = os.environ.get('GCP_CREDENTIAL')
GCS_URL_PREFIX="https://storage.cloud.google.com"
CONFIG_KEY = os.environ.get('CONFIG_KEY')
ROUND_MASK_PATH = os.environ.get('ROUND_MASK_PATH')
MASK_PATH = os.environ.get('MASK_PATH')
FRAME_PATH = "frames"
ROUND_MASK_PATH="frame/round_mask.png"
MASK_PATH="frame/mask.png"
BATCH_NO=int(os.environ.get('BATCH_NO'))
HOST_NAME = socket.gethostname() + "-" + os.getcwd()
RMQ_HOST = os.environ.get('RMQ_HOST')
RMQ_PORT = int(os.environ.get('RMQ_PORT'))
RMQ_QUEUE = os.environ.get('RMQ_QUEUE')
RMQ_USER = os.environ.get('RMQ_USER')
RMQ_PWD = os.environ.get('RMQ_PWD')
POS_PROMPT = os.environ.get('POS_PROMPT')
NEG_PROMPT = os.environ.get('NEG_PROMPT')
CONTROLNET_WEIGHTING = json.loads(os.environ.get('CONTROLNET_WEIGHTING'))


if not os.path.exists(PRESET_DIR):
    os.makedirs(PRESET_DIR+"/male/white/red")
    os.makedirs(PRESET_DIR+"/male/white/blue")
    os.makedirs(PRESET_DIR+"/male/white/white")
    os.makedirs(PRESET_DIR+"/male/black/red")
    os.makedirs(PRESET_DIR+"/male/black/blue")
    os.makedirs(PRESET_DIR+"/male/black/white")
    os.makedirs(PRESET_DIR+"/female/white/red")
    os.makedirs(PRESET_DIR+"/female/white/blue")
    os.makedirs(PRESET_DIR+"/female/white/white")
    os.makedirs(PRESET_DIR+"/female/black/red")
    os.makedirs(PRESET_DIR+"/female/black/blue")
    os.makedirs(PRESET_DIR+"/female/black/white")

def test():
    return WEBUI_URL
