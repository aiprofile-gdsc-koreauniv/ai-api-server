import logging 
from config import LOG_PATH


# @@ Logging ############################

logging.basicConfig(level=logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.FileHandler(LOG_PATH, mode="a")
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
