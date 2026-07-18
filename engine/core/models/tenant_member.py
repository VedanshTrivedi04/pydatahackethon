"""
TenantMember Model.

Association table linking Users to Tenants, with an assigned RBAC role.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.models.base import TimestampedModel

if TYPE_CHECKING:
    from engine.core.models.tenant import Tenant
    from engine.core.models.user import User


class TenantMember(TimestampedModel):
    """
    RBAC mapping: Which User belongs to which Tenant, and in what Role.
    """

    __tablename__ = "tenant_members"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_tenant_member_user_tenant"),
        {"comment": "User roles within a specific tenant"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="developer",
        server_default="developer",
        comment="RBAC role: owner | admin | developer | viewer",
    )

    # --- Relationships ---
    user: Mapped["User"] = relationship(
        "User",
        back_populates="tenant_memberships",
        lazy="selectin",
    )
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="members",
        lazy="selectin",
    )
