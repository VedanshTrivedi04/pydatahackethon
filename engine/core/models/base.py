"""
Base SQLAlchemy Model.

All domain models inherit from TimestampedModel which provides:
- UUID primary key (auto-generated)
- created_at / updated_at timestamps (auto-managed)
- soft-delete support (deleted_at)
- A clean __repr__ for debugging
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.config.database import Base


def utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


class TimestampedModel(Base):
    """
    Abstract base model with UUID PK and auto-managed timestamps.

    This is NOT a concrete table — it uses __abstract__ = True
    so SQLAlchemy won't try to create a 'timestamped_model' table.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        comment="Universally Unique Identifier — primary key",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        comment="Record creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        comment="Record last-updated timestamp (UTC)",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Soft-delete timestamp (NULL = active record)",
    )

    @property
    def is_deleted(self) -> bool:
        """Return True if this record has been soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark record as soft-deleted without physical removal."""
        self.deleted_at = utcnow()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"
