"""fastapi-service: a small FastAPI application package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

__all__ = ["__version__", "app", "create_app"]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .app import app, create_app


def __getattr__(name: str) -> Any:
    """Expose ``create_app`` / ``app`` lazily to avoid import cycles."""
    if name in {"create_app", "app"}:
        from .app import app, create_app

        return {"create_app": create_app, "app": app}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
