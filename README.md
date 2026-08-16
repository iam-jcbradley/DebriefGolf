# Debrief Golf

Arccos-grade post-round diagnostics for the Garmin Golf ecosystem — Strokes Gained,
dispersion modeling, outlier-filtered Smart Bag stats, and prescriptive practice, built
from Garmin watch/CT10/rangefinder rounds and R10/R50 launch monitor sessions.

See [`docs/PRD.md`](./docs/PRD.md) for the full product spec and
[`docs/DEVELOPMENT_PLAN.md`](./docs/DEVELOPMENT_PLAN.md) for the phased build-out.

## Stack

- **Frontend** — Next.js 15 (App Router, TS), Tailwind CSS, shadcn/ui, Recharts, Mapbox GL / deck.gl — `apps/web`
- **Backend** — FastAPI (Python 3.12+), SQLModel, NumPy/Pandas, fitparse — `apps/api`
- **Database** — PostgreSQL 16 + PostGIS

Details and rationale: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).

## Quickstart

```bash
cp .env.example .env
make up          # docker compose up --build: db + api + web
```

- Web: http://localhost:3000
- API: http://localhost:8000/api/health

Then apply migrations and load a demo round to have something to look at:

```bash
make migrate     # alembic upgrade head
make seed        # one 18-hole demo round, incl. a few PRD-style diagnostic scenarios
```

`make seed` prints the demo account's login. Sign in at
http://localhost:3000/login with it (or create your own account) — every
endpoint that touches player data requires a session, so `curl
localhost:8000/api/rounds` on its own now answers `401`.

## Local development (without Docker)

```bash
# frontend
cd apps/web && pnpm install && pnpm dev

# backend (requires a running Postgres — e.g. `make db-up`)
cd apps/api && uv sync && uv run uvicorn app.main:app --reload
```

## Getting round data in

Two ways: upload a `.FIT` file (drag-and-drop in the web app, or via
`POST /api/rounds/upload`), or enter a round manually with GPS-mapped
shots (`/rounds/new` — see Phase 5 in the development plan). Garmin's
official Health/Developer API requires a paid account, so there's no
built-in auto-sync; [`tools/garmin_import/`](./tools/garmin_import/) is an
optional, personal-use CLI that pulls your own `.FIT` files out of Garmin
Connect using your own login and feeds them into the upload endpoint above
— it runs entirely on your machine and never sends your Garmin credentials
to this app. See that directory's README before using it.

## Tests & linting

```bash
make test   # pytest + vitest
make lint   # ruff + eslint
```

`make test` starts the database itself (`make db-up`) if it isn't already
running. The backend suite creates and migrates its own `debrief_golf_test`
database and wraps every test in a transaction it rolls back, so it never
reads or writes your development data — `make seed`'s demo round can't break
a test, and a test run can't leave rows behind. Point it somewhere else with
`TEST_DATABASE_URL` if you'd rather not use Docker for it.

The pure-logic suites need no database at all:

```bash
cd apps/api && uv run pytest tests/parsers tests/test_strokes_gained.py
```

`tools/garmin_import` is a standalone pip project with its own tests, run in
CI and locally with:

```bash
cd tools/garmin_import && pip install -r requirements-dev.txt && pytest
```

## Docs

- [`docs/PRD.md`](./docs/PRD.md) — product requirements
- [`docs/DEVELOPMENT_PLAN.md`](./docs/DEVELOPMENT_PLAN.md) — phased build plan with acceptance criteria
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — stack, repo layout, data flow, decisions log
- [`docs/DATA_PRIVACY.md`](./docs/DATA_PRIVACY.md) — GDPR/CCPA retention & deletion working draft
