import os
import io
import PIL
from logger import logger
from config import BUCKET_PREFIX, BUCKET_NAME, GCP_CREDENTIAL, GCS_URL_PREFIX
from google.cloud import storage

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_CREDENTIAL


def upload_image_to_gcs(image: PIL.Image.Image, dest_file_name: str) -> str:
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"{BUCKET_PREFIX}/{dest_file_name}")

    # Convert the PIL Image to bytes
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    # Upload the bytes to GCS
    blob.upload_from_file(image_bytes, content_type="image/png")
    logger.info(f"Success-upload_gcs-url:{BUCKET_PREFIX}/{dest_file_name}" )
    return f"{GCS_URL_PREFIX}/{BUCKET_NAME}/{BUCKET_PREFIX}/{dest_file_name}"

