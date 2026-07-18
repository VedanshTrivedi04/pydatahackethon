"""
Webhook API Routes — /api/v1/webhooks

Public endpoints for external systems (e.g. GitHub) to send events.
These endpoints are NOT authenticated with Bearer tokens (unlike other routes).
Instead, they use HMAC signature validation to verify payload authenticity.
"""

from typing import Any

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from engine.api.schemas.webhook import WebhookResponse
from engine.config.database import get_db_session
from engine.core.jobs.service import JobService
from engine.core.jobs.repository import JobRepository
from engine.core.webhooks.service import WebhookService
from engine.utils.exceptions import AuthenticationError as AuthError, BusinessValidationError
from engine.utils.logging import get_logger

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = get_logger(__name__)


async def get_webhook_service(
    session: AsyncSession = Depends(get_db_session),
) -> WebhookService:
    """Dependency injection for WebhookService."""
    job_repo = JobRepository(session)
    job_service = JobService(session=session, repository=job_repo)
    return WebhookService(session=session, job_service=job_service)


@router.post(
    "/github",
    response_model=WebhookResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="GitHub Webhook Intake",
    description=(
        "Receives webhooks from GitHub App installations. "
        "Validates HMAC SHA-256 signature, maps the installation to a tenant, "
        "and potentially enqueues a ShipFaster job depending on the event."
    ),
)
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    service: WebhookService = Depends(get_webhook_service),
) -> WebhookResponse:
    """Process incoming GitHub webhook."""
    
    if not x_github_event or not x_github_delivery:
        logger.warning("webhook.github.missing_headers")
        raise BusinessValidationError("Missing required GitHub headers")

    raw_body = await request.body()
    
    try:
        payload_data = await request.json()
    except Exception:
        raise BusinessValidationError("Invalid JSON payload")

    try:
        result = await service.process_github_webhook(
            event_type=x_github_event,
            delivery_id=x_github_delivery,
            signature=x_hub_signature_256,
            raw_body=raw_body,
            payload_data=payload_data,
        )
        
        status_msg = result.get("status")
        
        if status_msg == "ignored":
            return WebhookResponse(
                success=True,
                message=f"Event ignored: {result.get('reason')}"
            )
            
        return WebhookResponse(
            success=True,
            message="Event processed successfully",
            event_id=result.get("event_id"),
            job_id=result.get("job_id"),
        )
        
    except AuthError as e:
        # We explicitly handle AuthError to return 401 instead of 500
        raise AuthError(str(e))
