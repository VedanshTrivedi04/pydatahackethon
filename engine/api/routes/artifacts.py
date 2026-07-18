"""
Artifacts API Routes — /api/v1/artifacts

Endpoints for interacting with generated files.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from engine.api.middleware.auth import require_auth
from engine.config.database import get_db_session
from engine.core.artifacts.service import ArtifactService
from engine.utils.exceptions import BusinessValidationError

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])


async def get_artifact_service(
    session: AsyncSession = Depends(get_db_session),
) -> ArtifactService:
    """Dependency injection for ArtifactService."""
    return ArtifactService(session=session)


@router.get(
    "/{artifact_id}/download",
    response_model=dict[str, str],
    summary="Get Presigned Download URL",
    description="Returns a temporary S3/MinIO presigned URL to download the artifact."
)
async def get_artifact_download_url(
    artifact_id: uuid.UUID,
    request: Request,
    service: ArtifactService = Depends(get_artifact_service),
    auth: dict[str, Any] = Depends(require_auth),
) -> dict[str, str]:
    """Get a short-lived download link for the artifact."""
    tenant_id = uuid.UUID(auth["tenant_id"])
    
    url = await service.get_download_url(artifact_id, tenant_id)
    return {"download_url": url}
