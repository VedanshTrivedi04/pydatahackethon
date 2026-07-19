"""
Artifacts API Routes — /api/v1/artifacts

Endpoints for interacting with generated files.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os

from engine.api.dependencies.auth import get_current_tenant
from engine.config.database import get_db_session
from engine.core.artifacts.service import ArtifactService
from engine.core.models.tenant import Tenant
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
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, str]:
    """Get a short-lived download link for the artifact."""
    tenant_id = current_tenant.id
    
    url = await service.get_download_url(artifact_id, tenant_id)
    return {"download_url": url}


@router.get(
    "/download-file",
    summary="Download local file directly",
)
async def download_local_file(key: str) -> FileResponse:
    """Download local fallback artifact file directly."""
    from engine.core.storage import LOCAL_STORAGE_DIR
    file_path = LOCAL_STORAGE_DIR / key
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(
        path=str(file_path),
        filename=os.path.basename(key),
        media_type="application/zip"
    )
