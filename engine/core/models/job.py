"""
Job and JobLog Models.

Jobs are the central work unit in ShipFaster. Every automation request
(scaffold, test-gen, docs, changelog, notebook-to-blog) is a Job.

JobLog stores a granular execution timeline — every state transition,
worker event, and error gets a row here for auditability.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.models.base import TimestampedModel


# --- Constants / allowed values ---
MODULE_TYPES = (
    "scaffolder",
    "test_generator",
    "docs_generator",
    "changelog_generator",
    "notebook_to_blog",
)

JOB_STATUSES = (
    "queued",
    "running",
    "success",
    "failed",
    "partial",
    "cancelled",
    "approval_pending",
    "approved",
    "rejected",
)

TRIGGER_TYPES = (
    "api",
    "webhook_github",
    "webhook_ci",
    "mcp",
    "cli",
    "scheduled",
)


class Job(TimestampedModel):
    """
    Represents a single automation job submitted to ShipFaster.

    A job is:
    - Created by a tenant (via API, webhook, CLI, or MCP)
    - Picked up by a Celery worker
    - Executed by the appropriate module handler (Dev 1's code)
    - Result persisted back here
    - Optionally dispatched to viaSocket on completion
    """

    __tablename__ = "jobs"
    __table_args__ = (
        # Composite index — most common query pattern
        Index("ix_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_jobs_tenant_module", "tenant_id", "module"),
        Index("ix_jobs_created_at", "created_at"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_celery_task_id", "celery_task_id"),
        CheckConstraint(
            f"module IN {MODULE_TYPES}",
            name="ck_jobs_module",
        ),
        CheckConstraint(
            f"status IN {JOB_STATUSES}",
            name="ck_jobs_status",
        ),
        CheckConstraint(
            f"trigger IN {TRIGGER_TYPES}",
            name="ck_jobs_trigger",
        ),
        {"comment": "Central job registry — every automation request is a job"},
    )

    # --- Tenant FK ---
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Owning tenant — all access is scoped to this",
    )

    # --- Module / Type ---
    module: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Automation module: scaffolder | test_generator | docs_generator | changelog_generator | notebook_to_blog",
    )
    trigger: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="api",
        server_default="api",
        comment="What initiated this job: api | webhook_github | webhook_ci | mcp | cli | scheduled",
    )

    # --- Status ---
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="queued",
        server_default="queued",
        index=True,
        comment="Current job status",
    )

    # --- Data ---
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Module-specific input payload (validated per module)",
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Module output — ModuleResult.output from Dev 1's handler",
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if job failed — never expose raw tracebacks in API responses",
    )

    # --- Queue ---
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Celery task UUID — used for status tracking and idempotency",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of Celery retries attempted",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
        comment="Queue priority (1=highest, 10=lowest)",
    )

    # --- Timing ---
    started_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp when worker picked up and started executing the job",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp when job reached terminal state (success/failed/cancelled)",
    )

    # --- Approval Flow (notebook_to_blog only) ---
    requires_approval: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        comment="True for notebook_to_blog jobs — must be approved before viaSocket dispatch",
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Identifier of who approved/rejected (email or user ID from Dev 2)",
    )
    approval_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional note from the approver/rejecter",
    )

    # --- Relationships ---
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]
        "Tenant",
        back_populates="jobs",
        lazy="select",
    )
    artifacts: Mapped[list["Artifact"]] = relationship(  # type: ignore[name-defined]
        "Artifact",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="select",
    )
    logs: Mapped[list["JobLog"]] = relationship(
        "JobLog",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobLog.created_at",
        lazy="select",
    )
    viasocket_dispatches: Mapped[list["ViaSocketDispatch"]] = relationship(  # type: ignore[name-defined]
        "ViaSocketDispatch",
        back_populates="job",
        lazy="select",
    )
    llm_usages: Mapped[list["LLMUsage"]] = relationship(  # type: ignore[name-defined]
        "LLMUsage",
        back_populates="job",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} module={self.module!r} status={self.status!r}>"


class JobLog(TimestampedModel):
    """
    Granular execution log for a Job.

    Every state transition, worker event, LLM call, and error
    gets its own row. This is the audit trail for debugging and
    support tickets — never delete these.
    """

    __tablename__ = "job_logs"
    __table_args__ = (
        Index("ix_job_logs_job_id", "job_id"),
        Index("ix_job_logs_level", "level"),
        {"comment": "Granular execution timeline for each job"},
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="INFO",
        comment="Log level: DEBUG | INFO | WARNING | ERROR | CRITICAL",
    )
    event: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Machine-readable event name (e.g. 'job.started', 'llm.called')",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable log message",
    )
    context: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured key-value context for this log event",
    )

    # --- Relationships ---
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="logs",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<JobLog job_id={self.job_id} event={self.event!r} level={self.level!r}>"
