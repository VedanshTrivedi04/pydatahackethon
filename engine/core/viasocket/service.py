"""
viaSocket Service Layer.

Manages the persistence of viaSocket dispatch attempts to the database,
ensuring a complete audit trail for outbound webhooks.
"""

import uuid
from typing import Any
from datetime import datetime, timezone, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.models.viasocket import ViaSocketDispatch
from engine.utils.logging import get_logger

logger = get_logger(__name__)


class ViaSocketService:
    """Service for tracking viaSocket dispatches."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_dispatch_record(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        event_name: str,
        target_url: str,
        payload_sent: dict[str, Any],
        attempt_count: int = 1,
    ) -> ViaSocketDispatch:
        """
        Create a new dispatch record in 'pending' state.
        This is called BEFORE making the HTTP request.
        """
        dispatch = ViaSocketDispatch(
            job_id=job_id,
            tenant_id=tenant_id,
            event_name=event_name,
            target_url=target_url,
            payload_sent=payload_sent,
            attempt_count=attempt_count,
            status="pending",
        )
        self._session.add(dispatch)
        await self._session.flush()
        return dispatch

    async def update_dispatch_result(
        self,
        dispatch_id: uuid.UUID,
        status_code: int,
        response_body: str,
        is_final_attempt: bool,
    ) -> None:
        """
        Update a dispatch record with the HTTP result.
        """
        # Determine status
        if 200 <= status_code < 300:
            status = "success"
            next_retry_at = None
        else:
            status = "dead_lettered" if is_final_attempt else "retrying"
            
            # Simple backoff calculation (e.g. 5 minutes)
            next_retry_at = None
            if status == "retrying":
                next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Truncate response body if it's too large (safety limit)
        truncated_body = response_body[:2000] if response_body else None

        stmt = (
            update(ViaSocketDispatch)
            .where(ViaSocketDispatch.id == dispatch_id)
            .values(
                status_code=status_code,
                response_body=truncated_body,
                status=status,
                next_retry_at=next_retry_at,
                # If network error (status_code == 0), log it to error_message
                error_message=truncated_body if status_code == 0 else None
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        
        logger.info(
            "viasocket.dispatch_result",
            dispatch_id=str(dispatch_id),
            status=status,
            status_code=status_code
        )
