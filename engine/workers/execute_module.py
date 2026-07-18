"""
Main Celery Task — execute_module_task.

This is the single Celery task that executes ALL ShipFaster modules.
It acts as the orchestrator — it:

1. Checks idempotency (skip if job already succeeded)
2. Updates job status to 'running'
3. Dynamically imports and calls the module's run() function
4. Persists the ModuleResult back to the jobs table
5. Triggers viaSocket dispatch on success (stub for Phase 7)
6. Handles retries with exponential backoff
7. Routes permanently failed jobs to the dead-letter queue

CRITICAL CONTRACT (never break this):
    Every module MUST implement:
        async def run(job_id: str, tenant_id: str, payload: dict) -> ModuleResult

Dev 1 owns the implementation. Dev 3 (this file) owns the orchestration.
"""

import asyncio
import importlib
from typing import Any

from celery import Task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from engine.core.queue.celery_app import celery_app, QUEUE_DLQ
from engine.core.queue.contracts import ModuleResult
from engine.utils.logging import get_logger

logger = get_logger(__name__)

# Mapping of module_name → Python import path of the handler
# Dev 1 will create these — we import dynamically so missing modules
# fail gracefully (job → failed) rather than crashing the worker process
MODULE_HANDLER_MAP: dict[str, str] = {
    "scaffolder": "engine.modules.scaffolder.handler",
    "test_generator": "engine.modules.test_generator.handler",
    "docs_generator": "engine.modules.docs_generator.handler",
    "changelog_generator": "engine.modules.changelog_generator.handler",
    "notebook_to_blog": "engine.modules.notebook_to_blog.handler",
}


@celery_app.task(
    name="engine.workers.execute_module.execute_module_task",
    bind=True,                      # `self` = Task instance for retry access
    max_retries=2,                  # Total 3 attempts (1 initial + 2 retries)
    default_retry_delay=60,         # Base delay between retries (seconds)
    acks_late=True,                 # ACK after completion (not before)
    reject_on_worker_lost=True,     # Re-queue if worker process dies
    track_started=True,             # Track 'STARTED' state in Redis
    serializer="json",
)
def execute_module_task(
    self: Task,
    job_id: str,
    tenant_id: str,
    module_name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute a single ShipFaster AI module for a given job.

    This task:
    1. Checks idempotency — skips if job already in success state
    2. Updates job to 'running'
    3. Calls module.run() in an event loop
    4. Persists result to jobs table
    5. Handles retries with exponential backoff
    6. Sends to DLQ on permanent failure

    Args:
        self:        Celery Task instance (bound task).
        job_id:      String UUID of the Job record.
        tenant_id:   String UUID of the owning Tenant.
        module_name: Module to execute (scaffolder, test_generator, etc.).
        payload:     Module-specific input dict.

    Returns:
        Dict with status, job_id, and output summary.
    """
    import uuid as _uuid

    job_uuid = _uuid.UUID(job_id)
    tenant_uuid = _uuid.UUID(tenant_id)

    logger.info(
        "worker.task_received",
        job_id=job_id,
        tenant_id=tenant_id,
        module=module_name,
        attempt=self.request.retries + 1,
    )

    # Run the async execution in a new event loop
    # Celery workers run in sync context — we bridge to async here
    try:
        result = asyncio.run(
            _execute_async(
                task=self,
                job_id=job_uuid,
                tenant_id=tenant_uuid,
                module_name=module_name,
                payload=payload,
            )
        )
        return result
    except SoftTimeLimitExceeded:
        # Task exceeded soft time limit — clean up and fail gracefully
        logger.error(
            "worker.soft_time_limit_exceeded",
            job_id=job_id,
            module=module_name,
        )
        asyncio.run(
            _fail_job(job_uuid, tenant_uuid, "Job exceeded maximum execution time limit.")
        )
        return {"status": "failed", "job_id": job_id, "error": "Soft time limit exceeded"}


async def _execute_async(
    task: Task,
    job_id: "uuid.UUID",
    tenant_id: "uuid.UUID",
    module_name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Async implementation of job execution.

    Separated from the sync Celery task to allow clean async/await patterns
    and better testability.
    """
    import uuid

    from engine.config.database import AsyncSessionLocal
    from engine.core.jobs.repository import JobRepository
    from engine.core.jobs.service import JobService

    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        service = JobService(session=session, repository=repo)

        # ------------------------------------------------------------------
        # IDEMPOTENCY CHECK
        # ------------------------------------------------------------------
        # If the job is already in a terminal state (success, failed, cancelled),
        # skip execution. This protects against duplicate Celery deliveries.
        job = await repo.get_by_id(job_id=job_id, tenant_id=tenant_id)
        if job is None:
            logger.error("worker.job_not_found", job_id=str(job_id))
            return {"status": "error", "job_id": str(job_id), "error": "Job not found"}

        if job.status in ("success", "cancelled"):
            logger.info(
                "worker.idempotency_skip",
                job_id=str(job_id),
                current_status=job.status,
            )
            return {"status": job.status, "job_id": str(job_id), "skipped": True}

        # ------------------------------------------------------------------
        # MARK AS RUNNING
        # ------------------------------------------------------------------
        await service.on_worker_started(job_id)
        await session.commit()

        # ------------------------------------------------------------------
        # DYNAMIC MODULE IMPORT
        # ------------------------------------------------------------------
        handler_path = MODULE_HANDLER_MAP.get(module_name)
        if handler_path is None:
            error_msg = f"No handler registered for module '{module_name}'"
            logger.error("worker.unknown_module", module=module_name)
            await _persist_failure(service, session, job_id, error_msg, is_retriable=False)
            return {"status": "failed", "job_id": str(job_id), "error": error_msg}

        try:
            module = importlib.import_module(handler_path)
            run_fn = getattr(module, "run", None)
            if run_fn is None:
                raise ImportError(f"Module '{handler_path}' has no 'run' function")
        except ImportError as e:
            error_msg = f"Module '{module_name}' not available yet: {str(e)}"
            logger.warning("worker.module_not_found", module=module_name, error=str(e))
            # Not retriable — module doesn't exist
            await _persist_failure(service, session, job_id, error_msg, is_retriable=False)
            return {"status": "failed", "job_id": str(job_id), "error": error_msg}

        # ------------------------------------------------------------------
        # EXECUTE MODULE
        # ------------------------------------------------------------------
        try:
            logger.info(
                "worker.module_executing",
                job_id=str(job_id),
                module=module_name,
            )

            # Call Dev 1's run() function with the contract signature
            raw_result = await run_fn(
                job_id=str(job_id),
                tenant_id=str(tenant_id),
                payload=payload,
            )

            # Validate the result shape against our contract
            if isinstance(raw_result, dict):
                module_result = ModuleResult(**raw_result)
            elif isinstance(raw_result, ModuleResult):
                module_result = raw_result
            else:
                raise ValueError(
                    f"Module '{module_name}' returned invalid type: {type(raw_result).__name__}. "
                    "Must return ModuleResult or dict."
                )

        except Exception as e:
            # Module raised an exception — retry if attempts remain
            return await _handle_module_exception(
                task=task,
                service=service,
                session=session,
                job_id=job_id,
                module_name=module_name,
                exception=e,
            )

        # ------------------------------------------------------------------
        # PERSIST ARTIFACTS & RESULT
        # ------------------------------------------------------------------
        async with AsyncSessionLocal() as result_session:
            from engine.core.artifacts.service import ArtifactService
            artifact_service = ArtifactService(result_session)
            
            # Upload each artifact to MinIO and persist DB record
            for artifact_data in module_result.artifacts:
                try:
                    await artifact_service.upload_artifact(
                        job_id=job_id,
                        tenant_id=tenant_id,
                        file_name=artifact_data.file_name,
                        content=artifact_data.content,
                        content_type=artifact_data.content_type,
                        artifact_metadata=artifact_data.metadata,
                    )
                except Exception as e:
                    logger.error(
                        "worker.artifact_upload_failed",
                        job_id=str(job_id),
                        file_name=artifact_data.file_name,
                        error=str(e),
                    )
                    # We continue uploading others even if one fails,
                    # but we could choose to fail the job here.

            result_repo = JobRepository(result_session)
            result_service = JobService(session=result_session, repository=result_repo)

            # We strip out the raw content from the result before saving it to the Job output
            # so we don't duplicate the massive files in PostgreSQL JSONB
            clean_artifacts = [{"file_name": a.file_name} for a in module_result.artifacts]
            safe_output = dict(module_result.output)
            safe_output["_artifacts"] = clean_artifacts
            if module_result.sandbox_logs:
                safe_output["_sandbox_logs"] = module_result.sandbox_logs

            await result_service.on_worker_completed(
                job_id=job_id,
                status=module_result.status,
                result=safe_output,
                error=module_result.error,
            )

            # If module requires approval (notebook_to_blog) and succeeded,
            # transition to approval_pending instead of success
            if module_result.status == "success" and job.requires_approval:
                await result_repo.mark_approval_pending(job_id)
                logger.info(
                    "worker.approval_required",
                    job_id=str(job_id),
                    module=module_name,
                )
            elif module_result.status == "success":
                # Fire viaSocket dispatch directly
                celery_app.send_task(
                    "engine.workers.viasocket_dispatcher.dispatch_webhook",
                    kwargs={
                        "job_id": str(job_id),
                        "tenant_id": str(tenant_id),
                        "event_name": "job_completed",
                        "module": module_name,
                        "data": module_result.output or {},
                    },
                    queue="shipfaster.low",
                )

            await result_session.commit()

        logger.info(
            "worker.module_completed",
            job_id=str(job_id),
            module=module_name,
            status=module_result.status,
        )

        return {
            "status": module_result.status,
            "job_id": str(job_id),
            "module": module_name,
            "artifact_count": len(module_result.artifacts),
        }


async def _handle_module_exception(
    task: Task,
    service: "JobService",
    session: Any,
    job_id: "uuid.UUID",
    module_name: str,
    exception: Exception,
) -> dict[str, Any]:
    """
    Handle a module execution exception with retry logic.

    Args:
        task:        Celery Task instance.
        service:     JobService for this session.
        session:     Async SQLAlchemy session.
        job_id:      UUID of the job.
        module_name: Module that raised the exception.
        exception:   The raised exception.

    Returns:
        Result dict (only if retries exhausted — otherwise raises Retry).
    """
    import uuid

    error_msg = f"{type(exception).__name__}: {str(exception)}"
    logger.error(
        "worker.module_exception",
        job_id=str(job_id),
        module=module_name,
        exc_type=type(exception).__name__,
        error=str(exception),
        attempt=task.request.retries + 1,
        max_retries=task.max_retries,
    )

    if task.request.retries < task.max_retries:
        # Retry with exponential backoff: 60s, 120s
        countdown = 60 * (2 ** task.request.retries)
        await service.on_worker_retry(job_id=job_id, reason=error_msg)
        await session.commit()

        logger.warning(
            "worker.retrying",
            job_id=str(job_id),
            countdown_seconds=countdown,
            attempt=task.request.retries + 1,
        )

        raise task.retry(exc=exception, countdown=countdown)
    else:
        # All retries exhausted — send to DLQ and mark as failed
        await _persist_failure(service, session, job_id, error_msg, is_retriable=False)

        # Send to dead-letter queue for manual inspection
        celery_app.send_task(
            "engine.workers.retry_handler.handle_dead_letter",
            kwargs={
                "job_id": str(job_id),
                "operation_type": "job_execution",
                "error": error_msg,
                "module": module_name,
            },
            queue=QUEUE_DLQ,
        )

        return {"status": "failed", "job_id": str(job_id), "error": error_msg}


async def _persist_failure(
    service: "JobService",
    session: Any,
    job_id: "uuid.UUID",
    error: str,
    is_retriable: bool = True,
) -> None:
    """Persist job failure and commit."""
    await service.on_worker_completed(
        job_id=job_id,
        status="failed",
        error=error,
    )
    await session.commit()


async def _fail_job(
    job_id: "uuid.UUID",
    tenant_id: "uuid.UUID",
    error: str,
) -> None:
    """Standalone async function to fail a job (used from sync exception handlers)."""
    from engine.config.database import AsyncSessionLocal
    from engine.core.jobs.repository import JobRepository
    from engine.core.jobs.service import JobService

    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        service = JobService(session=session, repository=repo)
        await service.on_worker_completed(job_id=job_id, status="failed", error=error)
        await session.commit()
