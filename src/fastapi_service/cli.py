"""Console entry point: ``fastapi-service``.

::

    fastapi-service              # start the API server
    fastapi-service serve        # same thing, explicit
    fastapi-service migrate      # apply database migrations
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn

from .config import get_settings


def _find_alembic_config() -> Path:
    """Locate ``alembic.ini``.

    Looked up in this order: ``$FASTAPI_ALEMBIC_INI``, the current working
    directory, then the installed package's project root.
    """
    override = os.environ.get("FASTAPI_ALEMBIC_INI")
    if override:
        return Path(override)

    candidates = [
        Path.cwd() / "alembic.ini",
        Path(__file__).resolve().parent.parent.parent / "alembic.ini",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "alembic.ini not found. Set FASTAPI_ALEMBIC_INI or run from the project root."
    )


def run_migrations(revision: str = "head") -> None:
    """Bring the database up to ``revision``."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(_find_alembic_config()))
    command.upgrade(config, revision)


def serve(
    host: str | None = None,
    port: int | None = None,
    reload: bool | None = None,
) -> None:
    """Run the API server with uvicorn."""
    settings = get_settings()
    uvicorn.run(
        "fastapi_service.app:app",
        host=host or settings.host,
        port=port or settings.port,
        reload=settings.reload if reload is None else reload,
    )


def main() -> None:
    """Entry point for the ``fastapi-service`` command."""
    parser = argparse.ArgumentParser(prog="fastapi-service", description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="run the API server")
    serve_parser.add_argument("--host", default=None, help="bind address")
    serve_parser.add_argument("--port", type=int, default=None, help="bind port")
    serve_parser.add_argument(
        "--reload", action="store_true", default=None, help="reload on source changes"
    )

    migrate_parser = subparsers.add_parser("migrate", help="apply database migrations")
    migrate_parser.add_argument(
        "--revision", default="head", help="target revision (default: head)"
    )

    args = parser.parse_args()

    if args.command == "migrate":
        run_migrations(args.revision)
    elif args.command == "serve":
        serve(args.host, args.port, args.reload)
    else:
        serve()


if __name__ == "__main__":  # pragma: no cover
    main()
