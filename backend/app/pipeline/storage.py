import os
import shutil
import logging

import boto3
from botocore.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None and settings.R2_ACCOUNT_ID:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _s3_client


def store_clip(local_path: str, job_id: str, segment_index: int) -> str:
    """
    Store a clip file.
    - If R2 is configured: upload to Cloudflare R2, return public URL.
    - Otherwise: copy to media/clips/ and return a local serving URL.
    """
    filename = f"{job_id}/clip_{segment_index:03d}.mp4"

    s3 = _get_s3()
    if s3 and settings.R2_PUBLIC_URL:
        # Upload to Cloudflare R2
        r2_key = f"clips/{filename}"
        s3.upload_file(
            local_path,
            settings.R2_BUCKET_NAME,
            r2_key,
            ExtraArgs={"ContentType": "video/mp4"},
        )
        public_url = f"{settings.R2_PUBLIC_URL.rstrip('/')}/{r2_key}"
        logger.info(f"Uploaded to R2: {public_url}")
        return public_url
    else:
        # Local dev: copy to media/clips/
        dest_dir = os.path.join(settings.MEDIA_DIR, "clips", job_id)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, f"clip_{segment_index:03d}.mp4")
        shutil.copy2(local_path, dest_path)
        public_url = f"{settings.BASE_URL}/media/clips/{job_id}/clip_{segment_index:03d}.mp4"
        logger.info(f"Stored locally: {public_url}")
        return public_url


def cleanup_temp(job_id: str):
    """Delete temp files after processing to save disk space."""
    temp_dir = os.path.join(settings.TEMP_DIR, job_id)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"Cleaned up temp: {temp_dir}")
