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

## Phase 3 — Frontend Foundations & the "2-Minute Fast Audit" Wizard (done, with noted gaps)

Goal: users can get data in and see it rendered, even before maps/practice hub exist.

- [x] Replaced the bootstrap placeholder dashboard with a real Round Snapshot + Tiger 5 Disaster Meter (`src/app/page.tsx`, `src/components/round-snapshot.tsx`, `src/components/tiger-five-meter.tsx`), wired to Phase 2's `/api/rounds` + `/api/rounds/{id}/analytics`. Added `CORSMiddleware` to the API (`app/main.py`) — the browser couldn't call the backend at all without it, caught during manual verification.
- [x] `.FIT` file upload UI (`src/components/fit-upload.tsx`, drag-and-drop + click-to-browse), calling a new `POST /api/rounds/upload` endpoint (`app/api/routes/rounds.py`) that wires up Phase 1's `parse_fit_activity()`. Required making `Round.course_id` nullable (migration `3c7e5b1f9a20`) — a freshly-uploaded round has GPS points but no matched course yet.
- [x] Audit wizard flow (`src/components/audit-wizard/`, logic in `src/lib/audit/`): penalty drop classifier (Lateral Hazard vs. OB/Lost Ball, matching the seed data's own conventions exactly), Fringe vs. True Putting isolation prompt, short-putt/long-putt routing, and a strike-quality tagging modal for shots below -0.4 SG. A `AuditWizard` shell sequences these over a draft shot list. **"Insert Shot Between" timeline tool with coordinate snapping is deferred** — it needs the map integration Phase 4 builds; there's no map component anywhere in the app yet to snap coordinates against.
- [x] Garmin Connect OAuth 2.0 + PKCE plumbing (`app/services/garmin_oauth.py`, `app/api/routes/garmin_auth.py`, `src/app/settings/garmin/`): authorize/callback/status/disconnect all real and tested (mocked token exchange). **Cannot be verified against Garmin's actual servers** — no Garmin Developer Program credentials are available in this environment, and the exact authorize/token endpoint URLs must come from Garmin's Developer Portal (left blank rather than guessed — see `.env.example`). Manually verified the whole flow up to that boundary: clicking "Connect Garmin" surfaces a clear "not configured" error rather than failing silently. **Update, Phase 5:** it turned out Garmin's Developer Program requires a paid account, so this can't be the primary way ordinary users get data in — kept intact (still real, still tested) but de-emphasized in favor of manual entry; see Phase 5.
- [x] IndexedDB layer for offline-friendly audit wizard draft state (`src/lib/audit/draft-store.ts`, `use-audit-draft.ts`) — a round's in-progress review survives a refresh/remount. Tested with `fake-indexeddb`.

**Gaps carried forward, tracked here rather than silently glossed over:**
- The audit wizard operates on a client-only draft shot list (`DraftShot`, keyed by hole *number*, not `hole_id`). There's no `POST /api/rounds/{id}/shots` endpoint yet, and submitting reviewed shots back to the backend needs a course assigned to the round first (course-matching or a manual course-picker — neither exists). The `/rounds/[id]/audit` page therefore includes its own manual "add a shot" form to demonstrate the review flow end-to-end rather than pulling real shots from a round.
- Short-sided classification and lateral dispersion remain the Phase 2 proxies noted there — still waiting on Phase 4's spatial data.

**Acceptance criteria:** Vitest/RTL coverage for the wizard's branching logic (penalty classification — including exact seed-data-scenario regression tests; short-putt vs. long-putt routing) — 115 frontend tests total. An end-to-end manual pass of uploading a sample `.FIT` file was run in a real browser (Playwright against Chromium) through to a rendered Round Snapshot for the *existing* seeded demo round, and separately through the full audit wizard flow (add shots → penalty → fringe isolation → putt routing → strike-quality tag → completion) for a fresh round — this manual pass caught two real bugs (missing CORS config; a decimal-distance input silently failing native HTML5 step validation), both fixed.

## Phase 4 — Hole Replay, Dispersion Maps & Strategy Engine (done, with noted gaps)

Goal: spatial visualization layer on top of Phase 1–3 data.

- [x] `app/services/geometry.py`: flat-earth tee→green aim-line projection (longitudinal/lateral yards for any GPS point). This is what actually closes the lateral-dispersion gap Phase 2 flagged as unpopulated — `Hole.tee_location`/`green_center` and `Shot.location` already existed in the schema, they just weren't being used together. Wired into `GET /api/bag/{user_id}`, which now reports `lateral_mean_yards`/`lateral_stdev_yards` and a `dispersion_ellipse` per club with at least one located shot. `app/db/seed.py` was extended to actually populate `Shot.location` (it never had before — every seeded shot's location was `NULL`), including a deliberate rule that a shot recording no forward progress (a penalty marker or stroke-and-distance reset) gets no location rather than a fabricated one.
- [x] `app/services/dispersion.py`: 2D dispersion ellipse math (`compute_dispersion_ellipse`, `is_within_ellipse`) — the latter is the primitive a real "sucker pin" containment check would use, built and tested but not yet wired to a live pin position (see gap below).
- [x] `GET /api/rounds/{id}/holes` + `GET /api/rounds/{id}/holes/{number}/replay`: hole geometry (tee, green center, green boundary) plus this round's shots with GPS locations and their Phase 2 `approach_leave` classification.
- [x] Hole replay UI (`src/components/hole-replay/`): an SVG schematic (`HoleReplaySvg`) that always works — tee/green markers, green boundary, shot path, and the dispersion ellipse anchored at the approach shot's actual start position (its mean/stdev are *carry* distance, relative to where the club was swung, not an absolute hole position — this was a real bug caught during the manual visual check below and fixed). The tee→green line doubles as the "center-green aim comparison line." A real Mapbox GL layer (`HoleReplayMap`) renders satellite imagery + markers + the shot-path line when a token is configured, loading `mapbox-gl` via a dynamic `import()` so the ~500KB library isn't bundled for the (default, in this environment) no-token path.
- [x] Short-sided / "sucker pin" banner (`ShortSidedBanner`), driven by Phase 2's `approach_leave` classification, shown on the new `/rounds/[id]` hole-by-hole replay page.

**Gaps carried forward:**
- **No real Mapbox token in this environment** (no developer account configured here) — same boundary as Garmin OAuth in Phase 3. `HoleReplayMap` is real, complete code, verified to fall back correctly (and to recover from a map load error) with a mocked `mapbox-gl`, but the actual satellite-tile rendering is unverified against Mapbox's real servers.
- **No per-round pin position** — `Hole.green_center` is a static point, not where the pin was cut that day. This is the same root cause Phase 2/3 already flagged for the short-sided proxy; it also means `is_within_ellipse`'s real use ("is today's tucked pin inside my dispersion pattern") isn't wired up yet, and the aim line targets the green center rather than the actual pin. Both need a schema addition (a per-round pin location) that's out of scope here.

**Acceptance criteria:** dispersion ellipse math covered by unit tests (`tests/test_dispersion.py` — known mean/stdev → exact expected bounds, boundary-inclusive containment checks). Manual visual check of hole replay against the real seeded demo round, in a real browser (Playwright/Chromium) — this caught and fixed the ellipse-anchoring bug above, on top of confirming the SVG schematic, green boundary, shot path, and lateral offsets (e.g. hole 7's "Heel / Push-Slice" tag) all render correctly against real computed geometry.

## Phase 5 — Manual Round Entry & Course Builder (done, with noted gaps)

Goal: Garmin's Developer Program turned out to require a paid account (discovered after Phase 3 shipped OAuth plumbing against it) — auto-syncing rounds isn't viable for ordinary users. This phase pivots the primary "get data in" path to manual entry: build a course (with real GPS hole geometry), create a round against it, then enter shots hole-by-hole with a GPS location picked by clicking the hole map. It also finally wires up the audit wizard's client-only draft state (flagged as a gap since Phase 3) to real persistence.

- [x] `POST /api/courses` + `GET /api/courses` + `GET /api/courses/{id}` (`app/api/routes/courses.py`): create a Course with Holes (par, yardage, and optional tee/green-center/green-boundary geometry) in one call; idempotent on `osm_relation_id` (added as a nullable indexed `Course` column, migration `9c1f4e7a2b83`) so re-searching the same OSM course doesn't duplicate it.
- [x] `app/services/osm_courses.py` + `GET /api/courses/search-osm` + `GET /api/courses/search-osm/{type}/{id}`: searches OpenStreetMap's Overpass API (free, keyless — no billing risk, unlike Garmin's or a commercial golf-course API) for a course by name, then resolves each `golf=hole` way's tee/green by nearest-endpoint matching against `golf=tee`/`golf=green` features, computing yardage from the hole way's own geometry via the same flat-earth math `geometry.py` already uses. Coverage is inconsistent (well-known courses tend to be mapped, private/smaller ones often aren't), so every field is optional and the frontend always lets the user fill gaps by hand. **Unverified against the real Overpass API in this environment** — `overpass-api.de` is blocked by this sandbox's network egress policy (confirmed via the proxy status endpoint, same "gateway answered 403 to CONNECT" pattern as Mapbox), so this is real, unit-tested code (`tests/test_osm_courses.py`, hand-built fixtures shaped like real Overpass JSON) without a live round trip.
- [x] `POST /api/rounds` (general creation — `user_id`/`course_id`/`played_at`/`total_score`/`status`, unlike the FIT-only `POST /api/rounds/upload`) and `POST /api/rounds/{id}/shots/bulk` (resolves each shot's `hole_number` to the round's course's `hole_id`, accepts an optional GPS `location` per shot; 409 if the round has no course yet). Found and fixed a real pre-existing bug while building this: `GET /api/rounds/{id}/shots` returned raw `Shot` ORM objects, and geoalchemy2 hands back a `WKBElement` for `location` — not JSON-serializable — so any shot with GPS data crashed that endpoint with a 500. Never caught before because no earlier test exercised it against a located shot; both endpoints now build plain dicts instead, with a regression test.
- [x] Course builder UI (`src/components/course-builder/`, page `src/app/courses/new/`): search OSM and prefill, or start blank; place each hole's tee/green/boundary by clicking a map, one placement-mode toggle (`HoleGeometryEditor`) driving either the real Mapbox layer or the SVG fallback (`CourseGeometryMap`/`CourseGeometryMapSvg`), both sharing one interactive component so there's no separate read-only/editable implementation to keep in sync. Yardage auto-computes once both tee and green are placed (editable, not locked). The SVG fallback uses a new, deliberately separate `local-map.ts` projection (arbitrary-center, north-up) rather than reusing the hole-replay SVG's tee→green-relative one — course building has no aim line yet, that's what's being built.
- [x] Manual shot entry (`src/components/manual-entry/hole-shot-entry.tsx`, pages `src/app/rounds/new/` + `src/app/rounds/[id]/enter/`): create a round against an existing course, then click the *real* hole-replay map (`HoleReplayMap`/`HoleReplaySvg`, both extended with a new optional `onPick` prop — previously strictly read-only) to set each shot's GPS location before entering club/lie/distances/tag. Shots accumulate in the same `DraftShot`/IndexedDB draft-store infrastructure Phase 3 built (extended with an optional `location` field) and submit to the backend in one `POST /api/rounds/{id}/shots/bulk` call when the round is done — closing the "no persistence path" gap Phase 3's own code comments flagged. Clicking a map point needed a real inverse of the existing forward-only projection math (`offsetToLatLng`, `svgPointToOffset` in `lib/hole-replay/`) to turn a click back into a GPS point.
- [x] Garmin OAuth de-emphasized, not removed: the dashboard's "Connect your Garmin account" prompt (`src/app/page.tsx`) now points at manual entry (`/rounds/new`) instead. `app/services/garmin_oauth.py`, `app/api/routes/garmin_auth.py`, and `src/app/settings/garmin/` are untouched and still fully tested — reachable directly, just no longer promoted as the primary path, so reviving it costs nothing if Garmin's pricing changes.
- [x] `tools/garmin_import/` — a separate, personal-use CLI (not part of the deployed app) that authenticates to Garmin Connect with the user's own email/password (there's no OAuth path for the consumer site) and downloads `.FIT` files, feeding them into the existing `POST /api/rounds/upload` endpoint. Built against `garminconnect==0.3.2`'s actual installed source (inspected directly — login/token-caching/MFA-resume mechanics and golf method signatures are all verified, not guessed), with 16 unit tests mocking the underlying client. The `.FIT` download → upload path was verified end-to-end against a real running API (real multipart POST, real `Round` row created). **The golf-specific scorecard/shot-data endpoints' response shape is unverified** — same live-access boundary as Mapbox/OSM (Garmin's SSO/Connect hosts are blocked by this sandbox's network policy) — so `export`/`shots` dump raw JSON to a file rather than mapping it into `Course`/`Round`/`Shot`, which needs a real sample payload to do correctly rather than guessing at an undocumented API's field names. See that directory's README for the full ToS/fragility caveats and `docs/DATA_PRIVACY.md`'s boundary note on why this never touches the deployed app's credentials.

**Gaps carried forward:**
- **OSM Overpass connectivity is unverified live** in this sandbox (see above) — same category as Mapbox/Garmin. Query construction and response parsing are real and unit-tested against realistic fixtures, not a live round trip.
- **Bulk shot submission is purely additive** — there's no "edit a previously-submitted round" flow yet; resubmitting creates a second set of shots rather than replacing the first.
- **Course-search is name-only** — no location/bounding-box narrowing, so a common course name could return unrelated same-named courses in different states. Not a problem the manual review-before-save step doesn't already catch.
- **`tools/garmin_import/`'s scorecard/shot-data JSON has no schema mapper yet** — real per-shot Garmin data (club, lie, GPS) could in principle skip manual entry entirely once this exists; blocked on getting a real sample payload rather than guessing at field names.

**Acceptance criteria:** 192 backend tests (`test_courses_routes.py`, `test_osm_courses.py`, extended `test_rounds.py`), ruff clean. 225 frontend tests, eslint/tsc clean, production build succeeds (`/courses/new` and `/rounds/[id]/enter` both stay in the ~120kB First Load JS range, confirming the dynamic Mapbox import discipline from Phase 4 held). Full manual, real-browser (Playwright/Chromium) pass against a real Postgres+PostGIS instance: built a course from scratch by clicking tee/green/boundary points (verified the persisted GPS data and auto-computed yardage via the API afterward), then created a round against the real seeded demo course, added shots across two holes (one with a clicked GPS location, one without), submitted, and confirmed the round redirects into Phase 4's hole-replay view rendering the real submitted geometry — including a dispersion ellipse computed from the single located shot.

## Phase 6 — Practice Hub, R10/R50 Delivery & Coach Export (done, with noted gaps)

Goal: close the loop from diagnosis to prescribed practice, and serve the PGA Coach persona.

- [x] R10/R50 session ingestion: `PracticeSession`/`PracticeShot` tables (`app/models/practice.py`, migration `6dbab0f48375`) and `POST /api/practice/sessions/upload`, wiring Phase 1's `launch_monitor_parser` to persistence the same way `POST /rounds/upload` does for `.FIT` — malformed rows are reported back alongside a successful upload rather than aborting it.
- [x] `app/services/delivery_profile.py` + `GET /api/practice/delivery/{user_id}`: per-club aggregate delivery numbers (Club Path, Face Angle, a derived Face-to-Path, Spin Axis, Smash Factor, Carry), a per-club per-session trend, and the Sim vs. Real-World Gapping Delta against Smart Bag's on-course carry (`app/services/smart_bag.py`) — reuses that engine rather than duplicating it.
- [x] `app/services/practice_combines.py` + `GET /api/practice/combines/{user_id}`: detects the four PRD §7.1 weaknesses (Approach 100-125y SG, Driver dispersion, Iron smash factor, Putting lag efficiency) from data already computed elsewhere (round Strokes Gained, Smart Bag, delivery profile, putting mechanics) and maps each to its fixed PRD §7.1 combine — a 1:1 mapping, not a generic recommendation bucket. Thresholds are grounded two ways (see the module's "Calibration notes"): driver dispersion and putting lag are matched exactly to their own PRD §7.1 target metric (15y, 80%) rather than a separate guess; iron strike quality uses per-club expected smash-factor bands (see follow-up note below) instead of one flat number. Only the approach-100-125y bracket has no directly comparable PRD number to align to, so it stays this implementation's own calibration (SG < 0 relative to the player's own handicap bucket) — same caveat as Phase 1's `SCRATCH_CURVES` note.
- [x] `VirtualRound` (`app/models/virtual_round.py`) + `POST`/`GET /api/virtual-rounds`: a deliberately separate table from `Round`, not a subtype or status flag on it, so "segregated from real-world handicap calculations" (PRD §6.2) holds by construction rather than by a filter someone could forget.
- [x] Practice Hub UI (`src/app/practice/`): R10/R50 upload widget, a combine card per detected weakness (instructions, target metric, curated-video-search link), the delivery profile table, a per-club smash-factor trend chart (`recharts`, dynamically imported — see bundle-size note below), and the Sim vs. Real-World gapping table.
- [x] Virtual/Sim Round Hub UI (`src/app/virtual-bag/`): log a sim round (Home Tee Hero/E6/GSPro) and see the log, visually separate from the real-world Rounds pages.
- [x] 1-Page "Coach-Ready" Lesson Brief (`src/lib/coach-brief/coach-brief-document.tsx`, `@react-pdf/renderer`): net stroke leaks (SG by category, worst first), strike patterns (approach shot outcomes), Tiger 5 metrics, and a recommended coaching agenda reusing the same weakness → combine mapping the Practice Hub shows. Generated client-side on click via a dynamic `import()` (same discipline as Mapbox in Phase 4/5 and the delivery trend chart above) so the renderer never loads on an ordinary page visit. Two real bugs caught by rendering an actual PDF rather than trusting the component tree: react-pdf's built-in Helvetica (WinAnsi encoding) silently mangles `≥`/`±`/`°` into wrong glyphs instead of erroring, so combine text is sanitized before rendering (`pdfSafeText`); and an early draft surfaced an "Unclassified miss" row that was actually every non-approach shot (tee shots, putts, penalty markers) miscounted as a miss — dropped, since `ApproachLeave.unclassified` isn't a strike pattern a coach could act on.

**Gaps carried forward:**
- **Combine video links are a YouTube search query, not a curated video** — PRD §7.1 wants "curated video tutorials"; no video library or curation pipeline exists yet, so each combine links to a search for its drill name instead of guessing at a specific real video URL. Deliberately still open: filling this in for real needs either a curation pipeline or actual video URLs from a human, not a guess.
- **Approach-100-125y threshold is still this implementation's own calibration** — not validated against real player data or PGA coaching guidance. Driver dispersion, iron strike quality, and putting lag are no longer in this category — see the follow-up note below.
- **`tools/garmin_import/`'s unmapped scorecard JSON (Phase 5 gap) would be the natural feeder for R10/R50 sim-round delivery data** — still blocked on a real sample payload, so `VirtualRound` and `PracticeSession` are both manual-entry-only for now, same as Phase 5's manual round entry.

**Follow-up — threshold calibration pass:** the original iron-strike-quality detector used one flat smash-factor cutoff (1.30) across every iron, which is physically wrong — smash factor falls with loft, so the same number either misses struggling long-iron players or wrongly flags short-iron players who are fine for that club. Replaced with `EXPECTED_SMASH_FACTOR_BY_IRON`, a per-club (2-Iron through 9-Iron) expected-value table grounded in commonly-published launch-monitor averages (order-of-magnitude accurate, not licensed data — same caveat as `SCRATCH_CURVES`); the detector now flags a club only when its own average falls >0.05 below its own expected value, and reports the worst-offending club in the signal detail. Also re-grounded driver dispersion and putting lag against their own PRD §7.1 target metrics exactly (driver was already correct at 15y; putting lag moved from an arbitrary 70% to the PRD's actual 80% bar) rather than softer made-up numbers, and raised minimum sample sizes (approach bracket and putting lag: 3 → 5) since 3 data points is easy to hit by chance in one round. 8 new/updated backend tests in `test_practice_combines.py` lock in the per-club behavior (a 9-Iron and a 3-Iron averaging the same 1.30 smash factor now correctly get different verdicts).

**Acceptance criteria:** 232 backend tests (40 new: `test_delivery_profile.py`, `test_practice_combines.py`, `test_practice_routes.py`, `test_virtual_rounds_routes.py`), ruff clean, migration verified to apply cleanly to a fresh Postgres+PostGIS instance. 268 frontend tests (26 new), eslint/tsc clean, production build succeeds with `/practice` at ~125kB First Load JS (recharts and `@react-pdf/renderer` both dynamically imported, so neither inflates the base bundle). Full manual, real-browser (Playwright/Chromium) pass against a real Postgres+PostGIS instance and the reseeded demo round: uploaded a real R10/R50 CSV fixture through the Practice Hub and watched the delivery profile, trend chart, and gapping table populate; logged a sim round through the Virtual Bag hub; and downloaded a real Coach-Ready Brief PDF from the dashboard, opened it, and visually confirmed every section (this is what caught both bugs noted above).

## Phase 7 — Data Privacy & Retention (done, with noted gaps)

Goal: close out the cross-cutting Data Privacy to-do below — overdue since "no later than Phase 3" — before any more real user data accumulates.

- [x] `GET /api/users/{user_id}/export` + `DELETE /api/users/{user_id}` (`app/api/routes/privacy.py`): a JSON export of everything a user has put into the app, and a real hard delete (not a soft flag) of everything they own — shots, rounds, R10/R50 practice sessions/shots, virtual rounds, and the Garmin OAuth connection — in FK-safe order. `Course`/`Hole` rows are deliberately untouched since they're shared course reference geometry, not this user's data.
- [x] `/settings/privacy` UI: a "Download my data" button, a "Delete my account" flow gated behind typing `DELETE` to confirm (irreversible, so no one-click destructive action), and a plain-language privacy notice covering legal basis, retention, and CCPA disclosure — explicitly labeled "Draft — pending legal review" in the product itself, not just in code comments, since `docs/DATA_PRIVACY.md` says this shouldn't be presented as a finished policy.
- [x] `SettingsTabs` (`src/components/settings/`): a small shared sub-nav between `/settings/garmin` and the new `/settings/privacy` — neither is linked from the main `NavBar` (PRD §8's nav is a fixed 5-item list), so this is what ties the two settings pages together.
- [x] `docs/DATA_PRIVACY.md` updated: every to-do item now points at real code, and the retention policy is explicit rather than implicit (no auto-purge — round/shot/practice data is retained until account deletion; Garmin tokens rotate on reconnect and are deleted on disconnect, unchanged from Phase 3).

**Gaps carried forward:**
- **The privacy notice itself is not legal-reviewed** — it's a good-faith engineering draft of the required disclosures, explicitly labeled as such in the UI. Actual launch requires counsel review, which is outside this repo's scope.
- **No automated retention *enforcement*** — the policy (retain until deletion) doesn't require a background job to enforce, since there's no auto-expiry to run. If a future retention window is added (e.g. purge inactive accounts after N years), it would need one.
- **Smart Bag baseline minimization has no code yet** — verified there's currently no pipeline aggregating real user shots into a shared baseline (`StrokesGainedBenchmark` is a fixed hand-authored curve, not user-derived), so there's nothing to minimize yet. Flagged in `DATA_PRIVACY.md` so it isn't forgotten if that pipeline is ever built.

**Acceptance criteria:** 240 backend tests (8 new: `test_privacy_routes.py`, covering export shape, token exclusion, full deletion, and that shared `Course`/`Hole` data survives), ruff clean. 277 frontend tests (9 new), eslint/tsc clean, production build succeeds with `/settings/privacy` at ~124kB First Load JS. Full manual, real-browser (Playwright/Chromium) pass: downloaded a real JSON export for a seeded user and inspected its contents, then ran the full type-DELETE-to-confirm flow and verified via direct DB query that the user row and all owned rows were actually gone (not soft-deleted) while the shared course/hole data they'd played was left intact.

## Phase 8 — Named, Persistent Player Identity (done, with noted gaps)

Goal: every page up to this point made whoever was using the app retype a raw numeric user ID — no name, no memory across a reload or a different page. That was never a deliberate design choice, just the "no login yet" placeholder never getting revisited; this phase replaces it with a name-based player picker persisted client-side, without building real authentication (still out of scope — see PRD §1.3 non-goals).

- [x] `app/api/routes/users.py`: `POST /api/users` (create, name + email), `GET /api/users?q=` (name search, returns only `{id, name}` — not email/handicap, since search results can surface *other* people's accounts on a shared device), `GET /api/users/{id}` (fetch, for resolving a persisted local id). None of this existed before — there was no way to create a user through the API at all; only `app/db/seed.py` and tests could.
- [x] `GET /api/rounds?user_id=` filter (`app/api/routes/rounds.py`): a real, pre-existing bug this phase made obvious rather than introduced — the dashboard picked the single most-recently-played round *across every user in the database*, unfiltered, silently. Harmless when "user ID" was a number nobody looked at twice; actively wrong once identity is a persisted name someone recognizes as *not theirs*.
- [x] `src/lib/current-user.tsx`: `CurrentUserProvider` + `useCurrentUser()`, localStorage-backed. Re-validates the stored id against `GET /api/users/{id}` on load and clears it silently on a 404 (the player deleted their account via Phase 7's `/settings/privacy` since this browser last used it) rather than leaving the app acting as a user ID that no longer exists.
- [x] `src/components/player-switcher/player-switcher-dialog.tsx`: search-as-you-type by name, or create a new player (name + email) — a `@base-ui/react` `Dialog`, matching the existing precedent in `strike-quality-modal.tsx` rather than introducing a new UI dependency. Mounted once in `CurrentUserProvider` (in `layout.tsx`) so any page can trigger it via `openPicker()`, not just the `NavBar` trigger that shows "Playing as `<name>`" / "Choose player".
- [x] Every page that had its own numeric "User ID" input — dashboard, Practice Hub, Virtual Bag, `/settings/garmin`, `/settings/privacy`, `/rounds/new` — now reads `useCurrentUser()` instead, with a shared `<NoPlayerSelected>` empty state (`src/components/no-player-selected.tsx`) replacing the input entirely.
- [x] Real bug caught by the live-browser pass, not the unit tests: deleting the current player's account (`/settings/privacy`) called `clearUser()`, which flipped `user` to `null` and immediately swapped the whole panel over to `<NoPlayerSelected>` — unmounting the "your account was deleted" confirmation before it could ever be seen. Fixed by lifting the "just deleted" confirmation out of `DeleteAccountPanel` into a page-level state independent of `user`, so it stays visible after the player is cleared.

**Gaps carried forward:**
- **Still no real authentication** — anyone can pick any existing player's name from the search box and start acting as them; the picker is a convenience for a single-user/single-household deployment, not an access control. Matches PRD §1.3's explicit non-goal, called out here so it isn't mistaken for an oversight.
- **No merge/rename flow** — creating a player with a near-duplicate name (typo, nickname) has no path back to the original except manual deletion and re-entry.

**Acceptance criteria:** 258 backend tests (10 new: `test_users_routes.py`, plus a `GET /api/rounds?user_id=` filter test in `test_rounds.py`), ruff clean. 306 frontend tests (19 new: `current-user.test.tsx`, `player-switcher-dialog.test.tsx`, `settings-tabs` unaffected, plus new/updated page tests for the dashboard, `/practice`, `/virtual-bag`, `/rounds/new`, `/settings/garmin`, `/settings/privacy`), eslint/tsc clean, production build succeeds (bundle grew ~20kB across every page, expected — the player switcher now mounts globally via `layout.tsx`). Full manual, real-browser (Playwright/Chromium) pass: created a named player from scratch, confirmed it persisted across a reload and resolved automatically on every migrated page with no re-entry, deleted the account and watched the confirmation message actually render (this is what caught the bug above), and forged a stale localStorage entry pointing at a nonexistent user id to confirm the app recovers to "Choose player" instead of getting stuck.

---

# Part II — Hardening (Phases 9-13)

Phases 0-8 built the product surface the PRD describes: ingestion, analytics, the
hole replay, the Practice Hub, privacy endpoints, player identity. This second
part comes out of a full-repo review rather than the PRD, and closes the gap
between "every PRD feature has a screen" and "this is safe to run for someone
other than its author."

The ordering is deliberate. Phase 9 is an enabling phase — the backend test
suite currently can't isolate a test from its neighbours, and Phase 10 is the
first phase where a test asserting "user A *cannot* reach user B's data" has to
be trustworthy. Everything after 10 is independent and can be reordered freely.

## Phase 9 — Test Foundation & Backend Test Isolation (done, with noted gaps)

Goal: make `make test` work on a clean checkout, and give the backend suite real
per-test isolation, so the access-control tests Phase 10 depends on can be
believed. Every route test module built `TestClient(app)` at import time and
wrote through the real `app.db.session.engine`: 72 of 258 tests failed outright
without a running Postgres, and the ones that passed shared one mutable database
with no rollback between them. The `uuid4()` email in nearly every seed helper
was the workaround for that missing isolation, not a stylistic choice — and
`test_courses_routes.py` said so in a comment ("a real Postgres DB shared across
test runs (no rollback-per-test), so a fixed id would collide with a leftover
row from an earlier run").

- [x] `apps/api/tests/conftest.py`: a `db_session` fixture wrapping each test in
  an outer transaction that is always rolled back, using SQLAlchemy 2.0's
  `join_transaction_mode="create_savepoint"` so the `session.commit()` calls
  inside route handlers still behave normally, and a `client` fixture that binds
  that same session into the app via `app.dependency_overrides[get_session]` —
  seeding and the request under test have to share one transaction, or seeded
  rows are invisible to the handler.
- [x] **The suite no longer touches the development database at all.** Rollback
  isolation alone doesn't fix this: rows that were *already there* (from `make
  seed`, or from every previous run of the un-isolated suite) still break
  assertions. Found the hard way — the first migrated test failed against a
  `Zaphod` row an earlier run had committed permanently. The suite now
  provisions and migrates its own `debrief_golf_test` database, overridable with
  `TEST_DATABASE_URL`.
- [x] `alembic/env.py` honours an explicitly-supplied `sqlalchemy_url` over
  `DATABASE_URL`, so the harness can migrate its own database. Unset for
  ordinary CLI runs, which behave exactly as before.
- [x] Actionable failure when Postgres isn't there: a raw
  `psycopg.OperationalError` is replaced by one message naming `make db-up` and
  the pure-logic subset. Scoped to the `db_session` fixture, so the 186
  pure-logic tests (parsers, strokes gained, geometry, combines) still run with
  no database at all — verified by pointing `DATABASE_URL` at a dead port.
- [x] All 12 route test modules moved onto the fixtures; no module-level
  `TestClient(app)` or direct `engine` use is left. Every `uuid4()` seed value
  is gone, replaced by fixed readable ones, and assertions that had to be vague
  about shared state got tightened (`GET /api/rounds` now asserts the exact list
  rather than `any(...)`).
- [x] `tests/test_isolation.py` proves the guarantee instead of assuming it: one
  test commits a user, the next asserts the unique email is free again, a third
  asserts a handler's commit *is* visible mid-test, and a fourth asserts the
  suite isn't pointed at the development database. Mutation-checked — disabling
  the rollback makes the second test fail, so it's a real assertion.
- [x] `make db-up` / `make db-down` (compose `--wait`, so nothing races the
  server's healthcheck), `test-api` and `migrate` depend on them, and the README
  describes what actually happens.
- [x] CI: a `tools` job linting and testing `tools/garmin_import`, which had 16
  tests from the day it landed and nothing that ever ran them. Added a
  `ruff.toml` mirroring `apps/api`'s rules, since it's a standalone pip project
  outside the uv workspace.

**Gaps carried forward:**
- **`make test` still doesn't cover `tools/garmin_import`** — only CI does. It's
  a pip/venv project rather than part of the uv workspace, and wiring venv
  bootstrapping into the Makefile seemed worse than the inconsistency.
- **Nothing checks models against migrations.** Tests now run on migrated
  schema, which is the right source of truth, but a model change with no
  corresponding migration still fails silently in both. An "autogenerate
  produces an empty diff" check belongs in Phase 12's CI work.
- **The compose path wasn't exercisable in the environment this phase was built
  in** (no Docker daemon available). `make db-up`'s compose invocation is
  unverified; everything downstream of it was verified against a local PostGIS
  16/3.4 server — the same server and PostGIS versions compose and CI both use.

**Acceptance criteria:** 262 backend tests (4 new, all in `test_isolation.py`),
green from a dropped database — the suite recreated, migrated, and ran against a
clean `debrief_golf_test` in one command. ruff clean. Pure-logic tests (41 of
them, run in isolation) still pass with `DATABASE_URL` pointed at a closed port.
`alembic upgrade head` from the CLI still targets `DATABASE_URL`. Frontend
unchanged and unaffected: 306 tests, no source files touched. Suite runtime went
from 3.47s to 3.53s including provisioning, so isolation cost nothing.

## Phase 10 — Authentication & Authorization

Goal: stop taking the caller's identity from the caller. Every endpoint takes
`user_id` as a query or path parameter and trusts it, which was a reasonable
placeholder while the app was a personal dashboard, but Phase 7 built the
privacy endpoints on top of that placeholder and Phase 8's picker made "acting
as another named person" a two-click operation. The result is that the GDPR/CCPA
rights `docs/DATA_PRIVACY.md` commits to are currently granted to everybody:

- `GET /api/users/{user_id}/export` returns any user's email, every round, and
  every GPS-tagged shot location — walkable by incrementing an integer.
- `DELETE /api/users/{user_id}` hard-deletes any account, unauthenticated, by
  design ("a real deletion, not a soft flag").
- `GET /api/users?q=` enumerates real names; `GET /api/users/{id}` then returns
  that user's email and handicap. The search endpoint's deliberate `{id, name}`
  narrowing is undone by the fetch endpoint next to it.
- `GET /api/rounds` with no `user_id` still returns every round in the database.

- [ ] A real session: credential storage, login/logout, and a signed
  session cookie. Scope it to what this app actually is — a small
  single-household deployment — rather than importing a full identity provider.
- [ ] A `current_user` FastAPI dependency, and every `user_id` parameter derived
  from it instead of from the request. Where an endpoint legitimately addresses
  another user's row (none today), that becomes an explicit authorization check.
- [ ] Ownership checks on every round-scoped and session-scoped route: a round
  id belonging to another user is a 404, not a payload.
- [ ] Refuse to boot with the default `SECRET_KEY` when `env != "development"` —
  it signs the Garmin OAuth state token and would sign session cookies too.
- [ ] Encrypt the Garmin `access_token`/`refresh_token` columns at rest, or
  document explicitly why plaintext is accepted.
- [ ] Tighten CORS off `allow_methods=["*"] / allow_headers=["*"]` once the
  cookie flow fixes the real method and header set.
- [ ] Frontend: a login screen, and `CurrentUserProvider` reading the session
  instead of localStorage. The player switcher becomes account switching, and
  the `localStorage` id becomes a hint, not an identity.

**Acceptance criteria:** every endpoint that touches user data rejects an
unauthenticated request; a test per privacy endpoint proving user A gets a
404/403 for user B's data (this is the suite that needs Phase 9's isolation).
Phase 8's "still no real authentication" gap closes, and PRD §1.3's non-goal is
updated to match.

## Phase 11 — Performance & Scale

Goal: the query patterns are all correct and all shaped for a demo dataset.
Fix them before there's production data to migrate around.

- [ ] Index the columns every query filters on: `round.user_id`,
  `shot.round_id`, `shot.hole_id`, `hole.course_id`. The initial migration
  created these FKs without indexes; later migrations did index
  `practice_session.user_id` and `practice_shot.session_id`, so this is an
  oversight in the original tables, not a policy.
- [ ] Replace the two-step `SELECT round.id WHERE user_id` → `WHERE round_id IN
  (...)` pattern with joins (`bag.py`, `practice.py` ×2, `privacy.py`). Two
  round trips and an unbounded `IN` list per request today.
- [ ] `GET /rounds/{id}/analytics` recomputes strokes gained and writes it back
  to every shot on every call — a non-idempotent GET on the dashboard's hot
  path. Compute on shot submission or cache; let the GET read.
- [ ] `list_round_holes` loads every shot in a round to produce per-hole counts;
  make it a `GROUP BY`.
- [ ] Paginate `GET /rounds` and `GET /courses`, and let the dashboard ask for
  the most recent round via `ORDER BY played_at DESC LIMIT 1` instead of sorting
  the full list client-side.
- [ ] Cap upload size on `POST /rounds/upload` and
  `POST /practice/sessions/upload` — both `await file.read()` the whole body
  into memory with no limit, no content-type check, and no rate limit.
- [ ] FK `ondelete="CASCADE"` so `privacy.py`'s deletion stops loading every
  child row into Python to delete it one at a time.

**Acceptance criteria:** a seeded benchmark (hundreds of rounds, tens of
thousands of shots) where the dashboard and Smart Bag endpoints stay flat rather
than degrading linearly; an oversized upload rejected with a 413 instead of
growing the container's RSS.

## Phase 12 — Observability & Operational Readiness

Goal: `grep -rn "import logging" apps/api/app` currently returns nothing. An
unhandled exception is a bare 500 with nothing on disk to explain it.

- [ ] Structured logging with a request id, and exception handlers that log the
  traceback while returning a clean error body.
- [ ] Split `/api/health` (process is up) from `/api/ready` (database reachable)
  — they're conflated today, so the container reads as dead whenever Postgres
  blips.
- [ ] CI: Python type checking (mypy or pyright — `bag.py` already carries a
  `# type: ignore[arg-type]`, exactly where a checker earns its keep),
  dependency and secret scanning (Dependabot, CodeQL, `pip-audit`/`pnpm audit`),
  coverage reporting, and a build of the prod Docker targets, which are never
  exercised today.
- [ ] A `CLAUDE.md` recording the conventions this repo already follows —
  raw-column selects to avoid geoalchemy2's non-serializable `WKBElement`, the
  PRD-section-reference comment style, the phase-per-PR rhythm.

**Acceptance criteria:** a deliberately-thrown error produces a correlatable log
line; CI fails on a known-vulnerable dependency and on a type error.

## Phase 13 — Frontend Data Layer & Error Boundaries

Goal: `use-dashboard-data.ts`, `use-practice-data.ts`, and
`use-virtual-rounds.ts` each hand-roll loading/error/cancel/refresh state. The
implementations are careful — the `cancelled` flag handling is correct — but
the pattern is now written three times, and there's no caching, dedupe, retry,
or revalidation, so every navigation refetches from scratch.

- [ ] Adopt SWR or TanStack Query and collapse the three hooks onto it.
- [ ] Add `error.tsx`, `loading.tsx`, and `not-found.tsx` — none exist anywhere
  under `apps/web/src/app/`, so a throw in any segment hits Next's default
  screen, including from the map components most likely to throw.
- [ ] Remove the dashboard's request waterfall (`getRounds` → client-side sort →
  `getRoundAnalytics`) once Phase 11 adds the server-side "latest round" query.

**Acceptance criteria:** no bespoke fetch-state machines left in `src/lib`; a
forced throw in a route segment renders a recoverable error UI rather than the
framework default.

## Backlog (not yet scheduled into a phase)

- `get_round_analytics` does `holes[shot.hole_id]` against a dict built only
  from the round's *current* course — a shot whose hole belongs to a
  since-changed course raises `KeyError` and returns a 500 where a 409 is meant.
- `create_shots_bulk` is documented as purely additive with no edit path, so a
  double-submit from a flaky network silently duplicates a hole's shots. Needs
  an idempotency key or a `(round_id, hole_id, shot_number)` uniqueness rule.
- No merge/rename flow for near-duplicate players (carried from Phase 8).

## Cross-cutting (ongoing, not a single phase)

- **Data privacy:** delivered as Phase 7 — see [`docs/DATA_PRIVACY.md`](./DATA_PRIVACY.md) for the remaining non-engineering gap (legal review of the user-facing notice). The access-control hole that makes those endpoints reachable by anyone is Phase 10.
- **Player identity:** delivered as Phase 8 above — still not real authentication, by design; Phase 10 is where that gap actually closes.
- **CI:** keep `.github/workflows/ci.yml` green; add new test suites to the existing `backend`/`frontend` jobs rather than creating parallel pipelines.
