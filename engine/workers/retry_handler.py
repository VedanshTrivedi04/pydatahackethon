"""
Dead-Letter Queue Handler.

Processes jobs that have exhausted all Celery retries and landed
in the shipfaster.dlq queue.

Responsibilities:
1. Create a RetryQueue record for manual inspection
2. Create a notification for the tenant dashboard
3. Log with full context for support/debugging

This task does NOT automatically retry — DLQ items require
manual intervention via the /api/v1/admin/retry-queue endpoint.
"""

import asyncio
from typing import Any

from engine.core.queue.celery_app import celery_app
from engine.utils.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="engine.workers.retry_handler.handle_dead_letter",
    bind=True,
    max_retries=0,      # DLQ handler never retries itself
    queue="shipfaster.dlq",
    serializer="json",
    acks_late=True,
)
def handle_dead_letter(
    self: Any,
    job_id: str,
    operation_type: str,
    error: str,
    module: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """
    Handle a permanently failed job from the dead-letter queue.

    Args:
        self:           Celery Task instance.
        job_id:         String UUID of the failed Job.
        operation_type: Type of operation that failed (job_execution, etc.).
        error:          Last failure error message.
        module:         Module name if applicable.

    Returns:
        Confirmation dict.
    """
    logger.error(
        "dlq.item_received",
        job_id=job_id,
        operation_type=operation_type,
        error=error,
        module=module,
    )

    # Persist DLQ item and create tenant notification
    result = asyncio.run(
        _persist_dlq_item(
            job_id=job_id,
            operation_type=operation_type,
            error=error,
            module=module,
        )
    )

    return result


async def _persist_dlq_item(
    job_id: str,
    operation_type: str,
    error: str,
    module: str | None,
) -> dict[str, Any]:
    """
    Persist a DLQ item to the retry_queue table and create a notification.

    Args:
        job_id:         String UUID of the failed job.
        operation_type: Operation type string.
        error:          Error message.
        module:         Module name.

    Returns:
        Confirmation dict.
    """
    import uuid

    from engine.config.database import AsyncSessionLocal
    from engine.core.models.notification import Notification, RetryQueue
    from engine.core.jobs.repository import JobRepository

    try:
        async with AsyncSessionLocal() as session:
            # Look up the job to get tenant_id
            job_uuid = uuid.UUID(job_id)
            stmt_result = await session.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(
                    __import__(
                        "engine.core.models.job", fromlist=["Job"]
                    ).Job
                ).where(
                    __import__(
                        "engine.core.models.job", fromlist=["Job"]
                    ).Job.id == job_uuid
                )
            )
            from engine.core.models.job import Job
            from sqlalchemy import select

            result = await session.execute(
                select(Job).where(Job.id == job_uuid)
            )
            job = result.scalar_one_or_none()

            if job is None:
                logger.error("dlq.job_not_found", job_id=job_id)
                return {"status": "error", "reason": "job not found"}

            # Create RetryQueue record
            retry_item = RetryQueue(
                tenant_id=job.tenant_id,
                operation_type=operation_type,
                reference_id=job_id,
                payload={"job_id": job_id, "module": module},
                failure_reason=error,
                attempt_count=3,  # After 3 attempts (1 + 2 retries)
                status="pending",
            )
            session.add(retry_item)

            # Create tenant notification
            notification = Notification(
                tenant_id=job.tenant_id,
                job_id=job.id,
                notification_type="job_failed",
                title=f"Job permanently failed: {module or 'unknown module'}",
                body=(
                    f"Job {job_id[:8]}... failed after all retry attempts. "
                    f"Error: {error[:200]}. "
                    "Contact support or retry from the dashboard."
                ),
                is_read=False,
            )
            session.add(notification)
            await session.commit()

            logger.warning(
                "dlq.item_persisted",
                job_id=job_id,
                tenant_id=str(job.tenant_id),
                retry_queue_id=str(retry_item.id),
            )

            return {
                "status": "persisted",
                "job_id": job_id,
                "retry_queue_id": str(retry_item.id),
            }

    except Exception as e:
        logger.error("dlq.persist_failed", job_id=job_id, error=str(e))
        return {"status": "error", "reason": str(e)}
