"""
Audit and API Log Models.

AuditLog: Immutable record of every security-significant action
          (tenant created, key revoked, job approved, etc.)

APILog:   Per-request HTTP log with correlation IDs, latency, status.
          Stored in DB for querying — also emitted as structured logs.
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.core.models.base import TimestampedModel


class AuditLog(TimestampedModel):
    """
    Immutable audit trail for all security-significant actions.

    These records must NEVER be deleted or modified.
    They form the chain of custody for compliance and forensics.

    Written by:
    - Auth middleware (failed auth attempts)
    - Tenant service (tenant CRUD)
    - Job service (status transitions, approvals)
    - Webhook receiver (signature failures, payload processing)
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_tenant_id", "tenant_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_actor", "actor"),
        Index("ix_audit_logs_created_at", "created_at"),
        {"comment": "Immutable audit trail — never delete these records"},
    )

    # --- Who ---
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Tenant context (NULL for pre-auth events like failed key lookups)",
    )
    actor: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Who performed the action (API key prefix, system, webhook source)",
    )
    actor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="api_key",
        comment="Actor type: api_key | system | webhook | scheduler",
    )

    # --- What ---
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Action name (e.g. 'tenant.created', 'job.approved', 'key.revoked')",
    )
    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Resource type affected (tenant, job, artifact, api_key)",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="UUID of the affected resource",
    )

    # --- Context ---
    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Correlation request ID from the HTTP request that triggered this",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address (IPv4 or IPv6)",
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="HTTP User-Agent header from the request",
    )
    old_value: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="State before the action (for update/delete actions)",
    )
    new_value: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="State after the action (for create/update actions)",
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Additional action-specific context",
    )
    outcome: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        comment="Result: success | failure | partial",
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r} outcome={self.outcome!r}>"


class APILog(TimestampedModel):
    """
    Per-HTTP-request access log stored in the database.

    Supplements structured stdout logs with queryable storage.
    Enables:
    - SLA analysis (slow endpoint detection)
    - Tenant-level API usage reports
    - Debugging specific failed requests by correlation ID
    """

    __tablename__ = "api_logs"
    __table_args__ = (
        Index("ix_api_logs_tenant_id", "tenant_id"),
        Index("ix_api_logs_request_id", "request_id", unique=True),
        Index("ix_api_logs_status_code", "status_code"),
        Index("ix_api_logs_created_at", "created_at"),
        Index("ix_api_logs_path", "path"),
        {"comment": "HTTP API request access log for analytics and debugging"},
    )

    # --- Request Identity ---
    request_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Unique request ID injected by middleware (also in X-Request-ID response header)",
    )
    correlation_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Client-provided correlation ID for distributed tracing",
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Resolved tenant (NULL for unauthenticated requests)",
    )

    # --- HTTP ---
    method: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="HTTP method: GET | POST | PUT | DELETE | PATCH",
    )
    path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Request path (no query string, no PII)",
    )
    status_code: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="HTTP response status code",
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total request processing time in milliseconds",
    )

    # --- Client Info ---
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address",
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="HTTP User-Agent",
    )
    error_detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error summary for non-2xx responses",
    )

    def __repr__(self) -> str:
        return f"<APILog {self.method} {self.path} {self.status_code} ({self.latency_ms}ms)>"
