import os
import io
from PIL import Image
from ai_api_server.logger import logger
from ai_api_server.config import BUCKET_PREFIX, BUCKET_NAME, GCP_CREDENTIAL, GCS_URL_PREFIX
from google.cloud import storage

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_CREDENTIAL


def upload_image_to_gcs(image: Image.Image, dest_file_name: str) -> str:
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"{BUCKET_PREFIX}/{dest_file_name}")

    # Convert the PIL Image to bytes
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    # Upload the bytes to GCS
    blob.upload_from_file(image_bytes, content_type="image/png")
    logger.info(f"Success-upload_gcs-image_path:{BUCKET_PREFIX}/{dest_file_name}" )
    return f"{BUCKET_PREFIX}/{dest_file_name}"


def download_image_from_gcs(source_img_path) -> Image.Image:
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(source_img_path)

    # Download the blob as bytes
    image_bytes = blob.download_as_bytes()

    # Create a PIL Image from the downloaded bytes
    return Image.open(io.BytesIO(image_bytes))
