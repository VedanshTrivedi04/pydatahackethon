"""
Async SQLAlchemy Database Engine and Session Factory.

Provides:
- Async engine creation using asyncpg
- Session factory (AsyncSessionLocal)
- Dependency-injectable async session (get_db_session)
- Base metadata for all models
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from engine.config.settings import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy ORM models.

    All models must inherit from this class to be included
    in metadata and Alembic autogeneration.
    """
    pass


def create_engine() -> AsyncEngine:
    """
    Create and configure the async SQLAlchemy engine.

    Uses asyncpg driver with connection pooling configured
    from application settings.
    """
    connect_args = {}
    if settings.environment == "development":
        connect_args["ssl"] = False

    return create_async_engine(
        url=settings.db.async_url,
        pool_size=settings.db.pool_size,
        max_overflow=settings.db.max_overflow,
        pool_timeout=settings.db.pool_timeout,
        pool_pre_ping=True,        # Test connections before using from pool
        pool_recycle=3600,         # Recycle connections after 1 hour
        echo=settings.db.echo,
        json_serializer=_json_serializer,
        json_deserializer=_json_deserializer,
        connect_args=connect_args,
    )


def _json_serializer(obj: Any) -> str:
    """Custom JSON serializer using orjson for performance."""
    import orjson
    return orjson.dumps(obj).decode()


def _json_deserializer(s: str) -> Any:
    """Custom JSON deserializer using orjson for performance."""
    import orjson
    return orjson.loads(s)


# --- Singletons (created once at module import) ---
engine: AsyncEngine = create_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,       # Don't expire objects after commit
    autoflush=False,               # Manual flush control
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a managed async database session.

    Usage in routes:
        async def my_route(db: AsyncSession = Depends(get_db_session)):
            ...

    Automatically commits on success, rolls back on any exception.
    Always closes the session when done.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """
    Create all tables defined in models.

    Used only in development/testing. Production uses Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """
    Drop all tables. DANGER — only for testing.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
