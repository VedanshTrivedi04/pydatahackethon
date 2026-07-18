"""
WebhookEvent Model.

Every inbound webhook (from GitHub or CI systems) is persisted here
as a raw record BEFORE any processing begins.

This provides:
- Full audit trail of all inbound events
- Ability to replay failed events
- Forensic debugging when a job wasn't triggered
- Protection against lost events (store first, process second)
"""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.models.base import TimestampedModel


WEBHOOK_SOURCES = ("github", "ci", "other")


class WebhookEvent(TimestampedModel):
    """
    Raw inbound webhook event record.

    Store-first approach: the raw payload is persisted immediately
    after signature verification, before any business logic runs.
    If processing fails, the event can be replayed.
    """

    __tablename__ = "webhook_events"
    __table_args__ = (
        # Primary query pattern: find unprocessed events
        Index("ix_webhook_events_processed", "processed"),
        Index("ix_webhook_events_tenant_id", "tenant_id"),
        Index("ix_webhook_events_source_type", "source", "event_type"),
        Index("ix_webhook_events_received_at", "received_at"),
        {"comment": "Inbound webhook events — stored before processing (store-first pattern)"},
    )

    # --- Tenant FK ---
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Tenant this webhook belongs to",
    )

    # --- Event Classification ---
    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Webhook origin: github | ci | other",
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Specific event type from source (e.g. 'push', 'release', 'workflow_run')",
    )
    delivery_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="GitHub X-GitHub-Delivery header — used for deduplication",
    )

    # --- Raw Payload (immutable) ---
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Complete raw webhook payload — never modified after insert",
    )
    headers: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Sanitized inbound HTTP headers (signature header excluded for security)",
    )

    # --- Processing Status ---
    processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
        comment="Whether this event has been successfully processed",
    )
    processing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if processing failed",
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        comment="Job created in response to this webhook (NULL if not yet processed)",
    )

    # --- Timing ---
    received_at: Mapped[Any] = mapped_column(
        nullable=False,
        comment="Timestamp when the webhook request arrived",
    )

    # --- Relationships ---
    tenant: Mapped["Tenant"] = relationship(  # type: ignore[name-defined]
        "Tenant",
        back_populates="webhook_events",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<WebhookEvent id={self.id} source={self.source!r} "
            f"type={self.event_type!r} processed={self.processed}>"
        )
