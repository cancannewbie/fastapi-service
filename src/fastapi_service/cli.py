"""Console entry point: ``fastapi-service``."""

from __future__ import annotations

import uvicorn

from .config import get_settings


def main() -> None:
    """Run the API server with uvicorn."""
    settings = get_settings()
    uvicorn.run(
        "fastapi_service.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
