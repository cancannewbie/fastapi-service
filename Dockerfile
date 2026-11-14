# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.13.8 AS uv

FROM python:3.12-slim AS builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
# Install the project itself so `fastapi_service` and the `fastapi-service`
# console script are on the image's PATH.
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim AS runtime
RUN useradd --create-home --uid 1000 appuser
WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/alembic /app/alembic
COPY --from=builder --chown=appuser:appuser /app/alembic.ini /app/alembic.ini
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FASTAPI_ALEMBIC_INI=/app/alembic.ini \
    FASTAPI_HOST=0.0.0.0 \
    FASTAPI_PORT=8000
USER appuser
EXPOSE 8000
# ENTRYPOINT (not CMD) so `docker run <image> migrate` runs
# `fastapi-service migrate` instead of looking for a "migrate" executable.
# FASTAPI_HOST=0.0.0.0 above is what makes the port reachable from outside
# the container (the app's default 127.0.0.1 would only listen on loopback).
ENTRYPOINT ["fastapi-service"]
CMD ["serve"]
