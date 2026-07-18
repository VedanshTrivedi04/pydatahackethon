"""
Analytics API Routes — /api/v1/analytics

Endpoints for dashboard metrics (Job statuses, LLM cost & token usage).
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from engine.api.middleware.auth import require_auth
from engine.api.schemas.analytics import JobSummaryResponse, LLMUsageSummaryResponse
from engine.config.database import get_db_session
from engine.core.jobs.repository import JobRepository
from engine.core.llm.usage_tracker import LLMUsageTracker
from engine.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


async def get_job_repository(session: AsyncSession = Depends(get_db_session)) -> JobRepository:
    """Dependency injection for JobRepository."""
    return JobRepository(session=session)


async def get_usage_tracker(session: AsyncSession = Depends(get_db_session)) -> LLMUsageTracker:
    """Dependency injection for LLMUsageTracker."""
    return LLMUsageTracker(session=session)


@router.get(
    "/jobs/summary",
    response_model=JobSummaryResponse,
    summary="Get Job Status Summary",
    description="Returns aggregate counts of jobs by status for the authenticated tenant.",
)
async def get_job_summary(
    repo: JobRepository = Depends(get_job_repository),
    auth: dict[str, Any] = Depends(require_auth),
) -> dict[str, int]:
    """Get aggregated job counts."""
    tenant_id = uuid.UUID(auth["tenant_id"])
    
    # Returns dict mapping status (e.g. 'success') to count
    counts = await repo.count_by_status(tenant_id)
    
    total = sum(counts.values())
    
    return {
        "total": total,
        "queued": counts.get("queued", 0),
        "running": counts.get("running", 0),
        "success": counts.get("success", 0),
        "failed": counts.get("failed", 0),
        "approval_pending": counts.get("approval_pending", 0),
        "partial": counts.get("partial", 0),
        "cancelled": counts.get("cancelled", 0),
    }


@router.get(
    "/llm/usage",
    response_model=LLMUsageSummaryResponse,
    summary="Get LLM Usage & Cost Summary",
    description="Returns total token consumption and estimated USD cost for the last 30 days.",
)
async def get_llm_usage_summary(
    tracker: LLMUsageTracker = Depends(get_usage_tracker),
    auth: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    """Get 30-day LLM usage aggregates."""
    tenant_id = uuid.UUID(auth["tenant_id"])
    
    summary = await tracker.get_usage_summary(tenant_id, days=30)
    
    return {
        "total_requests": summary.get("total_calls", 0),
        "total_input_tokens": summary.get("total_prompt_tokens", 0),
        "total_output_tokens": summary.get("total_completion_tokens", 0),
        "total_tokens": summary.get("total_tokens", 0),
        "total_cost_usd": summary.get("total_cost_usd", 0.0),
    }
