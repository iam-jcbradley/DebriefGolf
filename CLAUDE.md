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

## Review process

**Run a five-perspective panel before finalizing a plan, and before calling
significant work done.** Five independent agents — PM, developer, designer,
customer/end-user, QA — reviewing the same target in parallel with no shared
context, each told to critique from their lens only against the real project
docs (the plan itself, `docs/PRD.md`, `docs/STYLE_GUIDE.md` for the design
read, this file for the developer and QA reads), not from a summary of what
to think. The QA read is the long-term-maintainability lens the other four
don't cover: code quality, human legibility, simplicity, and adherence to
this file's own conventions, on the actual diff or code under review rather
than the plan prose — where a duplicated helper, a misleading name, a
missing test for the new branch, or a needless abstraction would slow down
whoever touches this next. Then synthesize: findings multiple reviewers hit
independently are the ones that matter most, and the pass isn't done until
they produce an actual revision — a panel that changes nothing wasn't worth
running. Part III of `docs/DEVELOPMENT_PLAN.md` is the reference example
(from the four-perspective version of this process, before the QA seat
existed): it reordered its four phases, cut two speculative items to the
backlog, and caught a factual error in a cost estimate, all from convergent
findings a single pass had missed.

Run it:
- Before finalizing or substantially revising `docs/DEVELOPMENT_PLAN.md` —
  a new phase, a re-sequencing, a scope change.
- Before marking a phase (or other significant chunk of work) done — a last
  pass before writing up acceptance criteria, not a replacement for it.

Don't run it for routine fixes or small edits — it's the expensive path,
reserved for decisions that are costly to get wrong and cheap to catch here.

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

**Identity comes from the session, never from a request parameter.** An
endpoint that needs to know who is calling takes `CurrentUser` from
`app/api/deps.py`; there is deliberately no way to name a different user in a
request, and no endpoint accepts a `user_id`. Anything addressing a row by id
(a round, a virtual round) must check ownership and return **404, not 403**, for
someone else's row — a 403 confirms the row exists. `rounds.py`'s `_owned_round`
is the pattern.

`tests/test_access_control.py` enumerates the live API surface from the OpenAPI
schema and asserts every endpoint 401s without a session, so a new route added
without `CurrentUser` fails the suite until someone adds it to `PUBLIC_ENDPOINTS`
with a reason. Don't add it there to make the test pass.

**Rotating `SECRET_KEY` invalidates every session and every stored Garmin
token.** It signs session cookies and the OAuth state token, and derives the
Fernet key for the encrypted `garmin_connection` columns. This bites in tests
too: monkeypatching `settings.secret_key` after logging a test client in makes
every subsequent request 401.

**Endpoints that walk all of a user's shots select raw columns, not ORM
objects.** `GET /bag` and both practice endpoints read every shot a player has
recorded; building that many `Shot` instances costs ~5x what the five columns
they actually read cost. `app/services/shot_view.py` defines the `ShotView`
protocol those services accept — a `Shot` satisfies it, and so does a
`select(Shot.club, ...)` row. Single-round endpoints still load full objects;
the difference there is a few dozen rows. `scripts/benchmark.py` is how any of
this gets checked — measure before changing.

**`GET /rounds/{id}/analytics` must stay read-only.** It used to write computed
Strokes Gained back to every shot on every call. Stored SG is written when
shots are recorded (`POST /rounds/{id}/shots/bulk`) and when handicap index
changes (`PATCH /api/auth/me`); `tiger_five` takes the values as an argument
rather than reading them off ORM objects a GET had to mutate first.

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
