import os
import io
from typing import List
from PIL import Image
from ai_api_server.logger import logger
from ai_api_server.config import BUCKET_PREFIX, BUCKET_NAME, FORMAT_DATE, GCP_CREDENTIAL, GCS_URL_PREFIX
from google.cloud import storage

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "test.json"


def upload_image_to_gcs(images: List[Image.Image], dest_file_names: List[str]) -> bool:
    try:
        storage_client = storage.Client()
        # bucket = storage_client.bucket(BUCKET_NAME)
        bucket = storage_client.bucket("2024-profile")
        
        for image, dest_file_name in zip(images, dest_file_names):
            # Convert the PIL Image to bytes
            blob = bucket.blob(f"{BUCKET_PREFIX}/{dest_file_name}")
            image_bytes = io.BytesIO()
            image.save(image_bytes, format="PNG")
            image_bytes.seek(0)

            # Upload the bytes to GCS
            blob.upload_from_file(image_bytes, content_type="image/png")
        print("Done")
        return True
    except Exception as e:
        print("ee", e)
        logger.error(f"Error-upload_gcs:{BUCKET_PREFIX}/{dest_file_names}::detail:{e}")
        return False



def download_image_from_gcs(source_img_paths: List[str]) -> tuple[bool, List[Image.Image]| None]:
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        result = []
        for source_img_path in source_img_paths:
            # Get the blob
            blob = bucket.blob(source_img_path)

            # Download the blob as bytes
            image_bytes = blob.download_as_bytes()
            img = Image.open(io.BytesIO(image_bytes))
            
            # Create a PIL Image from the downloaded bytes
            result.append(img)
            
        return True, result
    except Exception as e:
        logger.error(f"Error-download_gcs:{source_img_paths}::detail:{e}")
        return False, None

