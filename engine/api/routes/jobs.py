"""
Job API Routes — /api/v1/jobs

This is the primary API contract for Dev 2's frontend dashboard.

Routes:
    POST   /api/v1/jobs                              → Submit a new job
    GET    /api/v1/jobs                              → List jobs (paginated, filterable)
    GET    /api/v1/jobs/{job_id}                     → Get job detail (+ logs + artifacts)
    GET    /api/v1/jobs/{job_id}/status              → Lightweight status poll (for polling)
    POST   /api/v1/jobs/{job_id}/approve             → Approve notebook_to_blog job
    POST   /api/v1/jobs/{job_id}/reject              → Reject notebook_to_blog job
    GET    /api/v1/jobs/{job_id}/logs                → Get full execution log
    GET    /api/v1/jobs/stats                        → Job counts by status (dashboard widget)

All routes require authentication (Bearer API key).
All routes are strictly tenant-scoped — jobs from other tenants return 404.

OpenAPI schema published at GET /api/v1/openapi.json for Dev 2 client generation.
"""

import uuid

from fastapi import APIRouter, Depends, Query, Request, status

from engine.api.dependencies.auth import get_current_tenant
from engine.api.schemas.job import (
    ApproveJobRequest,
    JobDetailResponse,
    JobDetailSchema,
    JobListResponse,
    JobLogSchema,
    JobResponse,
    JobSchema,
    JobStatusCountsResponse,
    RejectJobRequest,
    SubmitJobRequest,
)
from engine.config.database import get_db_session
from engine.core.jobs.repository import JobRepository
from engine.core.jobs.service import JobService
from engine.core.models.tenant import Tenant
from engine.utils.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = get_logger(__name__)


# =============================================================================
# Dependency: Job Service
# =============================================================================

async def get_job_service(
    session: AsyncSession = Depends(get_db_session),
) -> JobService:
    """Provide a request-scoped JobService instance."""
    repo = JobRepository(session)
    return JobService(session=session, repository=repo)


# =============================================================================
# Routes
# =============================================================================

@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a new automation job",
    description=(
        "Creates a job and enqueues it for async execution by the Celery worker. "
        "Returns immediately with status='queued'. "
        "Poll `GET /api/v1/jobs/{job_id}/status` for updates, "
        "or use `GET /api/v1/jobs/{job_id}` for full details."
    ),
)
async def submit_job(
    body: SubmitJobRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    """Submit a new job for async execution."""
    job = await service.submit_job(
        tenant_id=current_tenant.id,
        module=body.module,
        payload=body.payload,
        trigger="api",
        priority=body.priority,
    )
    logger.info(
        "api.job_submitted",
        job_id=str(job.id),
        module=job.module,
        tenant_id=str(current_tenant.id),
    )
    return JobResponse(success=True, job=JobSchema.model_validate(job))


@router.get(
    "",
    response_model=JobListResponse,
    summary="List jobs",
    description=(
        "Returns a paginated list of jobs for the authenticated tenant. "
        "Filter by module and/or status. Results are sorted by created_at desc."
    ),
)
async def list_jobs(
    module: str | None = Query(
        default=None,
        description="Filter by module: scaffolder | test_generator | docs_generator | changelog_generator | notebook_to_blog",
    ),
    job_status: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status: queued | running | success | failed | partial | approval_pending | approved | rejected | cancelled",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Results per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    current_tenant: Tenant = Depends(get_current_tenant),
    service: JobService = Depends(get_job_service),
) -> JobListResponse:
    """List all jobs for the authenticated tenant."""
    jobs, total = await service.list_jobs(
        tenant_id=current_tenant.id,
        module=module,
        status=job_status,
        limit=limit,
        offset=offset,
    )
    return JobListResponse(
        success=True,
        jobs=[JobSchema.model_validate(j) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
        filters={"module": module, "status": job_status},
    )


@router.get(
    "/stats",
    response_model=JobStatusCountsResponse,
    summary="Job statistics",
    description="Returns job counts grouped by status. Used by the dashboard overview widget.",
)
async def get_job_stats(
    current_tenant: Tenant = Depends(get_current_tenant),
    service: JobService = Depends(get_job_service),
) -> JobStatusCountsResponse:
    """Get job counts by status for the tenant dashboard."""
    counts = await service.get_status_counts(current_tenant.id)
    return JobStatusCountsResponse(
        success=True,
        counts=counts,
        total=sum(counts.values()),
    )


@router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    summary="Get job detail",
    description=(
        "Returns full job details including execution logs and artifact metadata. "
        "Returns 404 if the job doesn't belong to the authenticated tenant."
    ),
)
async def get_job(
    job_id: uuid.UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: JobService = Depends(get_job_service),
) -> JobDetailResponse:
    """Get full details for a single job."""
    job = await service.get_job(
        job_id=job_id,
        tenant_id=current_tenant.id,
        include_logs=True,
        include_artifacts=True,
    )
    return JobDetailResponse(
        success=True,
        job=JobDetailSchema.model_validate(job),
    )


@router.get(
    "/{job_id}/status",
    summary="Poll job status",
    description=(
        "Lightweight status endpoint for polling without loading logs/artifacts. "
        "Recommended for real-time status polling in the frontend."
    ),
    response_model=dict,
)
async def get_job_status(
    job_id: uuid.UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: JobService = Depends(get_job_service),
) -> dict:
    """Lightweight job status poll — returns just status, id, and timestamps."""
    job = await service.get_job(
        job_id=job_id,
        tenant_id=current_tenant.id,
        include_logs=False,
        include_artifacts=False,
    )
    return {
        "success": True,
        "job_id": str(job.id),
        "status": job.status,
        "module": job.module,
        "requires_approval": job.requires_approval,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "retry_count": job.retry_count,
        "error": job.error,
    }


@router.get(
    "/{job_id}/logs",
    summary="Get job execution logs",
    description="Returns the full execution log timeline for a job.",
    response_model=dict,
)
async def get_job_logs(
    job_id: uuid.UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: JobService = Depends(get_job_service),
) -> dict:
    """Get all execution log entries for a job."""
    logs = await service.get_job_logs(
        job_id=job_id,
        tenant_id=current_tenant.id,
    )
    return {
        "success": True,
        "job_id": str(job_id),
        "logs": [JobLogSchema.model_validate(log).model_dump() for log in logs],
        "count": len(logs),
    }


@router.post(
    "/{job_id}/approve",
    response_model=JobResponse,
    summary="Approve a job for publishing",
    description=(
        "Approves a `notebook_to_blog` job for viaSocket publication. "
        "Only valid for jobs in `approval_pending` status. "
        "After approval, the result will be dispatched to viaSocket automatically."
    ),
)
async def approve_job(
    job_id: uuid.UUID,
    body: ApproveJobRequest,
    request: Request,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    """Approve a notebook_to_blog job for viaSocket publication."""
    # Use tenant key prefix as the approver identifier (Dev 2 can pass their user ID here)
    approver = f"tenant:{current_tenant.slug}"

    job = await service.approve_job(
        job_id=job_id,
        tenant_id=current_tenant.id,
        approved_by=approver,
        note=body.note,
    )
    logger.info(
        "api.job_approved",
        job_id=str(job_id),
        tenant_id=str(current_tenant.id),
    )
    return JobResponse(success=True, job=JobSchema.model_validate(job))


@router.post(
    "/{job_id}/reject",
    response_model=JobResponse,
    summary="Reject a job",
    description=(
        "Rejects a `notebook_to_blog` job — prevents viaSocket publication. "
        "Only valid for jobs in `approval_pending` status."
    ),
)
async def reject_job(
    job_id: uuid.UUID,
    body: RejectJobRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    """Reject a notebook_to_blog job."""
    rejecter = f"tenant:{current_tenant.slug}"
    job = await service.reject_job(
        job_id=job_id,
        tenant_id=current_tenant.id,
        rejected_by=rejecter,
        note=body.note,
    )
    logger.info(
        "api.job_rejected",
        job_id=str(job_id),
        tenant_id=str(current_tenant.id),
    )
    return JobResponse(success=True, job=JobSchema.model_validate(job))


@router.delete(
    "/{job_id}",
    summary="Delete a job",
    description="Deletes a job from the database including its logs.",
)
async def delete_job(
    job_id: uuid.UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: JobService = Depends(get_job_service),
):
    """Delete a job by ID."""
    await service.delete_job(job_id=job_id, tenant_id=current_tenant.id)
    return {"success": True, "message": f"Job {job_id} deleted successfully"}
