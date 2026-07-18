"""
Webhook Service Layer.

Business logic for receiving webhooks, looking up tenants, validating signatures,
and mapping events into ShipFaster Jobs (e.g. triggering docs_generator on push).
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.api.schemas.webhook import GitHubWebhookPayload
from engine.core.jobs.service import JobService
from engine.core.models.tenant import Tenant
from engine.core.webhooks.repository import WebhookRepository
from engine.core.webhooks.security import verify_github_signature
from engine.utils.exceptions import BusinessValidationError, NotFoundError, AuthError
from engine.utils.logging import get_logger

logger = get_logger(__name__)


# Simple mapping from GitHub event types to ShipFaster modules
# In a real system, this would be configurable per-tenant.
GITHUB_EVENT_MODULE_MAP = {
    # Generate tests or docs when a pull request is opened
    "pull_request": "test_generator",
    
    # Generate changelog when a release is published
    "release": "changelog_generator",
    
    # Generate docs on a push to main
    "push": "docs_generator",
}


class WebhookService:
    """Service for processing inbound webhooks."""

    def __init__(self, session: AsyncSession, job_service: JobService) -> None:
        self._session = session
        self._repo = WebhookRepository(session)
        self._job_service = job_service

    async def process_github_webhook(
        self,
        event_type: str,
        delivery_id: str,
        signature: str | None,
        raw_body: bytes,
        payload_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Process an inbound GitHub webhook.

        1. Verify signature.
        2. Prevent duplicate deliveries.
        3. Lookup Tenant by installation ID.
        4. Store raw WebhookEvent.
        5. Map event to a module and submit Job.
        6. Mark event processed.
        """
        # 1. Verify Signature
        if not verify_github_signature(raw_body, signature):
            logger.warning("webhook.invalid_signature", delivery_id=delivery_id)
            raise AuthError("Invalid or missing GitHub webhook signature")

        # 2. Prevent Duplicates
        if await self._repo.is_duplicate_delivery(delivery_id):
            logger.info("webhook.duplicate_delivery_ignored", delivery_id=delivery_id)
            return {"status": "ignored", "reason": "duplicate delivery"}

        # Extract structured data
        payload = GitHubWebhookPayload.model_validate(payload_data)

        # 3. Lookup Tenant by Installation ID
        # If there's no installation ID, we can't route this webhook
        if not payload.installation or not payload.installation.id:
            logger.warning("webhook.missing_installation_id", delivery_id=delivery_id)
            return {"status": "ignored", "reason": "missing installation id in payload"}
            
        installation_id = str(payload.installation.id)
        
        stmt = select(Tenant).where(Tenant.github_app_installation_id == installation_id)
        result = await self._session.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            logger.warning(
                "webhook.tenant_not_found", 
                installation_id=installation_id,
                delivery_id=delivery_id
            )
            return {"status": "ignored", "reason": "unrecognized installation id"}

        if not tenant.is_active:
            logger.warning(
                "webhook.tenant_inactive", 
                tenant_id=str(tenant.id),
                delivery_id=delivery_id
            )
            return {"status": "ignored", "reason": "tenant is inactive"}

        # 4. Store Raw WebhookEvent (Store First)
        # We store sanitized headers (excluding the signature itself)
        headers = {
            "x-github-event": event_type,
            "x-github-delivery": delivery_id
        }
        
        event = await self._repo.store_event(
            tenant_id=tenant.id,
            source="github",
            event_type=event_type,
            raw_payload=payload_data,
            headers=headers,
            delivery_id=delivery_id,
        )

        # We commit here so the raw event is safely stored even if job mapping fails
        await self._session.commit()

        # 5. Map to Module & Enqueue Job
        try:
            target_module = self._map_event_to_module(event_type, payload)
            
            job_id = None
            if target_module:
                # We extract the repository URL from the payload
                repo_url = payload.repository.html_url if payload.repository else ""
                
                job = await self._job_service.submit_job(
                    tenant_id=tenant.id,
                    module=target_module,
                    payload={"repo_url": repo_url, "webhook_event": event_type, "action": payload.action},
                    trigger="webhook",
                    priority=5,  # Medium priority for webhooks
                )
                job_id = job.id
                logger.info(
                    "webhook.job_created",
                    tenant_id=str(tenant.id),
                    event_id=str(event.id),
                    job_id=str(job_id),
                    module=target_module
                )
            
            # 6. Mark Processed
            await self._repo.mark_processed(event.id, job_id)
            await self._session.commit()
            
            return {
                "status": "processed",
                "event_id": str(event.id),
                "job_id": str(job_id) if job_id else None,
                "module": target_module
            }
            
        except Exception as e:
            # Mark failed and rollback
            await self._session.rollback()
            logger.error(
                "webhook.processing_failed",
                event_id=str(event.id),
                error=str(e),
                exc_info=True
            )
            
            # Use a new transaction to mark as failed
            await self._repo.mark_failed(event.id, str(e))
            await self._session.commit()
            raise

    def _map_event_to_module(self, event_type: str, payload: GitHubWebhookPayload) -> str | None:
        """
        Map a GitHub event to a ShipFaster module based on hardcoded rules.
        """
        # Exclude certain actions like 'closed' or 'deleted' which usually don't need generation
        if payload.action in ("closed", "deleted"):
            return None
            
        # Default map
        return GITHUB_EVENT_MODULE_MAP.get(event_type)
