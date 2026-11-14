"""Application configuration.

Values come from environment variables prefixed with ``FASTAPI_`` (or a
``.env`` file next to the process working directory).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FASTAPI_",
        extra="ignore",
    )

    app_name: str = "fastapi-service"
    debug: bool = False
    api_prefix: str = "/api/v1"

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False

    cors_origins: list[str] = ["http://localhost:3000"]

    # SQLAlchemy URL. Use the "postgresql+psycopg://" driver (async capable);
    # "postgresql+asyncpg://" also works if you prefer asyncpg.
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_service"
    db_echo: bool = False
    db_check_on_startup: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings object."""
    return Settings()
