"""Application factory and ASGI entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router, health_router
from .api.items import InMemoryItemRepository
from .config import Settings, get_settings
from .errors import register_error_handlers

__all__ = ["app", "create_app"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start-up / shut-down hooks."""
    settings: Settings = app.state.settings
    app.state.logger.info("started %s (debug=%s)", settings.app_name, settings.debug)
    yield
    app.state.logger.info("stopped %s", settings.app_name)


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
    application.state.repository = InMemoryItemRepository()
    application.state.logger = logging.getLogger(resolved.app_name)

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
