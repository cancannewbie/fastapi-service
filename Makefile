.PHONY: install dev test lint format typecheck check run migrate migrate-new \
        db-up db-down up down logs docker-build

install:
	uv sync

dev:
	uv run uvicorn fastapi_service.app:app --reload

run:
	uv run fastapi-service

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy

check: lint typecheck test

# Database --------------------------------------------------------------
db-up:
	docker compose up -d postgres

db-down:
	docker compose down

migrate:
	uv run fastapi-service migrate

migrate-new:
	uv run alembic revision --autogenerate -m "$(m)"

# Docker ---------------------------------------------------------------
# Full stack: postgres + a one-shot migration job + the app.
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

docker-build:
	docker build -t fastapi-service .
