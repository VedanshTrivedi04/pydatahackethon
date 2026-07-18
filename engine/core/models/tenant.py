"""
Tenant and TenantSecret Models.

Tenants are the core multi-tenancy primitive. Every resource in the system
(jobs, artifacts, webhooks) belongs to exactly one tenant.

TenantSecret stores hashed API keys — the plain-text key is NEVER stored.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.models.base import TimestampedModel


class Tenant(TimestampedModel):
    """
    Represents a single customer / organization tenant.

    Every inbound API request is resolved to a tenant via their API key.
    All downstream data is scoped to this tenant — no cross-tenant access ever.
    """

    __tablename__ = "tenants"
    __table_args__ = (
        Index("ix_tenants_is_active", "is_active"),
        Index("ix_tenants_created_at", "created_at"),
        {"comment": "Multi-tenant organization registry"},
    )

    # --- Identity ---
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable tenant / organization name",
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe unique identifier for the tenant",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Primary contact email for the tenant",
    )

    # --- Integrations ---
    github_app_installation_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="GitHub App installation ID for this tenant's org/repos",
    )
    viasocket_webhook_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Tenant-specific viaSocket outbound webhook URL",
    )
    github_webhook_secret: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Hashed GitHub webhook secret for signature verification",
    )

    # --- Status ---
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether this tenant is currently active and allowed to use the platform",
    )
    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="free",
        server_default="free",
        comment="Subscription plan tier: free | pro | enterprise",
    )

    # --- Relationships ---
    secrets: Mapped[list["TenantSecret"]] = relationship(
        "TenantSecret",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="select",
    )
    jobs: Mapped[list] = relationship(
        "Job",
        back_populates="tenant",
        lazy="select",
    )
    webhook_events: Mapped[list] = relationship(
        "WebhookEvent",
        back_populates="tenant",
        lazy="select",
    )
    llm_usages: Mapped[list] = relationship(
        "LLMUsage",
        back_populates="tenant",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug!r} plan={self.plan!r}>"


class TenantSecret(TimestampedModel):
    """
    Stores a hashed API key for a tenant.

    A tenant can have multiple API keys (e.g. production + dev + CI).
    The raw key is shown exactly once to the user on creation.
    Only the SHA-256 hash is stored here — it is never reversible.
    """

    __tablename__ = "tenant_secrets"
    __table_args__ = (
        Index("ix_tenant_secrets_key_hash", "key_hash", unique=True),
        Index("ix_tenant_secrets_tenant_id", "tenant_id"),
        {"comment": "Hashed API keys for tenant authentication"},
    )

    # --- Foreign Key ---
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner tenant",
    )

    # --- Key Data ---
    key_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        comment="SHA-256 hex digest of the raw API key — never store plaintext",
    )
    key_prefix: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="First 8 chars of the raw key for display identification (sf_xxxxxxxx...)",
    )
    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="User-assigned label for this key (e.g. 'CI Key', 'Dev Key')",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether this specific key is currently valid",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp of last successful authentication with this key",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Optional expiry timestamp — NULL means never expires",
    )

    # --- Relationships ---
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="secrets",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<TenantSecret id={self.id} prefix={self.key_prefix!r} active={self.is_active}>"
