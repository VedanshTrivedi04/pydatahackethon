"""
LLMUsage Model.

Records every LLM API call made through the centralized llm_client wrapper.

This is the cost visibility layer — every token consumed is tracked
per tenant, per job, per model, with latency and cost estimates.
Critical for:
- Enterprise billing / usage caps
- Cost attribution per tenant
- LLM performance monitoring
- Debugging runaway token usage
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.models.base import TimestampedModel


class LLMUsage(TimestampedModel):
    """
    One row per LLM API call, tracking tokens, cost, and latency.

    Never called directly — always populated by engine.core.llm.client
    after each API call completes (or fails).
    """

    __tablename__ = "llm_usage"
    __table_args__ = (
        Index("ix_llm_usage_tenant_id", "tenant_id"),
        Index("ix_llm_usage_job_id", "job_id"),
        Index("ix_llm_usage_model", "model"),
        Index("ix_llm_usage_created_at", "created_at"),
        {"comment": "Per-call LLM token and cost tracking for billing and observability"},
    )

    # --- Foreign Keys ---
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Tenant charged for this LLM call",
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Job that triggered this LLM call (NULL for system calls)",
    )

    # --- Model Info ---
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="LLM provider: google | anthropic",
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Model identifier (e.g. 'gemini-1.5-pro', 'claude-sonnet-4-6')",
    )

    # --- Token Counts ---
    input_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of input/prompt tokens consumed",
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of output/completion tokens generated",
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total tokens (input + output) for simplified queries",
    )

    # --- Cost Estimation ---
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=8),
        nullable=True,
        comment="Estimated cost in USD based on model pricing at time of call",
    )

    # --- Performance ---
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="End-to-end latency in milliseconds for this LLM call",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of retries before this call succeeded",
    )
    success: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether this LLM call completed successfully",
    )

    # --- Context ---
    operation: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="High-level operation label (e.g. 'scaffold.generate', 'docs.summarize')",
    )
    request_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional request context (system prompt hash, message count, etc.)",
    )

    # --- Relationships ---
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]
        "Tenant",
        back_populates="llm_usages",
        lazy="select",
    )
    job: Mapped["Job"] = relationship(  # type: ignore[name-defined]
        "Job",
        back_populates="llm_usages",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<LLMUsage id={self.id} model={self.model!r} "
            f"tokens={self.total_tokens} cost=${self.estimated_cost_usd}>"
        )
