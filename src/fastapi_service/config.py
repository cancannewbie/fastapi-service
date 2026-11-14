"""Application configuration.

Values come from environment variables prefixed with ``FASTAPI_`` (or a
``.env`` file next to the process working directory).
"""

from __future__ import annotations

from functools import lru_cache
from secrets import token_urlsafe

from pydantic import Field, SecretStr
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

    # Set FASTAPI_JWT_SECRET to a stable, high-entropy value across workers/restarts.
    jwt_secret: SecretStr = Field(default_factory=lambda: SecretStr(token_urlsafe(32)))
    jwt_expire_minutes: int = Field(default=30, gt=0)

    # SQLAlchemy URL. Use the "postgresql+psycopg://" driver (async capable);
    # "postgresql+asyncpg://" also works if you prefer asyncpg.
    # The port matches compose.yaml's published host port (5433).
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/fastapi_service"
    db_echo: bool = False
    db_pool_size: int = Field(default=5, ge=0)
    db_max_overflow: int = Field(default=10, ge=-1)
    db_check_on_startup: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings object."""
    return Settings()
