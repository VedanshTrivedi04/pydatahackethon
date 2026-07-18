"""
Webhook Event Repository.

Handles database operations for the WebhookEvent model.
Implements the store-first pattern: events are inserted immediately,
then marked as processed or failed after business logic completes.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from engine.core.models.webhook import WebhookEvent
from engine.utils.logging import get_logger

logger = get_logger(__name__)


class WebhookRepository:
    """
    Data access layer for WebhookEvent.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store_event(
        self,
        tenant_id: uuid.UUID,
        source: str,
        event_type: str,
        raw_payload: dict[str, Any],
        headers: dict[str, Any],
        delivery_id: str | None = None,
    ) -> WebhookEvent:
        """
        Store a new webhook event in the database.

        Args:
            tenant_id: Owner tenant.
            source: 'github', 'ci', etc.
            event_type: e.g. 'push', 'pull_request'.
            raw_payload: Full JSON payload.
            headers: Sanitized headers.
            delivery_id: ID for deduplication.

        Returns:
            The created WebhookEvent.
        """
        event = WebhookEvent(
            tenant_id=tenant_id,
            source=source,
            event_type=event_type,
            delivery_id=delivery_id,
            raw_payload=raw_payload,
            headers=headers,
            processed=False,
            received_at=datetime.now(timezone.utc),
        )
        self._session.add(event)
        
        # Flush to get the ID, don't commit yet (Service layer commits)
        await self._session.flush()
        return event

    async def mark_processed(self, event_id: uuid.UUID, job_id: uuid.UUID | None) -> None:
        """
        Mark a webhook event as successfully processed.

        Args:
            event_id: The WebhookEvent ID.
            job_id: The ID of the Job that was created, if any.
        """
        stmt = (
            update(WebhookEvent)
            .where(WebhookEvent.id == event_id)
            .values(
                processed=True,
                processing_error=None,
                job_id=job_id,
            )
        )
        await self._session.execute(stmt)

    async def mark_failed(self, event_id: uuid.UUID, error: str) -> None:
        """
        Mark a webhook event as failed.

        Args:
            event_id: The WebhookEvent ID.
            error: Error message/reason.
        """
        stmt = (
            update(WebhookEvent)
            .where(WebhookEvent.id == event_id)
            .values(
                processed=False,
                processing_error=error,
            )
        )
        await self._session.execute(stmt)

    async def is_duplicate_delivery(self, delivery_id: str) -> bool:
        """
        Check if a GitHub delivery ID has already been received.

        Args:
            delivery_id: The X-GitHub-Delivery header value.

        Returns:
            True if it exists, False otherwise.
        """
        if not delivery_id:
            return False

        stmt = select(WebhookEvent.id).where(WebhookEvent.delivery_id == delivery_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
