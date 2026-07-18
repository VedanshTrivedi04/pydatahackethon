"""
Alembic Migration Environment.

This file is loaded by Alembic on every `alembic` CLI command.

Key responsibilities:
1. Load application settings (DB URL from .env)
2. Import all SQLAlchemy models so their metadata is available
3. Configure the migration runner for both online and offline modes
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

# --- Load alembic logging config ---
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Import app settings and all models ---
# Models must be imported here so their tables appear in Base.metadata
# and Alembic can detect schema changes via autogenerate.
import sys
import os

# Ensure project root is on sys.path (alembic.ini prepend_sys_path handles this,
# but explicit is better than implicit for CI environments)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.config.settings import get_settings
from engine.config.database import Base

# Import all models — this registers their Table objects with Base.metadata
import engine.core.models  # noqa: F401  (side-effect import)

# --- Set DB URL from application settings ---
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.db.sync_url)

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
        # Compare server defaults so Alembic detects server_default changes
        compare_server_default=True,
        # Include schema-level comparisons
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (standard execution against a live DB).

    Creates a synchronous connection (required by Alembic — async not supported).
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No pooling for migration connections
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_default=True,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# --- Entry point ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
