.PHONY: install dev test lint format typecheck check run docker-build

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

docker-build:
	docker build -t fastapi-service .
