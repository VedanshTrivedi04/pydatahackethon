"""
Artifact Repository.

Handles database operations for the Artifact model, storing metadata
about files uploaded to MinIO.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.models.artifact import Artifact
from engine.utils.logging import get_logger

logger = get_logger(__name__)


class ArtifactRepository:
    """Data access layer for Artifacts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        file_name: str,
        s3_key: str,
        content_type: str,
        size_bytes: int | None,
        checksum: str | None = None,
        artifact_metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        """Create a new artifact metadata record."""
        # Check if an artifact with this name already exists for this job to bump version
        stmt = (
            select(Artifact)
            .where(Artifact.job_id == job_id, Artifact.file_name == file_name)
            .order_by(Artifact.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        latest_version = result.scalar_one_or_none()
        
        version = (latest_version.version + 1) if latest_version else 1

        artifact = Artifact(
            job_id=job_id,
            tenant_id=tenant_id,
            file_name=file_name,
            s3_key=s3_key,
            content_type=content_type,
            size_bytes=size_bytes,
            version=version,
            checksum=checksum,
            artifact_metadata=artifact_metadata,
        )
        self._session.add(artifact)
        await self._session.flush()
        return artifact

    async def get_by_id(self, artifact_id: uuid.UUID, tenant_id: uuid.UUID) -> Artifact | None:
        """Fetch an artifact by ID, ensuring tenant ownership."""
        stmt = select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
