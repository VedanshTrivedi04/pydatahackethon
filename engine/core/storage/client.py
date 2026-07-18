"""
MinIO / S3 Storage Client.

Provides a simplified interface for uploading files and generating
presigned URLs using boto3.
"""

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Any, Tuple
from io import BytesIO

from engine.config.settings import get_settings
from engine.utils.exceptions import BusinessValidationError
from engine.utils.logging import get_logger

logger = get_logger(__name__)


class StorageClient:
    """Wrapper around boto3 for MinIO / S3 operations."""

    def __init__(self) -> None:
        self.settings = get_settings().minio
        
        # Configure boto3 to work with MinIO (path style addressing is required)
        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.settings.endpoint_url,
            aws_access_key_id=self.settings.access_key,
            aws_secret_access_key=self.settings.secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1", # Dummy region for MinIO
        )
        self.bucket = self.settings.bucket
        
        # Ensure bucket exists (in a real production app, this might be done via terraform)
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Create the bucket if it doesn't exist."""
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                logger.info("storage.bucket_create", bucket=self.bucket)
                self.s3.create_bucket(Bucket=self.bucket)
            else:
                logger.error("storage.bucket_check_failed", error=str(e))
                # We don't raise here to prevent startup crashes if MinIO is temporarily down,
                # but uploads will fail later.

    def upload_file(
        self,
        s3_key: str,
        content: bytes | str,
        content_type: str = "application/octet-stream"
    ) -> int:
        """
        Upload data to MinIO.

        Args:
            s3_key: Destination path in the bucket.
            content: The file data (bytes or str).
            content_type: MIME type of the file.

        Returns:
            The size of the uploaded file in bytes.
        """
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
            
        size = len(content_bytes)

        try:
            self.s3.upload_fileobj(
                BytesIO(content_bytes),
                self.bucket,
                s3_key,
                ExtraArgs={"ContentType": content_type}
            )
            logger.info("storage.file_uploaded", key=s3_key, size=size)
            return size
        except ClientError as e:
            logger.error("storage.upload_failed", key=s3_key, error=str(e))
            raise BusinessValidationError(f"Failed to upload artifact: {str(e)}")

    def generate_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """
        Generate a temporary presigned URL for downloading a file.

        Args:
            s3_key: The path in the bucket.
            expires_in: Expiration time in seconds (default 1 hour).

        Returns:
            The presigned HTTP URL.
        """
        try:
            url = self.s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": s3_key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error("storage.presigned_url_failed", key=s3_key, error=str(e))
            raise BusinessValidationError(f"Failed to generate download URL: {str(e)}")
