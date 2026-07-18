"""
User Model.

Represents a human identity that can log into the ShipFaster platform.
Users are linked to one or more Tenants via the TenantMember model.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.models.base import TimestampedModel

if TYPE_CHECKING:
    from engine.core.models.tenant_member import TenantMember


class User(TimestampedModel):
    """
    Human identity for platform access.
    """

    __tablename__ = "users"
    __table_args__ = {"comment": "Human user identities"}

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Primary login email",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Passlib (bcrypt) hashed password",
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User's display name",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default="true",
        comment="Soft delete / ban flag",
    )

    # --- Relationships ---
    tenant_memberships: Mapped[list["TenantMember"]] = relationship(
        "TenantMember",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
