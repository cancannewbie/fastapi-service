.PHONY: install dev test lint format typecheck check run migrate migrate-new db-up db-down docker-build

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
docker-build:
	docker build -t fastapi-service .
