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
curl localhost:8000/api/rounds
```

## Local development (without Docker)

```bash
# frontend
cd apps/web && pnpm install && pnpm dev

# backend (requires a running Postgres — e.g. `docker compose up -d db`)
cd apps/api && uv sync && uv run uvicorn app.main:app --reload
```

## Tests & linting

```bash
make test   # pytest + vitest
make lint   # ruff + eslint
```

## Docs

- [`docs/PRD.md`](./docs/PRD.md) — product requirements
- [`docs/DEVELOPMENT_PLAN.md`](./docs/DEVELOPMENT_PLAN.md) — phased build plan with acceptance criteria
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — stack, repo layout, data flow, decisions log
- [`docs/DATA_PRIVACY.md`](./docs/DATA_PRIVACY.md) — GDPR/CCPA retention & deletion working draft
