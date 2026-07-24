"""Alembic environment configuration for async SQLAlchemy.

This env.py is adapted for asyncpg (async PostgreSQL driver).
It imports models from the application so autogenerate can detect schema changes.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from forgeai.config import get_settings
from forgeai.database import Base  # noqa: F401 — imports all models via metadata

# ─── Import all models so Alembic autogenerate can detect them ────────────────
# Phase 2 models — registers repositories + repository_files tables
from forgeai.models import Repository, RepositoryFile  # noqa: F401

# ─── Alembic Config ───────────────────────────────────────────────────────────
config = context.config
settings = get_settings()

# Inject the database URL from app settings (overrides alembic.ini sqlalchemy.url)
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without a live database connection.
    Useful for reviewing migrations before applying them.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    """Execute migrations against a live database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations."""
    connectable = create_async_engine(settings.database_url, echo=False)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live database."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
