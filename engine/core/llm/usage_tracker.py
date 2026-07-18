"""
LLM Usage Tracker — Service Layer.

Provides high-level usage analytics and cost reporting
on top of the llm_usage database table.

Used by:
- Admin API: GET /api/v1/analytics/llm-usage
- Cost dashboard widgets
- Rate limiting decisions (daily cost cap enforcement)

This tracker is read-only — it queries but never writes.
Writing happens in LLMClient._persist_usage() automatically.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.models.llm import LLMUsage
from engine.utils.logging import get_logger

logger = get_logger(__name__)


class LLMUsageTracker:
    """
    Query service for LLM usage analytics.

    All queries are tenant-scoped. Admin queries can span all tenants.

    Args:
        session: Async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_usage_summary(
        self,
        tenant_id: uuid.UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get a usage summary for a tenant over the last N days.

        Returns total calls, total tokens, total cost, and per-model breakdown.

        Args:
            tenant_id: Tenant UUID.
            days:      Number of days to look back (default 30).

        Returns:
            Summary dict with totals and per-model breakdown.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Total aggregates
        agg_stmt = select(
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.prompt_tokens).label("total_prompt_tokens"),
            func.sum(LLMUsage.completion_tokens).label("total_completion_tokens"),
            func.sum(LLMUsage.total_tokens).label("total_tokens"),
            func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
            func.avg(LLMUsage.latency_ms).label("avg_latency_ms"),
        ).where(
            and_(
                LLMUsage.tenant_id == tenant_id,
                LLMUsage.created_at >= since,
            )
        )
        agg_result = await self._session.execute(agg_stmt)
        agg_row = agg_result.one()

        # Per-model breakdown
        model_stmt = (
            select(
                LLMUsage.model,
                func.count(LLMUsage.id).label("calls"),
                func.sum(LLMUsage.total_tokens).label("tokens"),
                func.sum(LLMUsage.cost_usd).label("cost_usd"),
                func.avg(LLMUsage.latency_ms).label("avg_latency_ms"),
            )
            .where(
                and_(
                    LLMUsage.tenant_id == tenant_id,
                    LLMUsage.created_at >= since,
                )
            )
            .group_by(LLMUsage.model)
            .order_by(func.sum(LLMUsage.cost_usd).desc())
        )
        model_result = await self._session.execute(model_stmt)

        models = [
            {
                "model": row.model,
                "calls": row.calls,
                "tokens": int(row.tokens or 0),
                "cost_usd": float(round(row.cost_usd or 0, 6)),
                "avg_latency_ms": int(row.avg_latency_ms or 0),
            }
            for row in model_result.all()
        ]

        return {
            "tenant_id": str(tenant_id),
            "period_days": days,
            "since": since.isoformat(),
            "total_calls": agg_row.total_calls or 0,
            "total_prompt_tokens": int(agg_row.total_prompt_tokens or 0),
            "total_completion_tokens": int(agg_row.total_completion_tokens or 0),
            "total_tokens": int(agg_row.total_tokens or 0),
            "total_cost_usd": float(round(agg_row.total_cost_usd or 0, 6)),
            "avg_latency_ms": int(agg_row.avg_latency_ms or 0),
            "by_model": models,
        }

    async def get_daily_cost(
        self,
        tenant_id: uuid.UUID,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Get daily cost breakdown for the last N days.

        Used to render cost graphs on the dashboard.

        Args:
            tenant_id: Tenant UUID.
            days:      Number of days to look back.

        Returns:
            List of {date, cost_usd, calls} dicts, ordered ascending.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = (
            select(
                func.date(LLMUsage.created_at).label("date"),
                func.count(LLMUsage.id).label("calls"),
                func.sum(LLMUsage.cost_usd).label("cost_usd"),
                func.sum(LLMUsage.total_tokens).label("tokens"),
            )
            .where(
                and_(
                    LLMUsage.tenant_id == tenant_id,
                    LLMUsage.created_at >= since,
                )
            )
            .group_by(func.date(LLMUsage.created_at))
            .order_by(func.date(LLMUsage.created_at).asc())
        )
        result = await self._session.execute(stmt)

        return [
            {
                "date": str(row.date),
                "calls": row.calls,
                "cost_usd": float(round(row.cost_usd or 0, 6)),
                "tokens": int(row.tokens or 0),
            }
            for row in result.all()
        ]

    async def get_today_cost(self, tenant_id: uuid.UUID) -> float:
        """
        Get the total LLM cost for today for a tenant.

        Used for daily cost cap enforcement.

        Args:
            tenant_id: Tenant UUID.

        Returns:
            Today's cost in USD.
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        stmt = select(func.sum(LLMUsage.cost_usd)).where(
            and_(
                LLMUsage.tenant_id == tenant_id,
                LLMUsage.created_at >= today_start,
            )
        )
        result = await self._session.execute(stmt)
        cost = result.scalar_one_or_none()
        return float(cost or 0.0)

    async def list_recent_calls(
        self,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        List recent LLM calls for a tenant (or specific job).

        Args:
            tenant_id: Tenant UUID.
            job_id:    Optional job UUID to filter by.
            limit:     Max results.

        Returns:
            List of LLM call records.
        """
        filters = [LLMUsage.tenant_id == tenant_id]
        if job_id:
            filters.append(LLMUsage.job_id == job_id)

        stmt = (
            select(LLMUsage)
            .where(and_(*filters))
            .order_by(LLMUsage.created_at.desc())
            .limit(min(limit, 200))
        )
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        return [
            {
                "id": str(r.id),
                "job_id": str(r.job_id) if r.job_id else None,
                "provider": r.provider,
                "model": r.model,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "cost_usd": float(r.cost_usd or 0),
                "latency_ms": r.latency_ms,
                "finish_reason": r.finish_reason,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ]
