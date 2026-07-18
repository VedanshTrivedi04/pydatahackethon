"""
Job Repository — Infrastructure Layer.

ALL database queries for the jobs and job_logs tables live here.
No SQL anywhere else — service layer calls repository methods only.

Follows the Repository Pattern from Clean Architecture:
- One responsibility: data access for Job entities
- All queries are async and tenant-scoped
- Service layer is completely decoupled from SQLAlchemy
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from engine.core.models.job import Job, JobLog


class JobRepository:
    """
    Data access object for Job and JobLog entities.

    Every query enforces tenant_id scoping — there is no query
    in this class that reads across tenants. This is the
    architectural enforcement of multi-tenancy at the data layer.

    Args:
        session: Request-scoped async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------------
    # Job CRUD
    # -------------------------------------------------------------------------

    async def create(self, job: Job) -> Job:
        """
        Persist a new Job to the database.

        Args:
            job: Job instance (not yet in session).

        Returns:
            Persisted Job with DB-generated id and timestamps.
        """
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def get_by_id(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        load_logs: bool = False,
        load_artifacts: bool = False,
    ) -> Job | None:
        """
        Fetch a single job by ID, scoped to the given tenant.

        Args:
            job_id:         UUID of the job.
            tenant_id:      UUID of the requesting tenant (ownership check).
            load_logs:      Eagerly load job_logs relationship.
            load_artifacts: Eagerly load artifacts relationship.

        Returns:
            Job if found and owned by the tenant, None otherwise.
        """
        stmt = select(Job).where(
            Job.id == job_id,
            Job.tenant_id == tenant_id,
        )
        if load_logs:
            stmt = stmt.options(selectinload(Job.logs))
        if load_artifacts:
            stmt = stmt.options(selectinload(Job.artifacts))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_celery_task_id(self, celery_task_id: str) -> Job | None:
        """
        Fetch a job by its Celery task ID.

        Used for idempotency check in the worker — if a task is
        accidentally delivered twice, we skip re-execution.

        Args:
            celery_task_id: Celery task UUID string.

        Returns:
            Job if found, None otherwise.
        """
        stmt = select(Job).where(Job.celery_task_id == celery_task_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_tenant(
        self,
        tenant_id: uuid.UUID,
        module: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """
        Paginated list of jobs for a tenant with optional filtering.

        Args:
            tenant_id: Owning tenant UUID.
            module:    Filter by module type.
            status:    Filter by job status.
            limit:     Max results (capped at 200).
            offset:    Pagination offset.

        Returns:
            Tuple of (jobs_list, total_count).
        """
        filters = [Job.tenant_id == tenant_id]
        if module:
            filters.append(Job.module == module)
        if status:
            filters.append(Job.status == status)

        where_clause = and_(*filters)

        # Count query
        count_stmt = select(func.count(Job.id)).where(where_clause)
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        stmt = (
            select(Job)
            .where(where_clause)
            .order_by(Job.created_at.desc())
            .limit(min(limit, 200))
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def update_status(
        self,
        job_id: uuid.UUID,
        status: str,
        **extra_fields: Any,
    ) -> Job | None:
        """
        Update job status and any additional fields atomically.

        Used by the Celery worker to transition job state.

        Args:
            job_id:       UUID of the job to update.
            status:       New status value.
            **extra_fields: Additional fields to set (e.g. result, error, completed_at).

        Returns:
            Updated Job or None if not found.
        """
        values: dict[str, Any] = {"status": status, **extra_fields}
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(**values)
            .returning(Job)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_celery_task_id(
        self,
        job_id: uuid.UUID,
        celery_task_id: str,
    ) -> None:
        """
        Set the Celery task ID on a job after it is enqueued.

        Args:
            job_id:          UUID of the job.
            celery_task_id:  Celery task UUID from AsyncResult.
        """
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(celery_task_id=celery_task_id, status="queued")
        )
        await self._session.execute(stmt)

    async def mark_started(self, job_id: uuid.UUID) -> None:
        """
        Mark a job as running with a started_at timestamp.

        Called at the beginning of execute_module_task.
        """
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(status="running", started_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)

    async def mark_completed(
        self,
        job_id: uuid.UUID,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """
        Mark a job as completed (success, failed, or partial).

        Args:
            job_id:  UUID of the job.
            status:  Terminal status: success | failed | partial.
            result:  Module output dict (on success/partial).
            error:   Error message (on failed/partial).
        """
        values: dict[str, Any] = {
            "status": status,
            "completed_at": datetime.now(timezone.utc),
        }
        if result is not None:
            values["result"] = result
        if error is not None:
            values["error"] = error

        stmt = update(Job).where(Job.id == job_id).values(**values)
        await self._session.execute(stmt)

    async def mark_approval_pending(self, job_id: uuid.UUID) -> None:
        """
        Transition job to approval_pending state (notebook_to_blog only).

        Args:
            job_id: UUID of the job.
        """
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(status="approval_pending", requires_approval=True)
        )
        await self._session.execute(stmt)

    async def process_approval(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        approved: bool,
        approved_by: str,
        note: str | None = None,
    ) -> Job | None:
        """
        Process an approve or reject action on a job.

        Only works if the job is in approval_pending state and
        belongs to the requesting tenant.

        Args:
            job_id:      UUID of the job.
            tenant_id:   Requesting tenant UUID (ownership check).
            approved:    True to approve, False to reject.
            approved_by: Identifier of the approver (email/user_id from Dev 2).
            note:        Optional approval/rejection note.

        Returns:
            Updated Job or None if not found / wrong state.
        """
        new_status = "approved" if approved else "rejected"
        stmt = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.tenant_id == tenant_id,
                Job.status == "approval_pending",
            )
            .values(
                status=new_status,
                approved_by=approved_by,
                approval_note=note,
            )
            .returning(Job)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_retry_count(self, job_id: uuid.UUID) -> None:
        """Increment the retry counter on a job."""
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(retry_count=Job.retry_count + 1)
        )
        await self._session.execute(stmt)

    # -------------------------------------------------------------------------
    # Job Log
    # -------------------------------------------------------------------------

    async def add_log(
        self,
        job_id: uuid.UUID,
        event: str,
        message: str,
        level: str = "INFO",
        context: dict[str, Any] | None = None,
    ) -> JobLog:
        """
        Append a log entry to a job's execution timeline.

        Args:
            job_id:   UUID of the job.
            event:    Machine-readable event name (e.g. 'job.started').
            message:  Human-readable description.
            level:    Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL).
            context:  Optional structured context dict.

        Returns:
            Persisted JobLog instance.
        """
        log = JobLog(
            job_id=job_id,
            event=event,
            message=message,
            level=level,
            context=context,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def get_logs(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[JobLog]:
        """
        Fetch all log entries for a job (verified against tenant ownership).

        Args:
            job_id:    UUID of the job.
            tenant_id: Tenant UUID for ownership verification via JOIN.

        Returns:
            List of JobLog entries ordered by created_at ascending.
        """
        stmt = (
            select(JobLog)
            .join(Job, JobLog.job_id == Job.id)
            .where(
                JobLog.job_id == job_id,
                Job.tenant_id == tenant_id,
            )
            .order_by(JobLog.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Analytics / Aggregations
    # -------------------------------------------------------------------------

    async def count_by_status(self, tenant_id: uuid.UUID) -> dict[str, int]:
        """
        Count jobs grouped by status for a tenant.

        Used by the analytics/dashboard endpoint.

        Args:
            tenant_id: Tenant UUID.

        Returns:
            Dict mapping status → count.
        """
        stmt = (
            select(Job.status, func.count(Job.id))
            .where(Job.tenant_id == tenant_id)
            .group_by(Job.status)
        )
        result = await self._session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
