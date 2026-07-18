"""Storage package exports."""

import os
import logging
from pathlib import Path

logger = logging.getLogger("engine.core.storage")

# Root directory for storing temporary artifacts locally if MinIO is not available
LOCAL_STORAGE_DIR = Path("d:/pydata2.0/pydatahackethon/.temp_artifacts")

from engine.core.storage.client import StorageClient

def save_artifact(
    job_id: str,
    tenant_id: str,
    file_name: str,
    file_content: bytes,
    content_type: str = "application/octet-stream"
) -> str:
    """
    Saves an artifact. Uploads to MinIO/S3 using StorageClient if available,
    otherwise falls back to saving locally under `.temp_artifacts/`.
    """
    try:
        # Attempt to upload to MinIO
        client = StorageClient()
        # Clean UUID formatting if strings are passed
        s3_key = f"{tenant_id}/{job_id}/{file_name}"
        client.upload_file(s3_key, file_content, content_type)
        return s3_key
    except Exception as e:
        logger.warning(
            f"Could not save to MinIO/S3 storage, falling back to local storage. Error: {str(e)}"
        )
        
        # Local fallback
        try:
            target_dir = LOCAL_STORAGE_DIR / tenant_id / job_id
            target_dir.mkdir(parents=True, exist_ok=True)
            
            target_file = target_dir / file_name
            target_file.write_bytes(file_content)
            
            s3_key = f"{tenant_id}/{job_id}/{file_name}"
            logger.info(f"Artifact saved locally (fallback): {target_file} (Key: {s3_key})")
            return s3_key
        except Exception as local_err:
            logger.error(f"Failed to save artifact locally: {str(local_err)}")
            raise local_err

def get_artifact(s3_key: str) -> bytes:
    """
    Helper to fetch a locally saved artifact.
    """
    file_path = LOCAL_STORAGE_DIR / s3_key
    if not file_path.exists():
        raise FileNotFoundError(f"Artifact {s3_key} not found at {file_path}")
    return file_path.read_bytes()

__all__ = ["StorageClient", "save_artifact", "get_artifact"]
