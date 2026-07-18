"""
Artifact Service Layer.

Coordinates uploading files to MinIO and storing their metadata in PostgreSQL.
Also generates presigned URLs for secure downloads.
"""

import hashlib
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.artifacts.repository import ArtifactRepository
from engine.core.models.artifact import Artifact
from engine.core.storage.client import StorageClient
from engine.utils.exceptions import NotFoundError, BusinessValidationError
from engine.utils.logging import get_logger

logger = get_logger(__name__)


class ArtifactService:
    """Business logic for artifact management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ArtifactRepository(session)
        self._storage = StorageClient()

    async def upload_artifact(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        file_name: str,
        content: bytes | str,
        content_type: str = "application/octet-stream",
        artifact_metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        """
        Upload a file to MinIO and save metadata in the DB.

        Args:
            job_id: The job that created this artifact.
            tenant_id: The owning tenant.
            file_name: The desired file name.
            content: The actual file contents.
            content_type: MIME type.
            artifact_metadata: Optional JSON metadata.

        Returns:
            The created Artifact DB record.
        """
        # Ensure content is bytes for checksum
        content_bytes = content if isinstance(content, bytes) else content.encode("utf-8")
        
        # Calculate SHA-256 checksum
        checksum = hashlib.sha256(content_bytes).hexdigest()
        
        # We need a unique S3 key. Format: {tenant_id}/{job_id}/{uuid}-{file_name}
        # Adding a short UUID prevents accidental overwrites in MinIO before DB versioning is applied
        unique_id = str(uuid.uuid4())[:8]
        s3_key = f"{tenant_id}/{job_id}/{unique_id}-{file_name}"
        
        # 1. Upload to MinIO (blocking call, but acceptable for small artifacts in Celery)
        size_bytes = self._storage.upload_file(s3_key, content_bytes, content_type)
        
        # 2. Persist metadata to DB
        artifact = await self._repo.create(
            job_id=job_id,
            tenant_id=tenant_id,
            file_name=file_name,
            s3_key=s3_key,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum=checksum,
            artifact_metadata=artifact_metadata,
        )
        await self._session.commit()
        
        logger.info(
            "artifact.uploaded",
            artifact_id=str(artifact.id),
            job_id=str(job_id),
            file_name=file_name,
            size=size_bytes
        )
        
        return artifact

    async def get_download_url(self, artifact_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
        """
        Get a presigned URL to download an artifact.

        Args:
            artifact_id: The Artifact DB ID.
            tenant_id: Owning tenant.

        Returns:
            A string HTTP URL valid for 1 hour.
            
        Raises:
            NotFoundError: If artifact doesn't exist or isn't owned by tenant.
        """
        artifact = await self._repo.get_by_id(artifact_id, tenant_id)
        if not artifact:
            raise NotFoundError(f"Artifact {artifact_id} not found")
            
        url = self._storage.generate_presigned_url(artifact.s3_key)
        
        logger.info("artifact.download_url_generated", artifact_id=str(artifact_id))
        return url
