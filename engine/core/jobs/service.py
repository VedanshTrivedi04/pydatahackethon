"""
Job Service — Service Layer.

Orchestrates all job lifecycle operations:

1. Job submission (create + enqueue to Celery)
2. Job status polling
3. Approval / rejection of notebook_to_blog jobs
4. Job cancellation
5. Job log retrieval
6. Analytics aggregation

Business rules enforced here:
- Only certain status transitions are valid
- Only certain modules support approval flow
- Retry count limits
- Tenant ownership verification at every step

This is the coordination layer — the Celery worker also uses this
service to update job state after execution.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.jobs.repository import JobRepository
from engine.core.models.job import Job, JobLog
from engine.core.queue.celery_app import MODULE_QUEUE_MAP, celery_app
from engine.utils.exceptions import (
    JobStateError,
    NotFoundError,
    QueueError,
    ValidationError,
)
from engine.utils.logging import get_logger

logger = get_logger(__name__)

# Modules that require human approval before viaSocket dispatch
APPROVAL_REQUIRED_MODULES = {"notebook_to_blog"}

# Valid status transitions (from → set of allowed next states)
VALID_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"running", "cancelled", "failed"},
    "running": {"success", "failed", "partial", "approval_pending"},
    "partial": {"queued", "cancelled"},   # Can be retried
    "approval_pending": {"approved", "rejected"},
    "approved": {"success"},              # After viaSocket dispatch
    "rejected": set(),                    # Terminal
    "success": set(),                     # Terminal
    "failed": {"queued"},                 # Can be retried
    "cancelled": set(),                   # Terminal
}


class JobService:
    """
    Business logic for all job lifecycle operations.

    Instantiated per-request via FastAPI dependency injection.
    Also used by Celery workers (with their own session).

    Args:
        session:    Async SQLAlchemy session (request-scoped).
        repository: JobRepository instance for this session.
    """

    def __init__(
        self,
        session: AsyncSession,
        repository: JobRepository,
    ) -> None:
        self._session = session
        self._repo = repository

    # -------------------------------------------------------------------------
    # Job Submission
    # -------------------------------------------------------------------------

    async def submit_job(
        self,
        tenant_id: uuid.UUID,
        module: str,
        payload: dict[str, Any],
        trigger: str = "api",
        priority: int = 5,
    ) -> Job:
        """
        Create a new job and enqueue it to the appropriate Celery queue.

        Process:
        1. Validate module name
        2. Create Job record with status='queued'
        3. Determine queue based on module and priority
        4. Send task to Celery
        5. Update Job with celery_task_id

        Args:
            tenant_id: Owning tenant UUID.
            module:    Module name (scaffolder, test_generator, etc.).
            payload:   Module-specific input data.
            trigger:   What initiated this job (api, webhook_github, cli, mcp).
            priority:  Queue priority (1=highest, 10=lowest, default=5).

        Returns:
            The created and enqueued Job.

        Raises:
            ValidationError: If module name is invalid.
            QueueError:      If Celery enqueue fails.
        """
        # Validate module
        self._validate_module(module)

        # Determine if this module requires approval
        requires_approval = module in APPROVAL_REQUIRED_MODULES

        # Create job record
        job = Job(
            tenant_id=tenant_id,
            module=module,
            trigger=trigger,
            status="queued",
            payload=payload,
            requires_approval=requires_approval,
            priority=priority,
        )
        job = await self._repo.create(job)

        from engine.core.events import event_bus, SystemEvent
        await event_bus.emit(SystemEvent(
            type="job.created",
            tenant_id=str(tenant_id),
            payload={"job_id": str(job.id), "module": module, "trigger": trigger}
        ))

        # Log job creation
        await self._repo.add_log(
            job_id=job.id,
            event="job.created",
            message=f"Job created for module '{module}' via '{trigger}'",
            level="INFO",
            context={"module": module, "trigger": trigger, "priority": priority},
        )

        # Determine target queue
        queue_name = MODULE_QUEUE_MAP.get(module, "shipfaster.default")

        # Extract correlation_id for distributed tracing
        import structlog
        correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
        headers = {"x-correlation-id": correlation_id} if correlation_id else None

        # Commit the transaction so that the Celery worker (or synchronous eager task)
        # can immediately query the Job record from the database.
        await self._session.commit()

        # Enqueue to Celery
        try:
            task = celery_app.send_task(
                "engine.workers.execute_module.execute_module_task",
                kwargs={
                    "job_id": str(job.id),
                    "tenant_id": str(tenant_id),
                    "module_name": module,
                    "payload": payload,
                },
                queue=queue_name,
                task_id=None,  # Let Celery generate a UUID
                priority=10 - priority,  # Celery uses inverse priority (9=highest)
                headers=headers,
            )

            # Persist the Celery task ID for tracking and idempotency
            await self._repo.set_celery_task_id(job.id, task.id)

            await self._repo.add_log(
                job_id=job.id,
                event="job.enqueued",
                message=f"Job enqueued to '{queue_name}' with Celery task_id={task.id}",
                level="INFO",
                context={"celery_task_id": task.id, "queue": queue_name},
            )

            logger.info(
                "job.submitted",
                job_id=str(job.id),
                module=module,
                tenant_id=str(tenant_id),
                celery_task_id=task.id,
                queue=queue_name,
            )

        except Exception as e:
            # If Celery fails, mark job as failed and log
            await self._repo.mark_completed(
                job_id=job.id,
                status="failed",
                error=f"Failed to enqueue job: {str(e)}",
            )
            await self._repo.add_log(
                job_id=job.id,
                event="job.enqueue_failed",
                message=f"Celery enqueue failed: {str(e)}",
                level="ERROR",
            )
            logger.error(
                "job.enqueue_failed",
                job_id=str(job.id),
                module=module,
                error=str(e),
            )
            raise QueueError(f"Failed to submit job to queue: {str(e)}") from e

        return job

    # -------------------------------------------------------------------------
    # Job Retrieval
    # -------------------------------------------------------------------------

    async def get_job(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        include_logs: bool = False,
        include_artifacts: bool = False,
    ) -> Job:
        """
        Fetch a single job by ID, scoped to the tenant.

        Args:
            job_id:            UUID of the job.
            tenant_id:         Tenant UUID for ownership verification.
            include_logs:      Include execution log entries.
            include_artifacts: Include artifact metadata.

        Returns:
            Job entity.

        Raises:
            NotFoundError: If job not found or not owned by tenant.
        """
        job = await self._repo.get_by_id(
            job_id=job_id,
            tenant_id=tenant_id,
            load_logs=include_logs,
            load_artifacts=include_artifacts,
        )
        if job is None:
            raise NotFoundError(f"Job '{job_id}' not found.")
        return job

    async def list_jobs(
        self,
        tenant_id: uuid.UUID,
        module: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """
        Paginated job listing for a tenant.

        Args:
            tenant_id: Owning tenant UUID.
            module:    Optional module filter.
            status:    Optional status filter.
            limit:     Max results (auto-capped at 200).
            offset:    Pagination offset.

        Returns:
            Tuple of (jobs, total_count).
        """
        return await self._repo.list_for_tenant(
            tenant_id=tenant_id,
            module=module,
            status=status,
            limit=min(limit, 200),
            offset=offset,
        )

    async def get_job_logs(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[JobLog]:
        """
        Fetch execution logs for a job.

        Args:
            job_id:    UUID of the job.
            tenant_id: Tenant UUID for ownership verification.

        Returns:
            List of JobLog entries in chronological order.

        Raises:
            NotFoundError: If job not found or not owned by tenant.
        """
        # Verify job exists and is owned by tenant first
        await self.get_job(job_id=job_id, tenant_id=tenant_id)
        return await self._repo.get_logs(job_id=job_id, tenant_id=tenant_id)

    # -------------------------------------------------------------------------
    # Approval Flow
    # -------------------------------------------------------------------------

    async def approve_job(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        approved_by: str,
        note: str | None = None,
    ) -> Job:
        """
        Approve a notebook_to_blog job for viaSocket publication.

        After approval, the Celery worker will trigger viaSocket dispatch.

        Args:
            job_id:      UUID of the job.
            tenant_id:   Requesting tenant UUID.
            approved_by: Approver identifier (from Dev 2 auth context).
            note:        Optional approval note.

        Returns:
            Updated Job in 'approved' status.

        Raises:
            NotFoundError: If job not found.
            JobStateError: If job is not in approval_pending state.
        """
        updated_job = await self._repo.process_approval(
            job_id=job_id,
            tenant_id=tenant_id,
            approved=True,
            approved_by=approved_by,
            note=note,
        )
        if updated_job is None:
            # Could be not found OR wrong state
            existing = await self._repo.get_by_id(job_id, tenant_id)
            if existing is None:
                raise NotFoundError(f"Job '{job_id}' not found.")
            raise JobStateError(
                f"Job '{job_id}' cannot be approved in its current state: '{existing.status}'. "
                "Only jobs in 'approval_pending' state can be approved."
            )

        await self._repo.add_log(
            job_id=job_id,
            event="job.approved",
            message=f"Job approved by '{approved_by}'",
            level="INFO",
            context={"approved_by": approved_by, "note": note},
        )

        logger.info(
            "job.approved",
            job_id=str(job_id),
            approved_by=approved_by,
        )

        # Trigger viaSocket dispatch after approval
        # (viaSocket service will be wired in Phase 7)
        await self._trigger_post_approval_dispatch(updated_job)

        return updated_job

    async def reject_job(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        rejected_by: str,
        note: str | None = None,
    ) -> Job:
        """
        Reject a notebook_to_blog job — prevents viaSocket dispatch.

        Args:
            job_id:       UUID of the job.
            tenant_id:    Requesting tenant UUID.
            rejected_by:  Rejecter identifier.
            note:         Optional rejection reason.

        Returns:
            Updated Job in 'rejected' status.

        Raises:
            NotFoundError: If job not found.
            JobStateError: If job is not in approval_pending state.
        """
        updated_job = await self._repo.process_approval(
            job_id=job_id,
            tenant_id=tenant_id,
            approved=False,
            approved_by=rejected_by,
            note=note,
        )
        if updated_job is None:
            existing = await self._repo.get_by_id(job_id, tenant_id)
            if existing is None:
                raise NotFoundError(f"Job '{job_id}' not found.")
            raise JobStateError(
                f"Job '{job_id}' cannot be rejected in current state: '{existing.status}'."
            )

        await self._repo.add_log(
            job_id=job_id,
            event="job.rejected",
            message=f"Job rejected by '{rejected_by}'",
            level="INFO",
            context={"rejected_by": rejected_by, "note": note},
        )

        logger.info("job.rejected", job_id=str(job_id), rejected_by=rejected_by)
        return updated_job

    # -------------------------------------------------------------------------
    # Worker Callbacks (called by Celery workers, not API routes)
    # -------------------------------------------------------------------------

    async def on_worker_started(self, job_id: uuid.UUID) -> None:
        """
        Called by Celery worker when it begins processing a job.

        Args:
            job_id: UUID of the job being processed.
        """
        await self._repo.mark_started(job_id)

        from engine.core.events import event_bus, SystemEvent
        await event_bus.emit(SystemEvent(
            type="job.status_changed",
            payload={"job_id": str(job_id), "status": "running"}
        ))

        await self._repo.add_log(
            job_id=job_id,
            event="job.worker_started",
            message="Worker picked up and started processing the job",
            level="INFO",
        )

    async def on_worker_completed(
        self,
        job_id: uuid.UUID,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """
        Called by Celery worker when job execution finishes.

        Args:
            job_id:  UUID of the job.
            status:  Terminal status (success/failed/partial).
            result:  Module output dict.
            error:   Error message on failure.
        """
        await self._repo.mark_completed(
            job_id=job_id,
            status=status,
            result=result,
            error=error,
        )

        from engine.core.events import event_bus, SystemEvent
        event_type = "job.completed" if status == "success" else "job.failed"
        await event_bus.emit(SystemEvent(
            type=event_type,
            payload={"job_id": str(job_id), "status": status, "error": error}
        ))

        level = "INFO" if status == "success" else "ERROR" if status == "failed" else "WARNING"
        await self._repo.add_log(
            job_id=job_id,
            event=f"job.{status}",
            message=f"Job completed with status '{status}'",
            level=level,
            context={"status": status, "has_error": error is not None},
        )

    async def on_worker_retry(self, job_id: uuid.UUID, reason: str) -> None:
        """
        Called by Celery worker before retrying a failed job.

        Args:
            job_id:  UUID of the job.
            reason:  Why this retry is happening.
        """
        await self._repo.increment_retry_count(job_id)
        await self._repo.add_log(
            job_id=job_id,
            event="job.retrying",
            message=f"Job retry triggered: {reason}",
            level="WARNING",
            context={"reason": reason},
        )

    # -------------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------------

    async def get_status_counts(self, tenant_id: uuid.UUID) -> dict[str, int]:
        """
        Get job counts by status for analytics dashboard.

        Args:
            tenant_id: Tenant UUID.

        Returns:
            Dict of status → count.
        """
        return await self._repo.count_by_status(tenant_id)

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _validate_module(module: str) -> None:
        """
        Validate that the requested module is supported.

        Args:
            module: Module name string.

        Raises:
            ValidationError: If module is not recognized.
        """
        valid_modules = {
            "scaffolder",
            "test_generator",
            "docs_generator",
            "changelog_generator",
            "notebook_to_blog",
        }
        if module not in valid_modules:
            raise ValidationError(
                f"Unknown module '{module}'. "
                f"Valid modules: {', '.join(sorted(valid_modules))}"
            )

    async def _trigger_post_approval_dispatch(self, job: Job) -> None:
        """
        Trigger viaSocket dispatch after a job is approved.
        """
        logger.info(
            "job.dispatch_triggered",
            job_id=str(job.id),
            module=job.module,
        )
        from engine.core.queue.celery_app import celery_app
        celery_app.send_task(
            "engine.workers.viasocket_dispatcher.dispatch_webhook",
            kwargs={
                "job_id": str(job.id),
                "tenant_id": str(job.tenant_id),
                "event_name": "job_approved",
                "module": job.module,
                "data": job.result or {},
            },
            queue="shipfaster.low",
        )

    async def delete_job(self, job_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Delete a job and its associated logs/artifacts from database."""
        job = await self._repo.get_by_id(job_id=job_id, tenant_id=tenant_id)
        if not job:
            raise NotFoundError(f"Job {job_id} not found or access denied")
            
        await self._repo.delete(job_id=job_id)
        await self._session.commit()
