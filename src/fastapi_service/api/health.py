"""Health and readiness probes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, Any]:
    """Return ``ok`` as long as the process is serving requests."""
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
async def ready(request: Request) -> dict[str, Any]:
    """Return ``ready`` only when the database is reachable."""
    async with request.app.state.engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ready"}
