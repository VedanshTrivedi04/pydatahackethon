import os
import logging
from pathlib import Path

logger = logging.getLogger("engine.core.storage")

# Root directory for storing temporary artifacts locally
LOCAL_STORAGE_DIR = Path("d:/pydata2.0/pydatahackethon/.temp_artifacts")

def save_artifact(
    job_id: str,
    tenant_id: str,
    file_name: str,
    file_content: bytes,
    content_type: str = "application/octet-stream"
) -> str:
    """
    Saves an artifact. Under the hood, this mock client stores files locally
    in the workspace under `.temp_artifacts/`.
    Returns a string identifier/key (e.g., path) which Dev 3's real implementation
    can map to S3/MinIO.
    """
    try:
        # Create directory path
        target_dir = LOCAL_STORAGE_DIR / tenant_id / job_id
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_file = target_dir / file_name
        
        # Write bytes
        target_file.write_bytes(file_content)
        
        # S3 key format
        s3_key = f"{tenant_id}/{job_id}/{file_name}"
        logger.info(f"Artifact saved locally: {target_file} (Key: {s3_key})")
        
        # Return path / key that serves as reference
        return s3_key
        
    except Exception as e:
        logger.error(f"Failed to save artifact {file_name}: {str(e)}")
        raise e

def get_artifact(s3_key: str) -> bytes:
    """
    Helper to fetch a locally saved artifact.
    """
    file_path = LOCAL_STORAGE_DIR / s3_key
    if not file_path.exists():
        raise FileNotFoundError(f"Artifact {s3_key} not found at {file_path}")
    return file_path.read_bytes()
