"""
Alembic Migration Environment.

This file is loaded by Alembic on every `alembic` CLI command.

Key responsibilities:
1. Load application settings (DB URL from .env)
2. Import all SQLAlchemy models so their metadata is available
3. Configure the migration runner for both online and offline modes

Uses asyncpg (already installed) instead of psycopg2 via asyncio run_sync.
"""

from logging.config import fileConfig
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config, AsyncConnection
from sqlalchemy import pool

# --- Load alembic logging config ---
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Import app settings and all models ---
# Models must be imported here so their tables appear in Base.metadata
# and Alembic can detect schema changes via autogenerate.
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"), override=True)

from engine.config.settings import get_settings
from engine.config.database import Base

# Import all models — this registers their Table objects with Base.metadata
import engine.core.models  # noqa: F401  (side-effect import)

# --- Set DB URL from application settings (asyncpg) ---
settings = get_settings()
async_db_url = settings.db.async_url  # postgresql+asyncpg://...
config.set_main_option("sqlalchemy.url", async_db_url)

# The metadata object Alembic uses for autogeneration
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    In offline mode Alembic generates SQL scripts without a live DB connection.
    Useful for generating migration scripts in CI or reviewing SQL before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_server_default=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: AsyncConnection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_server_default=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using asyncpg via async engine.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# --- Entry point ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
