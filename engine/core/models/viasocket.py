"""
ViaSocketDispatch Model.

Records every outbound dispatch attempt to a tenant's viaSocket endpoint.

Each dispatch attempt creates a row — retries create additional rows
with attempt_count incremented. This gives a full retry history.
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.models.base import TimestampedModel


DISPATCH_STATUSES = ("pending", "success", "failed", "retrying", "dead_lettered")


class ViaSocketDispatch(TimestampedModel):
    """
    Audit record for each viaSocket outbound dispatch attempt.

    For each job completion that triggers viaSocket:
    - One or more ViaSocketDispatch rows are created
    - attempt_count tracks which retry this is
    - status_code records the HTTP response from viaSocket
    - On exhausted retries, status → 'dead_lettered'
    """

    __tablename__ = "viasocket_dispatches"
    __table_args__ = (
        Index("ix_viasocket_dispatches_job_id", "job_id"),
        Index("ix_viasocket_dispatches_tenant_id", "tenant_id"),
        Index("ix_viasocket_dispatches_status", "status"),
        {"comment": "Outbound viaSocket dispatch audit log with retry history"},
    )

    # --- Foreign Keys ---
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Job whose completion triggered this dispatch",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Tenant for direct filtering",
    )

    # --- Dispatch Data ---
    event_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="viaSocket event name (from events.py enum)",
    )
    payload_sent: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full JSON payload sent to viaSocket endpoint",
    )
    target_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="viaSocket webhook URL the payload was POSTed to",
    )

    # --- Response ---
    status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="HTTP status code from viaSocket (None if request never completed)",
    )
    response_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Response body from viaSocket (truncated to 2000 chars)",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if dispatch failed at network/transport level",
    )

    # --- Retry Tracking ---
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Which attempt this is (1 = first try, 2 = first retry, etc.)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="Dispatch status: pending | success | failed | retrying | dead_lettered",
    )
    next_retry_at: Mapped[Any] = mapped_column(
        nullable=True,
        comment="When to attempt the next retry (NULL if no retry scheduled)",
    )

    # --- Relationships ---
    job: Mapped["Job"] = relationship(  # type: ignore[name-defined]
        "Job",
        back_populates="viasocket_dispatches",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<ViaSocketDispatch id={self.id} event={self.event_name!r} "
            f"attempt={self.attempt_count} status={self.status!r}>"
        )
