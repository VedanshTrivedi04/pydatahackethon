"""
viaSocket Celery Worker Task.

Asynchronously sends outbound webhooks to viaSocket when jobs complete.
Uses exponential backoff retries if the viaSocket endpoint is down or returns 5xx.
"""

import asyncio
from typing import Any
import uuid

from celery import Task

from engine.core.queue.celery_app import celery_app, QUEUE_DEFAULT, QUEUE_DLQ
from engine.core.viasocket.contracts import ViaSocketPayload
from engine.core.viasocket.client import send_viasocket_webhook
from engine.utils.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="engine.workers.viasocket_dispatcher.dispatch_webhook",
    bind=True,
    max_retries=3,          # 1 initial + 3 retries = 4 total attempts
    default_retry_delay=60, # 1 minute
    acks_late=True,
    queue="shipfaster.low", # Low priority queue since it's just a notification
    serializer="json",
)
def dispatch_webhook(
    self: Task,
    job_id: str,
    tenant_id: str,
    event_name: str,
    module: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Send an outbound webhook to a tenant's viaSocket URL.

    Args:
        self: Celery task.
        job_id: Job UUID string.
        tenant_id: Tenant UUID string.
        event_name: e.g., 'job_completed', 'job_approved'.
        module: The module that ran (e.g., 'notebook_to_blog').
        data: The output artifact or data.

    Returns:
        Dict with dispatch results.
    """
    result = asyncio.run(
        _dispatch_async(
            task=self,
            job_id=job_id,
            tenant_id=tenant_id,
            event_name=event_name,
            module=module,
            data=data,
        )
    )
    return result


async def _dispatch_async(
    task: Task,
    job_id: str,
    tenant_id: str,
    event_name: str,
    module: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    from engine.config.database import AsyncSessionLocal, engine
    # Dispose connection pool to avoid "Event loop is closed" errors when reusing connections across Celery tasks on Windows
    await engine.dispose()
    from engine.core.models.tenant import Tenant
    from engine.core.viasocket.service import ViaSocketService
    from sqlalchemy import select
    
    job_uuid = uuid.UUID(job_id)
    tenant_uuid = uuid.UUID(tenant_id)

    async with AsyncSessionLocal() as session:
        # Lookup Tenant URL
        stmt = select(Tenant).where(Tenant.id == tenant_uuid)
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant or not tenant.viasocket_webhook_url:
            logger.info(
                "viasocket.skip_no_url",
                tenant_id=tenant_id,
                job_id=job_id
            )
            return {"status": "skipped", "reason": "No viaSocket URL configured"}

        target_url = tenant.viasocket_webhook_url
        
        # Build Payload
        payload_model = ViaSocketPayload(
            event=event_name,
            tenant_id=tenant_uuid,
            job_id=job_uuid,
            module=module,
            data=data,
        )
        payload_dict = payload_model.model_dump(mode="json")
        
        # Create Pending Record
        svc = ViaSocketService(session)
        dispatch_record = await svc.create_dispatch_record(
            job_id=job_uuid,
            tenant_id=tenant_uuid,
            event_name=event_name,
            target_url=target_url,
            payload_sent=payload_dict,
            attempt_count=task.request.retries + 1,
        )
        await session.commit()
        
        dispatch_id = dispatch_record.id

    # ---------------------------------------------------------
    # Execute HTTP Request (Synchronous / Blocking in Celery Worker Thread)
    # ---------------------------------------------------------
    status_code, response_body = send_viasocket_webhook(target_url, payload_dict)
    
    is_final_attempt = task.request.retries >= task.max_retries
    
    # Update Record
    async with AsyncSessionLocal() as session:
        svc = ViaSocketService(session)
        await svc.update_dispatch_result(
            dispatch_id=dispatch_id,
            status_code=status_code,
            response_body=response_body,
            is_final_attempt=is_final_attempt,
        )
        
    # Check if we need to retry
    if status_code == 0 or status_code >= 500:
        if not is_final_attempt:
            # Exponential backoff: 60, 120, 240 seconds
            countdown = 60 * (2 ** task.request.retries)
            logger.warning(
                "viasocket.dispatch_retrying",
                dispatch_id=str(dispatch_id),
                status_code=status_code,
                countdown=countdown
            )
            raise task.retry(countdown=countdown)
        else:
            logger.error(
                "viasocket.dispatch_failed_permanently",
                dispatch_id=str(dispatch_id),
                status_code=status_code
            )
            # Send to Dead Letter Queue for manual inspection
            celery_app.send_task(
                "engine.workers.retry_handler.handle_dead_letter",
                kwargs={
                    "job_id": job_id,
                    "operation_type": "viasocket_dispatch",
                    "error": f"viaSocket POST failed with status {status_code}: {response_body[:100]}",
                    "module": module,
                },
                queue=QUEUE_DLQ,
            )
            return {"status": "failed", "status_code": status_code}

    return {"status": "success", "status_code": status_code}
