"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from fastapi_service.app import create_app
from fastapi_service.config import Settings, get_settings


@pytest.fixture
def settings() -> Settings:
    """Settings that do not depend on the ambient environment."""
    get_settings.cache_clear()
    return Settings(app_name="test-service", api_prefix="/api/v1")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """A test client bound to a freshly built app."""
    with TestClient(create_app(settings)) as test_client:
        yield test_client
