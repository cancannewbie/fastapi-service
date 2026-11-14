"""Application factory and ASGI entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .api import api_router, health_router
from .config import Settings, get_settings
from .db.session import create_engine, create_session_factory
from .errors import register_error_handlers

__all__ = ["app", "create_app"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start-up / shut-down hooks.

    The database connection is verified on start-up so a misconfigured or
    unreachable database fails the process immediately instead of surfacing
    as 500s on the first request.
    """
    settings: Settings = app.state.settings
    logger: logging.Logger = app.state.logger
    engine: AsyncEngine = app.state.engine

    if settings.db_check_on_startup:
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception as exc:
            raise RuntimeError(
                f"Cannot reach the database at {settings.database_url!r}. "
                "Is Postgres running? Did you run the migrations?"
            ) from exc

    logger.info("started %s (debug=%s)", settings.app_name, settings.debug)
    try:
        yield
    finally:
        await engine.dispose()
        logger.info("stopped %s", settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a configured :class:`FastAPI` application.

    Passing ``settings`` makes the app fully independent from the environment,
    which is what the test-suite does.
    """
    resolved = settings or get_settings()

    application = FastAPI(
        title=resolved.app_name,
        version="0.1.0",
        debug=resolved.debug,
        lifespan=lifespan,
    )
    application.state.settings = resolved
    application.state.logger = logging.getLogger(resolved.app_name)
    application.state.engine = create_engine(resolved.database_url, echo=resolved.db_echo)
    application.state.session_factory = create_session_factory(application.state.engine)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router, prefix=resolved.api_prefix)
    return application


app = create_app()
