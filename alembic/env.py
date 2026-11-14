"""Alembic environment.

The database URL comes from the application settings (``FASTAPI_DATABASE_URL``)
so migrations and the service always point at the same database.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, create_engine, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from fastapi_service.config import get_settings
from fastapi_service.db import models  # noqa: F401  (registers the ORM mappings)
from fastapi_service.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """URL to migrate, overridable with ``-x url=...`` or ``sqlalchemy.url``."""
    override = context.get_x_argument(as_dictionary=True).get("url")
    if override:
        return override
    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return configured
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to a database."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_migrations_online() -> None:
    """Connect with an async engine and run the migrations."""
    url = _database_url()
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = url

    if "+psycopg" in url or "+asyncpg" in url:
        connectable = async_engine_from_config(
            section, prefix="sqlalchemy.", poolclass=pool.NullPool
        )
        async with connectable.connect() as connection:
            await connection.run_sync(_do_run_migrations)
        await connectable.dispose()
    else:
        connectable = create_engine(url, poolclass=pool.NullPool)
        with connectable.connect() as connection:
            _do_run_migrations(connection)
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(_run_migrations_online())
