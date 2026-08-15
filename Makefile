.PHONY: up down dev-web dev-api migrate seed test test-web test-api lint lint-web lint-api

up:
	docker compose up --build

down:
	docker compose down

dev-web:
	cd apps/web && pnpm dev

dev-api:
	cd apps/api && uv run uvicorn app.main:app --reload

migrate:
	cd apps/api && uv run alembic upgrade head

seed:
	cd apps/api && uv run python -m app.db.seed

test: test-web test-api

test-web:
	cd apps/web && pnpm test

test-api:
	cd apps/api && uv run pytest

lint: lint-web lint-api

lint-web:
	cd apps/web && pnpm lint

lint-api:
	cd apps/api && uv run ruff check .
