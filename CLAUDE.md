# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make up          # docker compose: db + api + web
make db-up       # just Postgres/PostGIS, waits for the healthcheck
make migrate     # alembic upgrade head (dev database)
make seed        # one 18-hole demo round with PRD-style diagnostic scenarios
make test        # vitest + pytest
make lint        # eslint + ruff
```

`make test` starts the database itself. The backend suite creates and migrates its
own `debrief_golf_test` database and never touches the dev one, so `make seed`
data and test runs can't interfere with each other.

Single tests:

```bash
cd apps/api && uv run pytest tests/test_rounds.py::TestCreateRound::test_404_for_unknown_user
cd apps/api && uv run pytest tests/parsers tests/test_strokes_gained.py   # no database needed
cd apps/web && pnpm test src/components/stat-tile.test.tsx
cd apps/web && pnpm vitest run -t "renders all five violation counts"
```

`tools/garmin_import` is a standalone pip project (not in the uv workspace) with
its own tests, run by CI's `tools` job:
`cd tools/garmin_import && pip install -r requirements-dev.txt && pytest`.

## Architecture

**FastAPI owns all backend logic; Next.js is frontend-only.** There are no Next.js
API routes and shouldn't be — the browser calls FastAPI directly via
`apps/web/src/lib/api.ts`, which is the single place every endpoint is typed and
called. Garmin's OAuth callback hits the FastAPI backend, not the web app.

**Layering in `apps/api`:**
- `app/services/` — pure business logic (Strokes Gained, Tiger 5, Smart Bag,
  parsers, geometry, dispersion, OSM lookup). These take plain values or model
  instances and touch no database session, which is why their tests need no
  Postgres. See `app/services/README.md` for what each module does and which
  phase built it.
- `app/api/routes/` — HTTP, validation, and persistence. Straight CRUD lives here
  deliberately rather than in a service module; only real analysis goes in
  `services/`.
- `app/models/` — SQLModel tables, all re-exported through `app/models/__init__.py`.
  Import from `app.models`, not the submodules.

**Data flow:** a round enters via `.FIT` upload or manual entry → shots persist
with PostGIS geometry → `services/` computes analytics → FastAPI serves JSON →
Next.js renders the PRD §8 views (Mapbox/deck.gl for spatial, Recharts for trends).

**Phase-driven.** `docs/DEVELOPMENT_PLAN.md` is the working source of truth: every
phase lists what shipped, what didn't, and its acceptance criteria. Code comments
reference PRD sections (`PRD §5.2`) rather than restating requirements. When you
finish a phase, update its entry with real numbers and a candid "gaps carried
forward" list — that section is load-bearing, not decoration.

## Things that will bite you

**Never return `select(Shot)` (or any model with a geometry column) as JSON.**
geoalchemy2 hands back a `WKBElement` for `location`, which isn't
JSON-serializable, so any shot with GPS data 500s. Select raw columns and unwrap
with `func.ST_Y(...)` / `func.ST_X(...)` instead — `GET /rounds/{id}/shots` in
`app/api/routes/rounds.py` is the reference implementation, and
`app/api/routes/privacy.py` repeats it. This has been rediscovered more than once.

**`apps/api/app/services/geometry.py` and `apps/web/src/lib/hole-replay/projection.ts`
are mirrors of each other** — the same flat-earth projection and the same
`YARDS_PER_DEGREE_LAT` constant, so the hole-replay SVG agrees with the backend's
lateral-dispersion numbers. Change one, change the other.

**`VirtualRound` is deliberately not a `Round`.** PRD §6.2 requires simulator
rounds to be segregated from real-world handicap calculations, and a separate
table means every existing query over `Round` is correct by construction with no
`is_simulator` filter to remember. Don't unify them.

**Alembic:** autogenerate is whitelisted to app tables via `include_object` in
`alembic/env.py` (the PostGIS image installs `postgis_topology`/`tiger_geocoder`
tables that otherwise show up as "tables to drop"). GeoAlchemy2 creates GIST
spatial indexes itself at table-creation time, so delete any `op.create_index` for
a geometry column from generated migrations or you'll get a duplicate-index error.
`env.py` also honours a `sqlalchemy_url` config attribute over `DATABASE_URL`,
which is how the test harness migrates its own database.

**Backend tests use the `client` and `db_session` fixtures from
`tests/conftest.py`.** Don't build `TestClient(app)` at module scope and don't
import `app.db.session.engine` in a test — that's the pattern Phase 9 removed.
Each test runs in a transaction that's rolled back, so seed with fixed readable
values; no `uuid4()` collision-dodging is needed. Test-body seeding and the
request under test must share `db_session`, or the handler won't see the seeded
rows. `tests/test_isolation.py` guards these properties.

**Frontend tests import `renderWithProviders as render` from `@/lib/test-utils`.**
`NavBar` renders on every page and calls `useCurrentUser()`, which throws without
a `CurrentUserProvider` ancestor.

**There is no authentication.** Every endpoint takes `user_id` as a query or path
parameter and trusts it — including `GET /api/users/{id}/export` and
`DELETE /api/users/{id}`. This is a known hole, scheduled as Phase 10, not a
pattern to extend. Before adding an endpoint that reads user data, check whether
Phase 10 has landed.

**Integrations that can't be verified here.** Garmin OAuth, the Overpass API, and
Mapbox are all unreachable from the dev sandbox (Garmin's API also requires a paid
developer account, which is why manual entry became the primary ingestion path).
The convention is to write standards-conformant code, unit-test it against mocked
responses, and state the verification limit plainly in the module docstring —
see `app/services/garmin_oauth.py` and `app/services/osm_courses.py`. Don't
quietly present unverified integrations as working.

## Frontend design system

`docs/STYLE_GUIDE.md` governs the UI: an editorial private-club aesthetic
("member's handbook", not fitness tracker). Colors are CSS custom properties in
`src/app/globals.css`, exposed to Tailwind via `@theme inline`. One accent color
(fairway green `--primary`); never pure black or white — use `--foreground` and
`--background`, which carry warm undertones. Fraunces for headlines
(`font-serif`), Geist Sans for everything else. No badges, streaks, or heavy
shadows; structure comes from hairline `--border` rules.
