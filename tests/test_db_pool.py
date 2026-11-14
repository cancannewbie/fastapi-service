"""Tests for database pool configuration."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from fastapi_service.app import create_app
from fastapi_service.config import Settings
from fastapi_service.db.session import create_engine


def test_pool_settings_defaults_and_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FASTAPI_DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("FASTAPI_DB_MAX_OVERFLOW", raising=False)
    defaults = Settings(_env_file=None)
    assert (defaults.db_pool_size, defaults.db_max_overflow) == (5, 10)

    monkeypatch.setenv("FASTAPI_DB_POOL_SIZE", "2")
    monkeypatch.setenv("FASTAPI_DB_MAX_OVERFLOW", "3")
    configured = Settings(_env_file=None)
    assert (configured.db_pool_size, configured.db_max_overflow) == (2, 3)


@pytest.mark.parametrize("name,value", [("db_pool_size", -1), ("db_max_overflow", -2)])
def test_invalid_pool_settings(name: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{name: value})


def test_engine_enables_pre_ping() -> None:
    with patch("fastapi_service.db.session.create_async_engine") as factory:
        create_engine("postgresql+psycopg://localhost/test", pool_size=2, max_overflow=3)
    factory.assert_called_once_with(
        "postgresql+psycopg://localhost/test",
        echo=False,
        pool_size=2,
        max_overflow=3,
        pool_pre_ping=True,
    )


async def test_app_uses_configured_pool(migrated_database_url: str) -> None:
    settings = Settings(
        _env_file=None,
        database_url=migrated_database_url,
        db_pool_size=1,
        db_max_overflow=1,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        pool = app.state.engine.pool
        assert pool.size() == 1
        async with app.state.engine.connect(), app.state.engine.connect():
            assert pool.checkedout() == 2
            assert pool.overflow() == 1
