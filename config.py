import os
import datetime 
from dotenv import load_dotenv

# load .env
load_dotenv()

mySecret = os.environ.get('MySecret')

current_date = datetime.date.today()
FORMAT_DATE = current_date.strftime("%Y-%m-%d")

# @@ Config ############################
WEBUI_URL = os.environ.get('WEBUI_URL')
API_BASE_URL = os.environ.get('API_BASE_URL')
TIMEOUT_SEC = 120
LOG_PATH = os.environ.get('LOG_PATH')
PRESET_DIR = os.environ.get('PRESET_DIR')
BUCKET_PREFIX = os.environ.get('BUCKET_PREFIX') + "/" +FORMAT_DATE
BUCKET_NAME = os.environ.get('BUCKET_NAME')
GCP_CREDENTIAL = os.environ.get('GCP_CREDENTIAL')
GCS_URL_PREFIX="https://storage.cloud.google.com"

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
