.PHONY: up down db-up db-down dev-web dev-api migrate seed test test-web test-api lint lint-web lint-api

up:
	docker compose up --build

down:
	docker compose down

# Just the database, without api/web — what the backend tests need. `--wait`
# blocks until the container's healthcheck passes, so a following `migrate`
# or `pytest` doesn't race the server's startup.
db-up:
	docker compose up -d --wait db

db-down:
	docker compose stop db

dev-web:
	cd apps/web && pnpm dev

dev-api:
	cd apps/api && uv run uvicorn app.main:app --reload

migrate: db-up
	cd apps/api && uv run alembic upgrade head

seed: migrate
	cd apps/api && uv run python -m app.db.seed

test: test-web test-api

test-web:
	cd apps/web && pnpm test

# Depends on db-up, not migrate: the backend suite provisions and migrates
# its own `<database>_test` database (apps/api/tests/conftest.py) and never
# touches the development one. It only needs a server to be running.
test-api: db-up
	cd apps/api && uv run pytest

lint: lint-web lint-api

lint-web:
	cd apps/web && pnpm lint

lint-api:
	cd apps/api && uv run ruff check .
