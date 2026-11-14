"""Shared pytest fixtures.

The suite always runs against a real PostgreSQL:

* ``TEST_DATABASE_URL`` if set (CI points it at a service container);
* otherwise an embedded PostgreSQL started by ``pgserver`` — no Docker
  required.

Migrations are applied to the test database, so the Alembic scripts are
exercised on every run.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from fastapi_service.app import create_app
from fastapi_service.config import Settings, get_settings

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """Connection string for the PostgreSQL instance used by the tests."""
    override = os.environ.get("TEST_DATABASE_URL")
    if override:
        yield override
        return

    try:
        import pgserver
    except ImportError as exc:  # pragma: no cover - depends on the interpreter
        raise RuntimeError(
            "No PostgreSQL available for the tests. Set TEST_DATABASE_URL to a "
            "reachable database, or run on Python 3.12 where the bundled "
            "'pgserver' (embedded PostgreSQL) is installed."
        ) from exc

    pgdata = Path(tempfile.gettempdir()) / "fastapi-service-test-pg"
    server = pgserver.get_server(str(pgdata))
    yield server.get_uri().replace("postgresql://", "postgresql+psycopg://", 1)


@pytest.fixture(scope="session")
def migrated_database_url(database_url: str) -> str:
    """Apply all migrations to the test database."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    return database_url


@pytest.fixture
def settings(migrated_database_url: str) -> Settings:
    """Settings that do not depend on the ambient environment."""
    get_settings.cache_clear()
    return Settings(
        app_name="test-service",
        api_prefix="/api/v1",
        database_url=migrated_database_url,
    )


@pytest_asyncio.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    """An HTTP client bound to a freshly built app."""
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield test_client
        async with app.state.engine.begin() as connection:
            # RESTART IDENTITY also resets the sequence, so ids stay predictable.
            await connection.execute(text("TRUNCATE tasks, users, items RESTART IDENTITY"))
