# Debrief Golf — Development Plan

This expands the PRD's [Phased Development Roadmap](./PRD.md#10-phased-development-roadmap) into concrete, checkable tasks with acceptance criteria per phase. Each phase should ship with passing tests before moving to the next.

## Phase 0 — Bootstrap (done)

Repo scaffolding: monorepo (`apps/web` Next.js 15 + `apps/api` FastAPI), Docker Compose with Postgres 16/PostGIS, CI, and project docs (this document, the PRD, architecture notes, data privacy stub).

**Delivered:**
- [x] `apps/web` — Next.js 15 (App Router, TS, Tailwind v4, shadcn/ui), Vitest + RTL, placeholder dashboard reflecting the PRD §8 nav.
- [x] `apps/api` — FastAPI on Python 3.12 (uv-managed), SQLModel session plumbing, `/api/health` endpoint that round-trips the DB, pytest smoke test.
- [x] `docker-compose.yml` — `db` (postgis/postgis:16), `api`, `web` services wired together for local dev.
- [x] GitHub Actions CI — backend (ruff + pytest against a real Postgres service container) and frontend (eslint + vitest + build) jobs.
- [x] `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/DATA_PRIVACY.md`, root `README.md`.

**Not yet built (as of Phase 0):** data models, parsers, analytics. Data models, migrations, parsers, SG benchmark data, and a demo seed script were added as part of Phase 1 (now complete, see below) — analytics (Phase 2) is still open.

## Phase 1 — Environment, Database Schemas & Data Parsers (done)

Goal: the DB schema and raw-data ingestion pipeline exist and are testable in isolation, before any analytics or UI depend on them.

- [x] SQLModel tables in `apps/api/app/models/`: `User`, `Course`, `Hole` (with PostGIS `Polygon`/`Point` geometry for green boundaries and hole layout), `Round`, `Shot` (with `Point` geometry per shot location, lie type, club, distance).
- [x] Alembic migration setup (`apps/api/alembic/`) with an initial migration creating the above tables + enabling `postgis`. Note: the `postgis/postgis` Docker image also installs `postgis_tiger_geocoder`/`postgis_topology` into non-`public` schemas — `alembic/env.py` whitelists only our own tables so autogenerate doesn't try to manage them.
- [x] Demo data seed script (`apps/api/app/db/seed.py`, `make seed`) — one realistic 18-hole round (score 78/+6, matching the PRD §8 example) covering a short-sided bunker approach, an OB penalty, a hazard penalty inside 150y, a 3-putt, and a par-5 bogey, so the API/UI have something real to exercise. `GET /api/rounds` and `/api/rounds/{id}/shots` expose it.
- [x] Broadie Strokes Gained benchmark lookup tables — `strokes_gained_benchmark` table (`app/models/benchmark.py`) seeded per handicap bucket (Scratch, 5, 10, 15, 20, 25) keyed by lie + distance bracket, via `app/services/benchmarks.py`'s `expected_strokes()`/`generate_benchmark_rows()` and `make seed`. (Distinct from the demo seed script above — this is reference data the SG engine benchmarks against, not sample round data.) Note: `SCRATCH_CURVES` is a hand-authored approximation of Broadie's published baseline shape, not a transcription of licensed data — swap in real figures before this feeds anything user-facing.
- [x] `.FIT` file parser (`app/services/parsers/fit_parser.py`, using `fitparse`) that extracts a GPS point track and activity metadata (`parse_fit_activity()`). Scoped to raw extraction only, per Phase 3's audit wizard being where shots get segmented/verified — no per-shot auto-segmentation from the continuous GPS track yet.
- [x] R10/R50 CSV/JSON parser (`app/services/parsers/launch_monitor_parser.py`) extracting per-shot delivery arrays (club path, face angle, spin axis, smash factor, carry/roll) via `parse_launch_monitor_csv()`/`parse_launch_monitor_json()`, with header-alias matching (exact Garmin export column names aren't publicly documented) and per-row error collection instead of hard failures.
- [x] Corrupted/incomplete `.FIT` handling: rounds missing essential coordinates (or files `fitparse` can't decode at all) are flagged `casual_practice` rather than rejected (PRD §4.3), verified by tests with a deliberately invalid fixture file and a too-few-GPS-points case.

**Acceptance criteria:** migrations apply cleanly to a fresh DB (verified against a real Postgres 16 + PostGIS instance, upgrade and downgrade); parser unit tests cover a valid `.FIT` fixture (mocked `fitparse.FitFile` — see `tests/parsers/test_fit_parser.py` docstring for why), a corrupted `.FIT` fixture, and valid R10/R50 CSV and JSON fixtures; SG benchmark lookups return the expected value for a handful of known (lie, distance, handicap) inputs (`tests/test_benchmarks.py`).

## Phase 2 — Analytics Core (Strokes Gained, Tiger 5 & Smart Bag) (done)

Goal: turn ingested shot data into the diagnostic numbers the UI will display.

- [x] Strokes Gained engine (`app/services/strokes_gained.py`) implementing `SG = Benchmark(start) - Benchmark(end) - 1` (via `app/services/benchmarks.py`, extended with a `Lie.penalty` = fairway-equivalent-plus-one-stroke rule so SG telescopes correctly across penalty sequences), split into OTT / APP / ARG / PUTT categories. Tee shots on par 3s fold into APP/ARG rather than OTT, matching the standard convention; a putter used off the green still counts as PUTT.
- [x] Tiger 5 evaluator (`app/services/tiger_five.py`): double-bogeys+, 3-putts, Par 5 bogeys, blown recoveries inside 50y, penalties inside 150y — plus Clean Card Index (CCI, % of holes at par or better) calculation.
- [x] Smart Bag club gapping: per-club carry-distance dispersion stats with IQR-based outlier rejection (`app/services/smart_bag.py`), using NumPy, plus consecutive-club carry-gap reporting. **Lateral dispersion is not yet populated** — it needs a per-shot target-line-relative offset that neither the on-course GPS data nor the R10/R50 parser currently captures; the stats engine accepts it (`lateral_by_club`) whenever that data exists, likely alongside Phase 4's dispersion-map work.
- [x] Putting mechanics split (`app/services/putting.py`): lag speed efficiency (>20ft putts, finish-within-3ft rate) and start-line conversion (<6ft putts, make rate).
- [x] Short-sided vs. safe-leave classification for approach shots (`app/services/approach.py`). **This is a distance/lie-based proxy, not true short-siding** — real short-siding needs the shot's miss angle relative to that day's actual pin position, which needs a per-round pin location this schema doesn't store (`Hole.green_center` is static, not per-round). Real geometric short-siding is Phase 4 work once pin position + green-boundary containment queries exist; this flags a candidate for the audit wizard in the meantime.
- [x] API endpoints exposing round-level and bag-level analytics to the frontend: `GET /api/rounds/{id}/analytics` (SG by category, Tiger 5 + CCI, putting mechanics, per-shot breakdown — also persists computed `Shot.strokes_gained`) and `GET /api/bag/{user_id}` (Smart Bag club gapping) in `app/api/routes/rounds.py` / `app/api/routes/bag.py`.

**Acceptance criteria:** unit tests validate SG math against hand-computed examples per distance bracket, plus a telescoping-sum invariant test (`tests/test_strokes_gained.py`) that holds regardless of the specific benchmark curve values; Tiger 5/CCI tests cover each violation type including a regression test for a double-counting bug found during manual verification (a penalty event's "shot into the hazard" row and its penalty-marker row both end in `Lie.penalty` — only the marker row counts); outlier rejection tests confirm a synthetic outlier shot is excluded from Smart Bag stats. All endpoints manually verified end-to-end against a real Postgres 16 + PostGIS instance and the seeded demo round.

## Phase 3 — Frontend Foundations & the "2-Minute Fast Audit" Wizard

Goal: users can get data in and see it rendered, even before maps/practice hub exist.

- [ ] Replace the bootstrap placeholder dashboard with the real Round Snapshot + Tiger 5 Disaster Meter layout (PRD §8), wired to Phase 2 API endpoints.
- [ ] `.FIT` file upload UI (drag-and-drop) calling the Phase 1 parser endpoint; shown automatically on Garmin webhook failure (PRD §4.3).
- [ ] Audit wizard flow: Fringe vs. True Putting isolation prompt, "Insert Shot Between" timeline tool with coordinate snapping, penalty drop classifier (Lateral Hazard vs. OB/Lost Ball), strike-quality tagging modal for shots below -0.4 SG.
- [ ] Garmin Connect OAuth 2.0 flow (frontend redirect + backend token exchange/storage).
- [ ] IndexedDB layer for offline-friendly draft state during the audit wizard.

**Acceptance criteria:** Vitest/RTL coverage for the wizard's branching logic (penalty classification, short-putt vs. long-putt routing); an end-to-end manual pass of uploading a sample `.FIT` file through to a rendered Round Snapshot.

## Phase 4 — Hole Replay, Dispersion Maps & Strategy Engine

Goal: spatial visualization layer on top of Phase 1–3 data.

- [ ] Mapbox GL integration rendering hole satellite imagery with the plotted shot vector per hole.
- [ ] 2D dispersion ellipse overlay (Deck.gl or SVG) computed from a club's Smart Bag carry/lateral stats, positioned relative to a chosen aim point.
- [ ] Center-green aim comparison line and tucked-pin dispersion-vs-pin overlay.
- [ ] Short-sided / "sucker pin" strategy alert banners triggered from Phase 2 classifications.

**Acceptance criteria:** dispersion ellipse math covered by unit tests (given known mean/stdev, ellipse bounds match expected values); manual visual check of hole replay against a real synced round.

## Phase 5 — Practice Hub, R10/R50 Delivery & Coach Export

Goal: close the loop from diagnosis to prescribed practice, and serve the PGA Coach persona.

- [ ] Practice Hub UI: prescriptive combine cards (9-Ball Wedge Matrix, 30-Yard Corridor Test, Low-Point Compression, Safety Circle Test per PRD §7.1) driven by detected weaknesses, each linking to a curated video.
- [ ] R10/R50 delivery profile view (per-club Face-to-Path, Spin Axis, Smash Factor trends over practice sessions) and Sim vs. Real-World gapping delta.
- [ ] Virtual/Sim Round Hub, segregated from real-world handicap calculations.
- [ ] 1-Page "Coach-Ready" Lesson Brief: React-PDF export summarizing net stroke leaks, strike patterns, Tiger 5 metrics, and a recommended coaching agenda.

**Acceptance criteria:** combine-selection logic unit tested (given a weakness profile, the correct drill is recommended); PDF export produces a well-formed single-page document from a sample round.

## Cross-cutting (ongoing, not a single phase)

- **Data privacy:** user-triggered deletion of spatial/scorecard data, retention policy enforcement — see [`docs/DATA_PRIVACY.md`](./DATA_PRIVACY.md). Should land no later than Phase 3 (once real user data exists).
- **CI:** keep `.github/workflows/ci.yml` green; add new test suites to the existing `backend`/`frontend` jobs rather than creating parallel pipelines.
