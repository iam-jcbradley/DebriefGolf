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

## Phase 10 — Authentication & Authorization (done, with noted gaps)

Goal: stop taking the caller's identity from the caller. Every endpoint took
`user_id` as a query or path parameter and trusted it, which was a reasonable
placeholder while this was a personal dashboard — but Phase 7 built the privacy
endpoints on that placeholder and Phase 8's picker made "acting as another named
person" a two-click operation. The GDPR/CCPA rights `docs/DATA_PRIVACY.md`
commits to were, in practice, granted to everybody: `GET /api/users/{id}/export`
returned any account's email, rounds and GPS shot traces to an unauthenticated
caller walking integers, and `DELETE /api/users/{id}` hard-deleted any account.

- [x] **Sessions.** Argon2id password hashing (`argon2-cffi`, OWASP's current
  first choice) and an HMAC-signed session token in an HttpOnly, SameSite=Lax
  cookie. `app/core/signing.py` was extracted from the Phase 3 Garmin `state`
  token, which already had exactly this shape — one signing implementation now
  serves both.
- [x] **`CurrentUser` dependency** (`app/api/deps.py`), and every `user_id`
  parameter across rounds, bag, practice, virtual rounds, privacy, courses and
  Garmin routes replaced by it. **No endpoint accepts a user id any more** — the
  capability was removed rather than guarded.
- [x] **Ownership checks** on every id-addressed route, returning 404 rather than
  403: a 403 confirms the row exists, which is more than a stranger should learn
  by guessing integers.
- [x] `/api/users` is gone entirely, and with it the name-search endpoint that let
  anyone enumerate other players. `POST /api/auth/register`, `/login`, `/logout`,
  `GET|PATCH /api/auth/me` replace it; export and delete moved to `/api/me/export`
  and `DELETE /api/me`, which have no way to name a subject. `PATCH /api/auth/me`
  also closes a real gap: handicap index feeds the SG benchmark bucket and there
  was previously no way to set it outside the seed script.
- [x] **Refuses to boot** on the example `SECRET_KEY` when `ENV != development` —
  a hard failure at import, not a log line nobody reads.
- [x] **Garmin tokens encrypted at rest** (Fernet, key derived from `SECRET_KEY`
  with domain separation). The columns are renamed `*_encrypted` so a plaintext
  token assigned to one reads as a bug. The migration deletes existing rows
  rather than encrypting them in place: anything written before this point sat in
  the clear in the database and every backup of it, so those tokens should be
  considered exposed and re-obtained, which costs one click.
- [x] CORS narrowed from `allow_methods=["*"] / allow_headers=["*"]` to what the
  frontend actually sends, plus `allow_credentials` for the cookie.
- [x] **Frontend rebuilt on sessions**: a `/login` screen (sign in + create
  account), `CurrentUserProvider` reading `GET /api/auth/me` instead of
  localStorage, the player-switcher dialog deleted, credentialed fetches, and
  `SignedOut` replacing `NoPlayerSelected` on every player-scoped page. The
  upload/form components no longer take a `userId` prop — they have no say in
  whose data it is.
- [x] **`tests/test_access_control.py`**: enumerates the live API surface from the
  OpenAPI schema and asserts every endpoint 401s without a session, so a route
  added without `CurrentUser` fails the suite by default rather than needing
  someone to remember to test it. Plus per-resource cross-user denial, and
  explicit tests that the two endpoints this phase existed to fix now return only
  the caller's own data.

**Gaps carried forward:**
- **Sessions are stateless, so there's no server-side revocation.** Logout clears
  the cookie, but a token already copied out of a browser stays valid until it
  expires; rotating `SECRET_KEY` is the only way to invalidate every outstanding
  session at once. Right trade at this size, wrong one for multi-tenant — that
  would want session rows.
- **No password reset or change flow.** A forgotten password currently means a
  new account. Needs an email-sending path this app doesn't have yet.
- **Pre-Phase-10 accounts can't log in.** `password_hash` is nullable and
  `verify_password` treats null as "can't log in" rather than "no password
  needed" — deliberate, but it means existing rows need a password set out of
  band (or `make seed` re-run) before they're usable.
- **A session expiring mid-visit surfaces as a page-level error**, not an
  automatic bounce to `/login`. A 401 interceptor in `apiFetch` belongs with
  Phase 13's data-layer work.
- **No rate limiting on login.** Argon2 makes each guess expensive, which is not
  the same as bounding them. Belongs with Phase 11's upload limits.

**Acceptance criteria:** 329 backend tests (84 new across `test_auth_routes.py`
and `test_access_control.py`), ruff clean; the access-control enumeration was
mutation-checked by removing `CurrentUser` from one route and confirming the
suite fails. 301 frontend tests (6 new for `/login`, `current-user.test.tsx`
rewritten for sessions), eslint and `tsc --noEmit` clean, production build
succeeds with `/login` at ~123kB First Load JS. `make seed` prints the demo
account's credentials, and an unauthenticated `curl /api/rounds` answers 401.

## Phase 11 — Performance & Scale (done, with noted gaps)

Goal: the query patterns were all correct and all shaped for a demo database
holding one round. Fix them before there's production data to migrate around.

Measured with `apps/api/scripts/benchmark.py`, which seeds 300 rounds and
21,600 shots per user (two users, so an endpoint that stopped scoping to the
caller shows up as both wrong and slow) and times the endpoints the dashboard,
Smart Bag and Practice Hub actually call. Median ms, same machine, before → after:

| endpoint | before | after | |
|---|---|---|---|
| `GET /rounds` | 5.3 | 3.6 | |
| `GET /rounds?limit=1` | — | 2.7 | what the dashboard now asks for |
| `GET /rounds/{id}/analytics` | 64.4 | 5.7 | **11x** |
| `GET /rounds/{id}/holes` | 7.4 | 4.1 | |
| `GET /bag` | 525.2 | 195.7 | **2.7x** |
| `GET /practice/delivery` | 500.6 | 200.8 | **2.5x** |
| `GET /practice/combines` | 543.7 | 245.7 | **2.2x** |
| `GET /me/export` | 366.9 | 341.3 | unchanged by design — it returns everything |

- [x] **Indexes** on `round.user_id`, `shot.round_id`, `shot.hole_id`,
  `hole.course_id`. The initial migration created these foreign keys without
  them; later migrations *did* index `practice_session.user_id` and
  `practice_shot.session_id`, so it was an oversight rather than a policy.
- [x] **`ON DELETE CASCADE`** on the ownership foreign keys, and
  `DELETE /api/me` reduced from a row-by-row ORM walk over every shot, round,
  practice shot, session and virtual round to a single `session.delete(user)`.
  Deliberately not applied to `shot.hole_id`, `hole.course_id` or
  `round.course_id`: courses and holes are shared reference geometry, and
  DATA_PRIVACY.md is explicit that deleting one user must not delete them.
- [x] **Joins** replacing the "select this user's round ids, then select shots
  where `round_id IN (...)`" pattern in `bag.py`, `practice.py` (×2) and
  `privacy.py` — two round trips and an IN list that grew with every round the
  user ever played.
- [x] **The analytics GET no longer writes.** It used to recompute Strokes
  Gained and write it back to every shot in the round on every call — a
  non-idempotent GET taking a write lock on the dashboard's hot path. The
  cause was hidden coupling: `tiger_five` read `Shot.strokes_gained` off the
  ORM objects, so the endpoint had to mutate them first. `evaluate_hole`/
  `evaluate_round` now accept the values explicitly, stored SG is written when
  shots are recorded, and `PATCH /api/auth/me` recomputes it when the handicap
  index (which sets the SG benchmark bucket) changes.
- [x] **Raw columns instead of ORM objects** for the three endpoints that walk
  every shot a player has ever recorded. Profiling showed the cost wasn't the
  PostGIS geometry (deferring it saved 8%) but ORM instantiation: 338ms for
  21,600 `Shot` objects vs 69ms for the five columns actually read.
  `app/services/shot_view.py` makes that contract explicit. This was the single
  biggest win on `/bag` and both practice endpoints — the indexes did nothing
  for them, because they read all of the user's rows regardless.
- [x] **`GROUP BY`** for per-hole shot counts, which loaded every shot in a
  round to count them in Python.
- [x] **Pagination** on `GET /rounds` and `GET /courses` (with a name filter),
  and the dashboard now asks for `?limit=1` instead of fetching every round and
  sorting client-side to pick the newest.
- [x] **Upload limits**, in two layers: an ASGI middleware that refuses an
  oversized `Content-Length` before routing or body parsing, and a chunked read
  capped at 10 MiB inside the handler for requests that declare no length. The
  middleware matters because by the time a handler runs, FastAPI has already
  parsed and spooled the multipart body — a check inside the handler bounds
  memory but not the parse.

**Gaps carried forward:**
- **The aggregate endpoints are now bound by Python-side aggregation** over all
  of a user's shots (~200ms at 21,600). Going further means aggregating in the
  database or keeping a per-club summary table — a bigger change that would move
  the IQR outlier rejection into SQL, and not worth it until someone has that
  much data.
- **Nothing is cached.** Every dashboard load recomputes the same round's
  analytics from scratch. Cheap now that the GET is read-only and idempotent,
  which is precisely what makes caching possible later.
- **`GET /me/export` is unchanged and unbounded** — it returns every row the
  user owns, by definition. Fine for a deliberate, rare export; it would want
  streaming or a background job if accounts get much larger.
- **No rate limiting** on uploads or login (carried from Phase 10). Size limits
  bound one request, not a thousand of them.

**Acceptance criteria:** 335 backend tests (5 new: `test_upload_limits.py`,
plus a test that the analytics GET writes nothing and one that shots get SG
when recorded), ruff clean. 301 frontend tests, eslint/tsc/build clean. The
migration was verified up, down and up again against a real PostGIS instance.
Benchmark numbers above are reproducible with
`uv run python scripts/benchmark.py`.

## Phase 12 — Observability & Operational Readiness (done, with noted gaps)

Goal: `grep -rn "import logging" apps/api/app` used to return nothing. An
unhandled exception was a bare 500 with nothing on disk to explain it.

- [x] **Structured logging + request-id correlation** (`app/core/logging.py`,
  `app/api/observability.py`): stdlib `logging` (no new dependency — a JSON
  formatter is a dozen lines) emitting one JSON object per line, tagged with a
  per-request id from a contextvar. `RequestIdMiddleware` generates one id per
  request, echoes it as `X-Request-Id`, and logs a `method path -> status in
  Nms` line on every response. A catch-all `Exception` handler
  (`unhandled_exception_handler`) logs the full traceback server-side and
  answers with `{"detail": "Internal server error", "request_id": ...}` — no
  traceback in the body. Ordinary `HTTPException`s (404s, 401s, 422s) never
  reach it; only genuine bugs do.
  - Two real bugs found building this, both fixed: (1) `ServerErrorMiddleware`
    sends the handler's response over the raw ASGI `send` channel once
    built, so it never flows back down through `RequestIdMiddleware` the way
    an ordinary response does — the handler now sets its own `X-Request-Id`
    header instead of relying on the middleware to. (2) `alembic/env.py`'s
    `fileConfig(config.config_file_name)` used the default
    `disable_existing_loggers=True`, which silently disabled every logger
    that already existed at that point — including this app's own, since
    `tests/conftest.py` runs `command.upgrade()` in-process *after*
    `app.main` has already configured them. Passing
    `disable_existing_loggers=False` (the same guard uvicorn's own default
    logging config uses) fixed it; this would have bitten in production too,
    for anyone who runs migrations in-process on startup.
- [x] **`/api/health` vs `/api/ready`** (`app/api/routes/health.py`): `/health`
  is liveness only, no DB dependency at all — a Postgres blip can no longer
  make a perfectly fine process read as dead. `/ready` does the real `SELECT
  1` round-trip and answers 503 (not a bare 500) when the database is
  unreachable. `docker-compose.yml`'s `api` service now has a real
  healthcheck pointed at `/health` for exactly this reason. Both are public
  (added to `PUBLIC_ENDPOINTS` in `test_access_control.py`) — a probe can't
  hold a session.
- [x] **CI — type checking** (`pyright`, added to `[tool.pyright]` in
  `apps/api/pyproject.toml`): basic mode. Investigated all 101 pre-existing
  diagnostics rather than blanket-suppressing; two in
  `app/services/tiger_five.py` were real (a nullable-PK dict lookup and a
  `float | None` narrowing gap from calling the same helper twice in one
  boolean expression — fixed with a walrus, which also stopped computing SG
  twice per shot) and got fixed, not silenced. The other 99 are systemic
  SQLModel/GeoAlchemy2 stub gaps (`Model.col.in_()`/`.is_not()` not
  recognized as column-expression methods, `id: int | None` pre-insert
  typing on always-persisted rows, `WKTElement` vs. the `str | None` a
  Geometry column is annotated as), concentrated entirely in
  `app/api/routes/`, `app/models/`, and `app/db/seed.py` — `app/services/`
  (PRD's "touches no database session" layer) is clean apart from the two
  real ones. Demoted those five specific rule categories to `warning` (still
  visible in CI output, doesn't fail the build) rather than either hiding
  them entirely or hand-annotating ~90 individual call sites for a stub gap,
  not a bug; see the comment above `[tool.pyright]` for the full reasoning.
- [x] **CI — dependency scanning** (`pip-audit` for `apps/api` and
  `tools/garmin_import`, `pnpm audit` for `apps/web`, blocking where clean).
  `pip-audit` found nothing in `apps/api`. It found something real in
  `tools/garmin_import`: `garminconnect==0.3.2` carries PYSEC-2026-3467
  (CWE-732, high severity) — versions ≤0.3.4 wrote the OAuth token store
  with whatever the process umask allowed, so `.garmin_tokens/` could end up
  world-readable (containing a live Garmin refresh token) on a shared host.
  Bumped to `0.3.5` and re-verified against the newly-installed source
  before trusting it: every method `garmin_client.py` calls has the
  identical signature it had at 0.3.2, and the full 35-test mocked suite
  still passes. `pnpm audit` found 7 findings in `apps/web`; 5 were fixable
  with `pnpm.overrides` on direct dependencies (`postcss`, `sharp`, both
  pinned inside `next`'s own tree) — verified safe with a real `pnpm build`
  and the full test suite after overriding, not just installed and hoped.
  The remaining 2 are `image-size`, six `deck.gl`→`loaders.gl` levels deep
  in a glTF texture-loading chain this app never exercises (2D map overlays
  only), with no patched version published upstream at all yet — kept as a
  real, non-blocking (`continue-on-error`) CI step so a *new* finding still
  shows up, rather than dropped or force-overridden into an untested code
  path.
- [x] **CI — secret scanning, partially.** CodeQL (`.github/workflows/
  codeql.yml`, Python + JavaScript/TypeScript, push/PR/weekly) is wired up —
  it also catches a meaningfully overlapping set of injection/XSS-shaped
  bugs, not just credentials. GitHub's actual *secret-scanning* feature
  (detecting a committed API key/token) is a repository **setting**
  (Settings → Security → Secret scanning), not something expressible in a
  commit — flagged here rather than silently left off, since no admin
  access to toggle it exists from this environment.
- [x] **CI — coverage reporting**: `pytest --cov` (backend, `pytest-cov`) and
  `vitest run --coverage` (frontend, `@vitest/coverage-v8`), both uploaded as
  build artifacts (no external service/token available to verify, so no
  Codecov-style integration — same "don't quietly present unverified
  integrations as working" rule this repo already follows for Garmin/Mapbox).
  Backend baseline: 89% line coverage (`app/db/seed.py` is the one large gap,
  at 0% — it's a standalone script run via `make seed`, not exercised by the
  suite, which is expected).
- [x] **CI — Dependabot** (`.github/dependabot.yml`): weekly, covering every
  ecosystem in the repo — `uv` (`apps/api`), `npm` (`apps/web`), `pip`
  (`tools/garmin_import`), `docker` (both Dockerfiles), and `github-actions`
  itself. `tools/garmin_import`'s entry calls out that an update PR there
  needs the same re-verify-against-installed-source treatment the
  `garminconnect` bump above got, not an automatic merge.
- [x] **CI — build the prod Docker targets** (`docker` job in `ci.yml`,
  `docker/build-push-action@v6`, matrix over `apps/api`/`apps/web`, both
  `target: prod`). **Unverified in this environment**: a real Docker daemon
  is available here (unlike Phase 9, where none was), but this sandbox's
  network policy blocks the registry blob-fetch CDNs for both Docker Hub and
  ghcr.io (`docker pull python:3.12-slim` and `ghcr.io/astral-sh/uv:latest`
  both fail the same way postgis's image pull did in Phase 9) — so neither
  Dockerfile's base image can actually be pulled from here. The workflow
  itself is standard, correctly-configured `docker/build-push-action` usage;
  it just hasn't had a real build run against it, the same verification
  boundary as Mapbox/Garmin/Overpass elsewhere in this repo.
- [x] **Delivered early, out of phase order (Phase 9).** A root `CLAUDE.md`
  recording the conventions this repo already follows — raw-column selects to
  avoid geoalchemy2's non-serializable `WKBElement`, the `geometry.py` ↔
  `projection.ts` mirror, the deliberate `VirtualRound`/`Round` split, the
  alembic autogenerate caveats, Phase 9's test fixtures, the PRD-section-
  reference comment style, and the documented-verification-limit convention for
  integrations that can't be exercised here. It also states plainly that no
  endpoint authenticates anyone, so the gap gets read as scheduled work
  (Phase 10) rather than as a pattern to copy.

**Gaps carried forward:**
- ~~**The Docker build CI job is unverified**, per above — no registry access
  in this environment to actually pull a base image and run it for real.~~
  **Verified, the hard way.** The first real GitHub Actions run against this
  job (PR #21) failed outright — not the registry-access limit predicted
  above, but `docker/build-push-action@v6`'s `cache-to: type=gha` silently
  requiring the `docker-container` buildx driver, which this job never
  switched to. Fixed by adding a `docker/setup-buildx-action@v3` step; see
  `docs/KNOWN_ISSUES.md`.
- **GitHub's native secret-scanning feature isn't enabled** — it's a repo
  setting outside this environment's reach, not a code gap. CodeQL covers a
  different, overlapping class of finding in the meantime.
- **pyright's 99 demoted warnings are a real, if bounded, blind spot.**
  Resolving them for real means changing how every table model annotates its
  geometry/PK columns — a bigger, separately-justified change than "add a CI
  type check," and risky to do without a live Postgres+PostGIS round-trip to
  verify against every time (available in this environment, per below, but
  not exercised for this).
- **`pnpm audit`'s 2 remaining findings have no upstream fix** (`image-size`
  DoS parsers, unreachable from this app's actual usage) — nothing to do
  here until `loaders.gl`/`texture-compressor` ships one.
- **Nothing is cached in the request-id/logging path** (matches Phase 11's
  same note about analytics) — nothing here needed it yet.

**Acceptance criteria:** a deliberately-thrown error (verified with a real
endpoint whose DB dependency is forced to raise, not a handcrafted
Request/exc pair) produces a `{detail, request_id}` body with no traceback in
it, and the same request id in both the response header and a structured log
line with a full traceback attached. 341 backend tests (6 new:
`test_observability.py`, plus `/health`+`/ready` split coverage in
`test_health.py`), ruff clean, `pyright` clean (0 errors), `pip-audit` clean.
301 frontend tests, eslint clean, production build succeeds with the
`postcss`/`sharp` overrides in place. Migrations verified to apply cleanly
against a real Postgres 16 + PostGIS instance — this environment's Docker
registry access is blocked (see the Docker build gap above), but
`postgresql-16-postgis-3` installs cleanly via `apt`, which isn't, so a real
local Postgres stood in for `docker compose`'s where Phase 9/11 had neither.

## Phase 13 — Frontend Data Layer & Error Boundaries (done, with noted gaps)

Goal: `use-dashboard-data.ts`, `use-practice-data.ts`, and
`use-virtual-rounds.ts` each hand-rolled loading/error/cancel/refresh state. The
implementations were careful — the `cancelled` flag handling was correct — but
the pattern was written three times, and there was no caching, dedupe, retry,
or revalidation, so every navigation refetched from scratch.

- [x] **Adopted SWR, collapsed the three hooks onto it.** Chose SWR over
  TanStack Query for its smaller surface — this app has no mutations
  sophisticated enough to need TanStack's cache-write helpers, just
  read-and-refetch, which is SWR's whole design center. All three hooks
  (`use-dashboard-data.ts`, `use-practice-data.ts`, `use-virtual-rounds.ts`)
  keep their exact external `{ state, refresh }` shape — every page that
  consumes them (`page.tsx`, `practice/page.tsx`, `virtual-bag/page.tsx`)
  needed no change beyond the signature swap below, and neither did the two
  page tests that mock the hook module directly rather than exercising SWR
  for real.
  - **Real fix, not just a swap: cache keys are scoped by user id, not a
    `signedIn` boolean.** All three hooks used to take `signedIn: boolean`;
    since `current-user.tsx`'s sign-in/sign-out is a client-side state
    change with no forced page reload, a `useSWR("dashboard-round", ...)`
    keyed only by a fixed string would have let SWR's cache serve player
    A's cached round to player B for a moment after A signs out and B signs
    in in the same tab, before revalidating — exactly the class of bug
    Phase 8/10 exist to close. Hooks now take `userId: number | null`
    (`useDashboardData(user?.id ?? null)` etc.) and key on
    `["dashboard-round", userId]`; `null` both disables the fetch (SWR's
    key-is-null convention) and reports `idle`, same as before.
  - **Found and fixed a real test-isolation bug along the way, in
    `page.test.tsx`.** SWR's default cache is a module-level singleton
    shared across every test in a file. Every test in that file signs in as
    the same `testUser.id`, so all eight tests shared one cache entry — and
    since the second test (`shows a loading state before data arrives`)
    deliberately mocks a fetch that never resolves, every test after it
    inherited that permanently-pending entry and hung until timeout. Fixed
    by wrapping each render in a fresh `<SWRConfig value={{ provider: () =>
    new Map() }}>` (SWR's own documented pattern for exactly this), not by
    changing the hooks — this was purely a test-isolation gap the migration
    exposed.
- [x] **Added `error.tsx`, `loading.tsx`, `not-found.tsx`** at the app root
  (`src/app/`) — styled consistently with the rest of the app (`Card`,
  `Overline`, `NavBar`), not left as Next's unstyled defaults.
  `error.tsx` logs the caught error and offers "Try again" (calls Next's
  `reset()`) and a full, non-client-side navigation back to the dashboard —
  deliberately a plain `<a>`, not `<Link>`, so whatever broke doesn't ride
  along through client-side routing on the way out. Verified in a real
  browser (Chromium via Playwright): a real 404 on an unmatched route
  renders the new styled page, not Next's default.
- [x] **Dashboard's request waterfall.** Already resolved by Phase 11's
  `?limit=1` server-side query, not new work here — confirmed by reading
  `use-dashboard-data.ts` before touching it: `getRounds({ limit: 1 })` is
  the only round fetch, no client-side sort over the full list survives.
  What's left (`getRounds` → `getRoundAnalytics`) is an inherent dependency
  — the second call needs the first's result — not a waterfall a data
  library removes; SWR doesn't change that shape, just how the two-step
  fetch's loading/error/cache state is managed.

**Gaps carried forward:**
- **No global `SWRConfig`.** Every hook relies on SWR's built-in defaults
  (revalidate-on-focus, etc.), which are reasonable for this app's size; a
  provider would only be worth adding for a deliberate override, and there
  isn't one yet.
- **`loading.tsx`'s actual trigger condition is narrow.** It's Next's
  route-segment-transition fallback, not a stand-in for what each page's own
  "Loading round…"/"Loading practice data…" text already covers for the
  client-side SWR fetch — those aren't redundant with it, they cover
  different moments, but it means `loading.tsx` itself is rarely seen in
  this app's current all-client-components shape. Kept anyway: cheap, and
  it's exactly what the App Router convention expects to find.
- **No dedicated error boundary for the map components specifically** —
  Phase 4 already gave `HoleReplayMap`/`CourseGeometryMap` their own
  internal fallback-to-SVG recovery, so today's root `error.tsx` is a
  second, unreached safety net for them rather than the primary one. Still
  the right thing to have for everything else.
- **The 401 interceptor Phase 10 assigned to this phase did not get built.**
  Phase 10's gap list says, in as many words, "a 401 interceptor in
  `apiFetch` belongs with Phase 13's data-layer work" — and this phase
  rewrote the data layer without doing it. `apiFetch` still throws a bare
  `ApiError(401)` (`src/lib/api.ts`), so a session that expires mid-visit
  surfaces as whatever error text the page happens to render rather than
  bouncing to `/login`. Not a regression — it's exactly as broken as it was
  before Phase 13 — but it was in scope and was missed, so it's carried
  into Phase 15 (Password Reset & Account Recovery) rather than quietly
  re-filed. SWR's `onError` config is now the obvious place for it, which
  the pre-SWR code didn't have.

**Acceptance criteria:** no bespoke fetch-state machines left in `src/lib` —
`use-dashboard-data.ts`, `use-practice-data.ts`, and `use-virtual-rounds.ts`
are all thin wrappers around `useSWR` now. 306 frontend tests (5 new:
`error.test.tsx`, `not-found.test.tsx`, `loading.test.tsx`), eslint clean,
`tsc`/production build clean (`postcss`/`sharp` overrides from Phase 12 still
in place). A forced throw renders the new `error.tsx` rather than Next's
default (unit-tested directly with a thrown `Error` and a mocked `reset`); an
unmatched route renders the new `not-found.tsx`, verified in a real browser
(Chromium via Playwright) against the dev server, not just asserted in
jsdom. 341 backend tests, unaffected — this phase touched `apps/web` only.

---

# Part III — Completion (Phases 14-17)

Parts I and II each ended with an explicit, honest list of what didn't get
built. Part III is those lists, promoted into scheduled work. Nothing here
comes from a new idea — every item is a gap some earlier phase wrote down
and deferred, which is why each one below names the phase it's inherited
from.

**This ordering was revised after a four-perspective review** (a PM read, an
implementation read, a design read, and an end-user read, run as independent
passes against the first draft of this Part). All four converged on the same
finding from different angles: the first draft led with authentication
hardening — password reset, server-side session revocation, rate limiting,
account merge — and buried the one phase with direct, visible product value
(real short-siding, PRD's own marquee diagnostic) third. The PM read called
this a 1:3 ratio of invisible engineering hygiene to user value in a
four-phase plan; the end-user read, independently, said to ship the
short-siding work "first, alone if you have to." The review also caught a
factual error in the original Phase 14 (server-side sessions do not add "a
database read where today there is none" — `get_current_user` already reads
the database every request) and confirmed account merge has no evidence of
actual demand, only a hypothetical inherited from Phase 8's now-deleted
picker UI. The plan below reflects that: short-siding goes first, and merge
plus the heavier abuse-resistance items move to the Backlog to wait for an
actual signal rather than ship speculatively.

Phases 15, 16 and 17 remain independent of each other and can be reordered
freely.

## Phase 14 — Per-Round Pin Positions & True Short-Siding (done, with noted gaps)

Goal: the oldest unpaid debt in this document, and — per the first review —
the only phase in this Part with direct, visible product value, which is
why it leads. Phase 2 shipped short-siding as "a distance/lie-based proxy,
not true short-siding" and said so. Phase 3 repeated it. Phase 4 built
`is_within_ellipse` — the exact primitive a real "sucker pin" check needs —
and left it wired to nothing, because `Hole.green_center` is a static point,
not where the pin was cut that day. Three phases have now deferred the same
schema addition. This is the one that makes the PRD's marquee diagnostic
honest.

**A second panel pass, run specifically as this phase's pre-implementation
gate, sent the previous version of this entry back.** It wasn't a priority
question this time — that was already settled — it was readiness. The
developer and design reads independently caught that the plan was factually
wrong about the codebase it was describing (the audit wizard has no map or
location field at all; "reuse the existing interaction" only holds for
manual entry), that "true geometric short-siding" named its inputs but never
specified an actual rule, and that the new table was missing the same
uniqueness/cascade discipline this session already added to `Shot`. Three
readers independently hit the same finding from different angles — PM, design,
and the end-user read all separately flagged that a fallback label appearing
on ~100% of existing rounds at launch needed a real decision, not inherited
copy. This revision makes those decisions explicitly rather than leaving them
for whoever implements it to guess:

- **Pin capture ships in manual entry only.** The audit wizard
  (`audit-wizard/add-shot-form.tsx`) has no map or location UI today —
  contrary to what the previous draft assumed, there's nothing there to
  relabel. Adding one is real, separate scope; it's not in this phase (see
  below).
- **Placing a pin is optional, never required.** No hole is blocked or
  nagged for missing one; an unmarked hole just gets the fallback verdict.
- **The fallback isn't styled as a warning.** `ShortSidedBanner`
  (`components/hole-replay/short-sided-banner.tsx`) returns `null` on most
  holes and uses `--status-critical` (the same rust as `--destructive`) for
  an actual disaster flag — wrong precedent for routine data provenance.
  The pin-source line lives outside that banner, in `text-muted-foreground`,
  and reads "Based on green center — no pin recorded" rather than
  "Estimated," which two independent reads flagged as landing closer to an
  apology than a fact on a field that'll be true for nearly every round at
  launch.
- **Audit-wizard pin capture, short-siding trends over time, and live
  in-round pin capture at the moment of play (the end-user read's
  preference — see the new Backlog item) are explicitly not in this
  phase.**

- [x] **Schema: a per-round, per-hole pin position.** `RoundHolePin`
  (`app/models/round_hole_pin.py`), not a column on `Hole` — that table is
  shared reference geometry across every user's rounds, and a pin is a
  property of one round on one day, the same reasoning that keeps
  `VirtualRound` separate from `Round`. `UniqueConstraint("round_id",
  "hole_id", name="uq_pin_round_hole")` (one pin per hole per round — a
  second placement replaces it, the way a resubmitted shot does, not a
  second row), `round_id` cascades on delete, `hole_id` does not (`Hole` is
  shared reference geometry, not this row's to own — same comment
  `Shot.hole_id` already carries). Migration `cfdf38640868` verified up,
  down and up against a real local Postgres 16 + PostGIS instance
  (`postgresql-16-postgis-3` via `apt`, this sandbox's Docker registry
  still being blocked); `\d round_hole_pin` confirms a single GIST index
  (autogenerate's redundant `op.create_index` removed, per this repo's own
  documented caveat) and the two FK cascade behaviors. The unique
  constraint was exercised directly at the SQL level, not just through the
  API: a second `INSERT` for the same `(round_id, hole_id)` inside the same
  transaction raises `duplicate key value violates unique constraint
  "uq_pin_round_hole"`, as intended.
- [x] **A real, specified short-siding rule** in `app/services/approach.py`.
  Given the pin, the green boundary polygon, and the miss point: take the
  line through the pin along the shot's approach bearing, measure how much
  green lies beyond the pin on the miss's side of that line
  (`green_extent_beyond_point()`, `app/services/geometry.py`) versus the
  opposite side, and call it short-sided when the miss's side has
  substantially less green to work with — the golf-instruction definition,
  not a fixed distance. `SHORT_SIDE_GREEN_RATIO = 0.5` is this
  implementation's own calibration, named as such in the module docstring
  (same caveat as `SCRATCH_CURVES` and `EXPECTED_SMASH_FACTOR_BY_IRON`), not
  a licensed number.
- [x] **A third state the previous draft's two-value `pin_source` missed:
  pin recorded, but no green boundary to measure against.** The response
  reports two independent booleans, `has_pin` and `has_green_boundary`
  (`GET /rounds/{id}/analytics` and `GET /rounds/{id}/holes/{n}/replay`),
  rather than a single enum trying to cover three states in two values; the
  geometric rule only runs when both are true, and the existing
  distance/lie proxy is the fallback whenever either is missing.
- [x] **Wired `is_within_ellipse` to real pins — client-side, not on the
  backend.** The ellipse itself already comes from `GET /bag`, and
  `rounds/[id]/page.tsx` already stitches hole replay + Smart Bag together
  in the browser to anchor it (`ellipseAnchorYards`); adding a second
  backend round-trip just to re-fetch the same bag data would have
  duplicated that wiring, not simplified it. `is_within_ellipse` is mirrored
  in `lib/hole-replay/dispersion.ts` (same math, same test cases ported
  from `test_dispersion.py`) — a second math mirror pair alongside
  `geometry.py` ↔ `projection.ts`, flagged here so it doesn't drift
  unnoticed the way that pair's own warning exists to prevent. A new
  `SuckerPinAlert` (`--status-warning`, not the short-sided banner's
  `--status-critical` — this is a before-the-shot risk flag, not a report of
  a bad outcome) renders when today's pin falls inside the approach club's
  dispersion ellipse.
- [x] **Aim line targets the pin, not the green center**, in both UI render
  sites: `HoleReplaySvg` (falls back to `green_center` when no pin is
  recorded, and now renders a distinct flag marker at the pin) and
  `HoleReplayMap`'s Mapbox layer (a third marker color, `#c9a227`, alongside
  the existing tee/green/shot markers).
- [x] **A pin-placement mode on manual entry's existing map.**
  `HoleShotEntry` gained a `mode: "shot" | "pin"` toggle (a labeled "Set
  today's pin" control) and an `onSetPin` prop, threaded as real state
  rather than a second meaning silently overloaded onto the existing
  `onPick`. **Deviates from the original plan on one point, deliberately:**
  the plan called for holding the pin in the same client-side draft as the
  hole's shots and submitting it with them, reasoning that "no pin endpoint
  exists yet." That premise stopped being true partway through this phase —
  `POST /rounds/{id}/pins/bulk` was built for the API item above — so a pin
  placement now saves immediately, the same idempotent
  existing-pin-gets-replaced pattern `POST /shots/bulk` already established.
  This is simpler than threading a second draft type through
  `use-audit-draft`, and arguably safer (a pin persists the moment it's
  placed rather than only if the player finishes and submits the whole
  round) — recorded here since the plan's stated reasoning for the
  original choice no longer held once the endpoint existed.
- [x] **Report `has_pin`/`has_green_boundary` in the analytics response, and
  render the muted provenance line described above** whenever either is
  false. `PinProvenanceNote` (`text-muted-foreground`, not the banner's
  `--status-critical`) renders on the hole replay page reading "Based on
  green center — no pin recorded" (no pin) or "Based on distance — no green
  boundary recorded" (pin but no boundary — the third state above), and
  disappears once both are true.

**Not in this phase, on purpose:** pin capture inside the audit wizard (needs
a map/location UI added there first, which doesn't exist); short-siding rate
aggregated as a trend over time (a natural follow-on, not this phase's job);
live, in-round pin capture at the moment of play (see the Backlog item).

**Acceptance criteria:** a hand-computed short-siding case per quadrant (pin
tucked left with a miss left, same pin with a miss right, etc.) computed
against a real pin and asserted exactly — `test_approach.py`'s
`TestGeometricRule` — *and*, learning from Phase 4's own ellipse-anchoring
bug, which passed every synthetic unit case and was only caught by a real
visual pass against real data: the new rule was also run against the seeded
demo round's actual shots, not just hand-built cases. This caught something
real: hole 7's scripted narrative ("heel/push-slice into a short-sided
bunker," the PRD §8 mockup example verbatim) actually computes as
`safe_leave` under the pre-Phase-14 proxy — the shot ends 12y from the pin,
past the 10y `SHORT_SIDE_PROXIMITY_YARDS` threshold, so the demo data's own
narrative comment has been slightly wrong since Phase 2. Placing a real pin
on the miss's side of that green via `POST /pins/bulk` and re-fetching the
hole replay flipped the verdict to `short_sided`, as the golf actually
calls for; placing the same pin on the opposite side correctly gave
`safe_leave`. (The proxy's threshold isn't being changed — it's a
documented, unvalidated calibration and out of this phase's scope — but the
mismatch is worth knowing about.) The existing proxy tests still pass, now
covering both fallback conditions (no pin, and pin-but-no-boundary). A test
that every existing round (which has neither `has_pin` nor, for some holes,
`has_green_boundary`) round-trips through the correct fallback and renders
the muted provenance line, styled with `text-muted-foreground` and not the
banner's `--status-critical`, verified both in `vitest` and in a real
browser screenshot. Migration verified up, down and up against a real
PostGIS instance, including the unique constraint rejecting a second pin
for the same round/hole at the raw SQL level. A real-browser Playwright
pass (Chromium, this sandbox's pre-installed browser) logged into the
seeded demo account, switched manual entry to pin mode, clicked the hole 7
map, and confirmed both the pin marker appeared and the aim line's SVG
endpoint moved to it; a second pass on the round detail page confirmed the
provenance note appears/disappears correctly across holes with and without
a recorded pin. **The Mapbox-layer half of that pass is unverified in this
sandbox** — no `NEXT_PUBLIC_MAPBOX_TOKEN` is configured here, the same
standing limit `garmin_oauth.py` and `osm_courses.py` already document;
`HoleReplayMap` falls back to the SVG schematic whenever no token is
present, which is what the browser pass above actually exercised. 369
backend tests (up from 362: `TestGreenExtentBeyondPoint`,
`TestGeometricRule`, `TestCreatePinsBulk`, and the hole-replay/analytics
pin-provenance cases), ruff clean, pyright clean (0 errors, 118 warnings —
up from 101, all in the same pre-existing demoted categories, no new
category introduced). 332 frontend tests (up from 310), `tsc --noEmit`
clean, eslint clean.

**Gaps carried forward:**
- **The Mapbox-layer aim line/pin marker is implemented but unverified in a
  real browser**, per the standing Mapbox token limit above — only its
  props/marker-call wiring is covered by `hole-replay-map.test.tsx`'s mocked
  `mapbox-gl`.
- **Hole 7's seed narrative comment is now slightly inaccurate** (says
  "short-sided," proxy-classifies as `safe_leave` without a pin) — a
  one-line comment fix, not a behavior bug, left for whoever next touches
  `app/db/seed.py` rather than bundled into this phase's diff.
- **`SHORT_SIDE_GREEN_RATIO = 0.5` is still unvalidated calibration**, as
  documented in `approach.py` — the acceptance-criteria pass checked that it
  produces sensible, side-correct verdicts on real geometry, not that 0.5
  specifically is the right cutoff.
- Audit-wizard pin capture, short-siding trend-over-time, and live in-round
  pin capture remain explicitly out of scope — see Backlog.

## Phase 15 — Password Reset & Account Recovery (done)

Goal: the trimmed remainder of what was originally a five-item auth phase.
Phase 10 shipped real authentication and listed five things it deliberately
didn't do; of those, password reset is the one with a real, common,
non-speculative trigger (anyone can forget a password) and a small, bounded
blast radius. The review split it out from server-side session revocation,
rate limiting, and account merge — each real, but each wanting either
infrastructure this phase doesn't need (a shared counter/cache store) or an
actual signal of demand this app doesn't have yet. See the Backlog for where
those three went and why.

- [x] **An email-sending path** (`app/services/email.py`). Development writes
  the message to the log (no SMTP server in the dev sandbox, and the repo's
  convention is to make the unverifiable boundary obvious rather than
  pretend); production takes SMTP over stdlib `smtplib` using new `SMTP_*`
  settings (`app/core/config.py`, `.env.example`). Follows the
  `garmin_oauth.py` / `osm_courses.py` convention: standards-conformant code,
  unit-tested against a mocked `smtplib.SMTP` (dev no-op path, TLS/login
  branches, and both connection- and send-time failures raising `EmailError`
  — `tests/test_email.py`), verification limit stated plainly in the module
  docstring.
- [x] **Password reset** (Phase 10 gap: "a forgotten password currently means
  a new account"). Request → single-use signed token emailed to the account
  → set a new password, at `POST /auth/forgot-password` /
  `POST /auth/reset-password` (`app/api/routes/auth.py`). Built on
  `app/core/signing.py` as planned — a third caller, not a third
  implementation — but "single-use" needed one more piece than the plan
  named: with no server-side token store, a reset token is bound to a
  fingerprint of the account's *current* password hash
  (`_password_fingerprint` in `app/core/security.py`); redeeming it changes
  the hash, so the same token fails a second time on its own, no revocation
  list required. `password_hash IS NULL` is a real, fingerprintable input
  (hashes to `"no-password-set"`), not a special case, which is what lets a
  pre-Phase-10 account through the same path with no branch for it anywhere.
  `POST /auth/forgot-password` returns the identical `{"ok": true}` whether
  or not the email has an account — same reasoning as `POST /auth/login`'s
  deliberately identical wrong-password/no-account answer. UI: two named
  pages, `/forgot-password` and `/reset-password/[token]`, in the existing
  `/login` visual register — no alarm styling, dry factual copy ("Check your
  email for a reset link"), matching `docs/STYLE_GUIDE.md`'s ban on
  exclamation points and apology theater. `/login` gained a "Forgot your
  password?" link in sign-in mode.
- [x] **The 401 interceptor Phase 13 missed** (Phase 10 gap, mis-assigned to
  Phase 13, not built there — see Phase 13's gap list). `apiFetch` now calls
  a registered handler on any 401 outside a small exempt list (`/auth/me`,
  `/auth/login`, `/auth/register`, and the two reset endpoints above — the
  flows where a 401 is the ordinary, expected answer, not a session gone bad
  mid-use). `CurrentUserProvider` registers the handler and gates it on its
  own current `user` state via a ref, so an anonymous visitor's routine 401s
  don't get treated as an expired session — only a tab that actually
  thought someone was signed in gets bounced, to `/login?expired=1`, which
  renders the copy decision this item called for: a plain "Signed out — sign
  in again.", not a bare silent redirect and not alarm language either way.
- [x] **Pre-Phase-10 accounts** (Phase 10 gap: rows with a null
  `password_hash` can't log in and need a password set out of band). Closed
  by the reset-token fingerprint scheme above; `TestForgotPassword` and
  `TestResetPassword` in `tests/test_auth_routes.py` each have a dedicated
  test constructing a `password_hash=None` account and taking it through the
  real HTTP path end to end, not just asserting against the token internals.

**Acceptance criteria, verified:** a real script (not just the test suite)
called `POST /auth/forgot-password` against the running dev stack for the
seeded demo account, read the token out of the logged dev-mode email, drove
`/reset-password/[token]` in an actual browser (Chromium, this sandbox's
pre-installed one) to a real new password, confirmed the dashboard rendered
signed-in afterward, then confirmed via `/auth/login` that the old password
now 401s and the new one 200s — and the demo account's documented password
was reset back to its seeded value afterward so `make seed`'s printed
credentials stay correct for the next person. `tests/test_access_control.py`
needed no logic changes, only its `PUBLIC_ENDPOINTS` allowlist grew by the
two new routes, each with a written reason, matching the plan. A dedicated
interceptor test confirms a stale-session 401 clears client state and
redirects with `?expired=1` rather than rendering page-level error text, and
a sibling test confirms an anonymous visitor's 401 does neither. 389 backend
tests (up from 370: `TestForgotPassword`, `TestResetPassword`, and
`tests/test_email.py`), ruff clean, pyright clean (0 errors; new warnings are
all the same pre-existing nullable-id pattern Phase 17 owns, no new
category). 364 frontend tests (up from 337: the interceptor in
`api.test.ts`/`current-user.test.tsx`, the two new pages, and `/login`'s
additions), `tsc --noEmit` clean, eslint clean.

**Gaps carried forward:**
- **Rate limiting a reset request is still absent** — same Phase 10/11 gap
  the Backlog already tracks for login/register, now with a third public
  endpoint sharing it. Not new scope for this phase; noted so it isn't
  rediscovered as if it were.
- **The reset email is plain text**, matching this app's other outbound
  surface (none, until now) rather than introducing an HTML-email templating
  dependency for one transactional message.
- **`smtplib` over TLS/auth is unit-tested against a mock, not a real SMTP
  server** — the same unverifiable-boundary limit `garmin_oauth.py` and
  `osm_courses.py` already carry, stated in `email.py`'s own docstring
  rather than pretended away.

## Phase 16 — Aggregate Query Push-Down & Export Bounding (done)

Goal: Phase 11 ended with two "not worth it until someone has that much
data" notes. The review cut the third item this phase originally carried —
caching `GET /rounds/{id}/analytics` — because the numbers don't support it:
Phase 11 already got that endpoint to 5.7ms, and a cache whose key can miss
one of three dependencies (shots, course, handicap index) and silently serve
a wrong Strokes Gained number is a bad trade for shaving single-digit
milliseconds off an endpoint that isn't slow. Revisit only if profiling ever
shows otherwise — see the Backlog.

- [x] **Push aggregation into SQL** for `GET /bag` and both practice
  endpoints (Phase 11 gap: "now bound by Python-side aggregation over all of
  a user's shots, ~200ms at 21,600"). The real obstacle named in that same
  note — Smart Bag's IQR outlier rejection is a two-pass operation — moved
  into SQL as three CTEs in `club_carry_dispersion_sql`
  (`app/api/routes/_shot_queries.py`): quartiles via `percentile_cont`,
  Tukey fences from those quartiles (skipped, via a `NULL` bound, for clubs
  under `MIN_SAMPLES_FOR_IQR`), then a `FILTER`-qualified aggregate for the
  survivors. `percentile_cont`'s ordered-set interpolation turned out to
  match NumPy's default `percentile` method to the float on every sample
  tried, both a synthetic dataset and every club in the seeded demo round,
  verified directly against a live Postgres instance before writing any
  application code — but `avg()`/`percentile_cont()` and Python's
  `statistics.fmean`/`pstdev` aren't guaranteed the same summation order in
  general, so the test suite compares to a `1e-9` tolerance rather than
  leaning on that empirical match holding for every possible input (see the
  acceptance-criteria note below). Lateral dispersion deliberately stayed in
  Python: it's already the smaller query (only located shots), and pushing
  its flat-earth trig into
  SQL would risk a third copy of `app/services/geometry.py`'s
  `YARDS_PER_DEGREE_LAT` alongside the existing TypeScript mirror — not a
  trade this phase's own named obstacle called for. `GET /bag` no longer
  calls `fetch_on_course_shots` at all; `GET /practice/delivery` only calls
  the new SQL function; `GET /practice/combines` still calls
  `fetch_on_course_shots` for its Strokes-Gained bracket and putting
  evaluation, unrelated to the IQR obstacle this phase targeted.
- [x] **Bound `GET /me/export`** (Phase 11 gap: "unchanged and unbounded — it
  returns every row the user owns, by definition"). Rewritten as a
  `StreamingResponse` (`app/api/routes/privacy.py`) that fetches one round's
  shots (or one practice session's shots) at a time and yields each round/
  session object as soon as it's serialized, rather than grouping every shot
  the user has ever recorded into one dict before any of it is sent. Peak
  memory is now O(one round's shots) instead of O(every shot the user
  owns). This trades one big query for one small query per round/session —
  explicitly sanctioned by this item's own framing below — rather than a
  true DB-level server-side cursor, which would have needed to interact with
  Phase 9's savepoint-based transactional test isolation in ways this phase
  didn't need to risk for a "not about latency" requirement.
- [x] **Re-run `scripts/benchmark.py`** and record real before/after numbers
  in this entry, the way Phase 11's table does.

| endpoint | before | after | |
|---|---|---|---|
| `GET /bag` | 244.0 | 43.2 | **5.6x** |
| `GET /practice/delivery` | 241.0 | 43.7 | **5.5x** |
| `GET /practice/combines` | 315.1 | 292.6 | still walks every shot for its SG bracket + putting — unrelated to this phase's IQR push-down |
| `GET /me/export` | 462.0 | 708.0 | **slower, by design** — 300 small queries instead of 2 big ones; see gaps below |

(Unlisted endpoints — `GET /rounds`, `GET /rounds?limit=1`,
`GET /rounds/{id}/analytics`, `GET /rounds/{id}/holes` — are untouched by
this phase and unchanged within noise of Phase 11's numbers.)

**Acceptance criteria, verified:** `tests/test_shot_queries.py` compares
`club_carry_dispersion_sql`'s output directly against
`app/services/smart_bag.py`'s `compute_dispersion` on identical samples,
including the six-sample `[248, 250, 252, 251, 249, 400]` set
`tests/test_bag_route.py`'s planted-outlier test already relies on —
which samples get kept/excluded and the resulting count match exactly;
mean/median/stdev are compared to `1e-9` rather than `==`, since Postgres's
and Python's summation order aren't guaranteed identical in general even
though they land on the same float for every case tried here. A
below-`MIN_SAMPLES_FOR_IQR` case, the exact-boundary case (`n ==
MIN_SAMPLES_FOR_IQR` with a real outlier present), independent multi-club
aggregation, cross-user scoping, and the empty-string/putter/non-positive-
carry exclusions all get their own test. `tests/test_privacy_routes.py`
gained two tests seeding two rounds (and two practice sessions) with
different clubs each, to catch a round/session mix-up in the new
per-entity streaming query — a real risk this refactor introduced that the
single-query original couldn't have had. 397 backend tests (up from 389),
ruff clean. Verified live against the running dev stack (not just
`scripts/benchmark.py`'s bench database): `GET /bag`,
`GET /practice/delivery`, `GET /practice/combines`, and `GET /me/export`
all called against the seeded demo account and inspected by hand, plus a
Chromium pass over `/rounds/{id}` (which calls `getSmartBag()` for its
dispersion ellipse) and `/practice` confirming no visual or console
regression. No frontend files changed this phase — the response shapes
are identical, only how they're computed and delivered.

**Five-perspective panel, run before marking this phase done:** PM,
developer, QA, and end-user reads (no UI changed this phase, so no
designer read). PM and end-user reads both approved the export-latency
trade as-is — the export is a low-frequency GDPR/CCPA action, not a
hot-path screen, and going from ~460ms to ~710ms doesn't register against
either the PRD's success metrics or the DATA_PRIVACY.md commitment being
about completeness, not speed. The QA and developer reads each found real
issues, since fixed: an `empty club == ""` divergence where the SQL only
filtered `IS NOT NULL` but `shot_carry_distance`'s Python original also
excluded the empty string, which would have silently surfaced a bogus
`""` club group; an untested `n == MIN_SAMPLES_FOR_IQR` boundary case
(added above); dead code (`compute_club_gapping` and `shot_carry_distance`
had zero production callers left once `bag.py`/`practice.py` were cut over
— deleted, along with `build_club_gapping` being a near-duplicate of
`compute_club_gapping` it should have delegated to instead — replaced with
a `TestBuildClubGapping` unit test covering the function actually in use
now); and the mean/stdev-equality over-claim this section and the
`percentile_cont` item above have since been reworded to match. Left as a
named, accepted gap rather than fixed: a mid-stream export failure now
serves a truncated 200 instead of a clean 500 (see below).

**Gaps carried forward:**
- **`GET /me/export` got slower, not just unbounded-in-memory-but-otherwise-
  fine.** 300 rounds' worth of one-query-per-round adds real round-trip
  overhead the original's two big queries didn't pay — 708ms vs. 462ms at
  this benchmark's volume, all against a local Postgres with no network
  latency to speak of. A real deployment with non-trivial DB round-trip time
  would feel this more, not less. This item's own acceptance framing ("not
  holding an entire account in memory rather than about latency") sanctions
  the trade, but a future pass could close both gaps at once with a single
  ordered shots query merge-joined against the rounds iterator instead of
  one query per round — deferred here because it requires both streams
  consistently ordered (round id rather than the current `played_at`), which
  touches more than this phase's stated scope.
- **A mid-stream failure on `GET /me/export` now serves a truncated 200
  instead of a clean 500.** `StreamingResponse` commits to the 200 status
  and starts sending bytes before every round has been fetched, so a DB
  error partway through (round 150 of 300, say) produces an incomplete JSON
  body under a success status rather than the old buffered version's
  all-or-nothing response. Inherent to streaming and a reasonable cost for
  the memory bound this item exists to deliver, but worth naming plainly for
  a GDPR/CCPA access endpoint rather than leaving it implicit.
- **`GET /practice/combines` only picked up a small win** (315.1ms →
  292.6ms) because its dominant cost — `fetch_on_course_shots` for the
  Strokes-Gained bracket and `evaluate_putting` — was never the IQR
  aggregation this phase's own text named as "the real obstacle." Pushing
  those into SQL too is a real follow-up but a different one: SG-bracket
  filtering and putting classification aren't outlier-rejection problems,
  so `percentile_cont` doesn't apply, and each would need its own
  correctness argument the way `club_carry_dispersion_sql` got here.
- **The streaming export still does N+1 queries against practice sessions**
  the same way it does against rounds — not separately benchmarked above
  since the seeded demo account and this benchmark's synthetic data both
  have only one practice session, so its contribution to the 708ms figure
  is real but small next to the 300-round cost. Would be fixed by the same
  merge-join redesign as the rounds gap above.

## Phase 17 — Type-Safety Follow-Through (done, one item needs a human)

Goal: Phase 12 added pyright, fixed the two real bugs it found, and demoted
five rule categories to `warning` with a written justification. That was the
right call for a phase whose job was "add a type checker" — it is not a
permanent answer, and the justification says so.

The warning count had grown to 121 by the time this phase started (up from
Phase 12's 101/103 — later phases kept adding SQLModel-facing code, as
expected), and it broke down into more than the two named clusters:
nullable-PK mismatches (~60) and geometry-column mismatches (~10) were real
and exactly as described, but the largest remaining cluster (~50) was a
third, unnamed shape — SQLModel types a class attribute's *static* access
(`Shot.id`, `Shot.club`, `Round.played_at`) as the column's plain Python
type (`int | None`, `str | None`, `datetime`) rather than the SQLAlchemy
column-expression it actually is at that level, so `.order_by()`, `.join()`
predicates, `.is_not()`, `.in_()`, and `.desc()` all fail to type-check even
on perfectly correct SQLAlchemy code. This is a known, long-standing
SQLModel/pyright gap (SQLModel's fields are Pydantic-typed for validation,
not `Mapped[]`-typed for the ORM side), not something introduced here.

- [x] **Narrow the nullable-primary-key pattern.** `app/core/orm_typing.py`'s
  `persisted(id_: T | None) -> T` raises `AssertionError` on `None`
  (surfacing a real bug loudly, not silently returning a wrong type) and is
  otherwise identity — applied at ~50 call sites across `app/api/routes/*.py`
  and `app/db/seed.py` wherever a route reads `row.id`/`row.user_id`/etc. off
  a row it just fetched or committed+refreshed.
- [x] **Annotate geometry columns honestly.** `course.py`'s `Hole` fields,
  `Shot.location`, and `RoundHolePin.location` are now typed `WKTElement`
  (`| None` where nullable) instead of `str | None` — matching every
  constructor call site (`_point()`/`_polygon()` in `courses.py`/`seed.py`,
  `WKTElement(...)` in `rounds.py`), never `str`. `WKTElement` has no
  Pydantic schema of its own, so each of those three model classes also
  picked up `model_config = {"arbitrary_types_allowed": True}` — these
  tables are never validated against untrusted input (always built
  internally with a real `WKTElement`), so there's nothing to validate.
- [x] **The unnamed third cluster.** `app/core/orm_typing.py`'s `col(attr:
  Any) -> Any` is `Any`-typed identity, reached for only at query-
  construction call sites where pyright is flatly wrong about what
  `SomeModel.column` is — never to paper over an actual mismatch. Applied at
  ~40 call sites. Two related, narrower stub gaps got scoped
  `# type: ignore[the specific rule]` instead, each with an inline comment
  naming the gap, since no type-level fix existed: SQLModel's typed
  `select()` overloads cap at 4 positional columns (beyond that there's no
  matching overload at all, typed or `Any`-typed — verified directly, not
  assumed) — 6 call sites selecting 5+ raw columns; and a multi-column
  select's row type resolves to a bare `tuple[...]` rather than the
  named-attribute `Row` it actually is at runtime once `.label()` is
  involved — 2 call sites. `Shot.__table__` (real at runtime, untyped by
  SQLModel) got the same treatment, 1 site. Two further issues turned out to
  have real fixes instead of needing a workaround:
  `app/services/parsers/fit_parser.py`'s `fitparse` library ships no type
  stubs at all, so a local `_FitMessage` Protocol + `cast()` types its
  messages precisely rather than guessing at a suppression; and
  `app/services/putting.py`'s `evaluate_putting(shots: list[ShotView])`
  rejected `list[Shot]` (a real caller, `rounds.py`'s single-round analytics
  endpoint, which loads full `Shot` ORM objects) purely from `list`'s
  invariance despite `Shot` structurally satisfying `ShotView` — changed to
  `Sequence[ShotView]`, correct for a read-only parameter regardless of the
  typing issue it also happens to fix.
- [x] **Re-promote the five rules to `error`** in `pyproject.toml`. Verified
  clean with `reportUnnecessaryTypeIgnoreComment` also enabled (temporarily,
  not committed — it's a one-time check, not an ongoing rule this repo has
  opted into): one pre-existing ignore in `_shot_queries.py` (predating this
  phase) turned out to have become unnecessary as a side effect of an
  unrelated fix nearby and was removed, leaving 10 scoped ignores, all
  confirmed live.
- [ ] **Confirm the Docker build job actually passes** (Phase 12 gap: correct
  but unverified, because this sandbox blocks registry blob fetches). Still
  needs a human to look at the first CI run against GitHub's runners and
  check this box — no code changes this phase touch that job either way.

**Acceptance criteria, verified:** `uv run pyright app/` reports 0 errors, 0
warnings, 0 informations with all five rules at `error`
(`app/api/routes/rounds.py` alone went from 44 warnings to 0). Every
remaining suppression is a scoped `# type: ignore[rule]` with an inline
comment naming the specific gap — no bare `# type: ignore`, confirmed by
grep. 401 backend tests, up from 397 at the start of this phase — the 4 new
tests (`tests/test_orm_typing.py`, covering `persisted()`'s pass-through
including the `0`-is-not-`None` case, its raise-on-`None` path, and `col()`'s
identity) are for the two new primitives this phase added, not a behavior
change to anything existing; every other file's test count is identical,
and none of their assertions changed. ruff clean. Verified live against the
running dev stack: `GET /bag`, `/practice/delivery`, `/practice/combines`,
`/me/export`, `/rounds?limit=1`, `/rounds/{id}/holes`,
`/rounds/{id}/analytics`, `/rounds/{id}/holes/{n}/replay`, `/rounds/{id}/shots`,
and `/courses` all called against the seeded demo account and inspected by
hand — identical output to before this phase (same Strokes Gained totals,
same putting percentages, same hole geometry). A Chromium pass over `/`,
`/rounds`, `/rounds/{id}`, `/practice`, and `/virtual-bag` showed zero new
console errors. 364 frontend tests unaffected (no frontend files changed —
this phase is backend typing only).

## Not scheduled — blocked on something other than engineering time

These are real gaps, listed so they aren't mistaken for oversights. None of
them is waiting on a decision I can make or work I can do.

- **Curated combine videos** (Phase 6 gap). PRD §7.1 wants curated video
  tutorials; each combine currently links to a YouTube *search* for its drill
  name. Filling this in needs either real video URLs from a human or a
  curation pipeline someone has decided to own — guessing at plausible-looking
  video links would be exactly the "quietly present unverified things as
  working" failure this repo's conventions forbid.
- **Live Garmin verification** (Phases 3, 5, and this session's scorecard
  work). The OAuth flow needs paid Developer Program credentials. The
  scorecard mapper is verified against a real sanitized payload;
  `get_golf_shot_data`'s shape is not, and needs one real run against a live
  account to stop being provisional.
- **Mapbox and Overpass live verification** (Phases 4 and 5). Both blocked by
  the sandbox's network egress policy, both unit-tested against realistic
  fixtures in the meantime.
- **Legal review of the privacy notice** (Phase 7). Labelled "Draft — pending
  legal review" in the product itself. Needs counsel, not code.
- **GitHub secret scanning** (Phase 12). A repository setting, not a commit —
  needs an admin to toggle it at Settings → Security.

## Backlog (not yet scheduled into a phase)

- ~~`get_round_analytics` does `holes[shot.hole_id]` against a dict built only
  from the round's *current* course...~~ **Fixed.** A course reassignment
  after shots were recorded now raises a deliberate 409
  (`test_analytics_endpoint_409_when_course_reassigned_after_shots_recorded`)
  instead of an unhandled `KeyError` — the exact scenario
  `_persist_round_strokes_gained` already no-op'd on rather than crashed for.
- ~~`create_shots_bulk` is documented as purely additive with no edit path...~~
  **Fixed.** `Shot` now has a `UniqueConstraint("round_id", "hole_id",
  "shot_number")` (migration `da7ddd5e0023`) — a hole's shot 1, shot 2, ...
  is a natural key, not just a dedup mechanism. The route checks for an
  existing match before inserting and returns it instead of erroring or
  duplicating, so a retried submit (dropped connection after the write
  actually landed) is safe; a genuinely new hole's shots still accumulate
  normally. Both directions covered:
  `test_resubmitting_the_same_shot_does_not_duplicate_it`,
  `test_duplicate_shot_within_one_payload_does_not_duplicate_it`,
  `test_a_second_hole_can_still_be_added_after_the_first`.
- ~~No merge/rename flow for near-duplicate players (carried from Phase 8).~~
  **Split.** Rename turned out to already work — `PATCH /api/auth/me` covers
  it, as a side effect of Phase 10 rather than by design for this item.
  **Account merge itself is deferred here, deliberately, not scheduled.** A
  four-perspective plan review (see Part III's intro) found no evidence
  anyone has actually hit the scenario it exists for — it was inherited from
  Phase 8's picker UI, which let near-duplicate accounts get created by
  typo, and that picker no longer exists; real login/password auth makes the
  triggering scenario much rarer. If it does get built: it proves ownership
  of the second account by the same emailed-confirmation primitive password
  reset (Phase 15) builds, and needs its own transaction covering rounds,
  shots, practice sessions, virtual rounds and the Garmin connection, plus
  an explicit answer for what happens when both accounts have a row that
  collides (e.g. a round on the same date) — none of which was worked out
  before this deferral, on purpose.
- **Server-side session revocation** (Phase 10 gap, considered for Phase 14
  in the first draft of this Part, deferred by the plan review). Today's
  revocation lever — rotate `SECRET_KEY`, which invalidates every session at
  once — is coarse but functional at this app's actual scale, and the
  original framing of the cost was wrong: `get_current_user` already reads
  the database on every authenticated request, so a `session` table adds a
  *second* read or a join, not a first one. If this gets built, prefer a
  `revoked_at`/`session_version` column checked in that existing query over
  a separate lookup, and re-run `scripts/benchmark.py` either way — the plan
  review's developer read flagged this as the one change in this document
  that can plausibly slow every endpoint.
- **Login/register/upload/forgot-password rate limiting** (Phase 10 *and* 11
  gap, also deferred from the first draft's Phase 14; Phase 15 added a
  fourth public endpoint sharing it rather than closing it). Still real —
  Argon2 makes one password guess expensive, which is not the same as
  bounding the number of guesses, and `forgot-password` triggers a real
  email send per request — just not urgent enough to lead with. Needs a
  decision this repo hasn't had to make yet: there's no Redis or equivalent
  shared store in `docker-compose.yml` today, only Postgres, and in-memory
  counters don't work once there's more than one worker process. Build the
  counters on Postgres, or add a shared cache, before writing the limiter
  itself.
- **Caching `GET /rounds/{id}/analytics`** (cut from Phase 16's first draft
  by the plan review). Phase 11 already got this endpoint to 5.7ms; a cache
  whose key can miss the round's shots, its course, or the caller's handicap
  index serves a confidently wrong Strokes Gained number, and that
  correctness risk isn't worth it for an endpoint that isn't slow. Revisit
  only if profiling on real usage ever shows otherwise — not a guess ahead
  of the data.
- **Faster manual entry** (raised by the plan review's end-user read, not
  previously written down anywhere). Live Garmin sync stays blocked on a
  paid Developer Program account (see "Not scheduled" above) with no
  near-term path to unblocking it, which means hand-clicking every shot on
  a hole map stays the fastest way to get a round in for the foreseeable
  future. Bulk hole entry, or a spreadsheet/CSV import for a whole round at
  once, would address the actual bottleneck a real user is facing today —
  worth scoping into a phase once there's a concrete design, rather than
  left implicit.
- **Live, in-round pin capture** (raised by Phase 14's pre-implementation
  panel pass, specifically the end-user read). Phase 14 as scoped captures a
  pin after the fact, at a desk, in manual entry — the same read predicted
  that's exactly the kind of optional step a player skips every time,
  leaving the "true" short-siding feature mostly dormant on top of a mostly
  unused field. The read's actual ask was a one-tap prompt at the moment of
  play, tied to whatever GPS fix is already being captured, not a form field
  reached later. This app has no live/in-round mobile capture surface today
  at all — every ingestion path (`.FIT` upload, manual entry) is
  retrospective — so this isn't a small addition to Phase 14, it's a new
  capability. Worth designing once Phase 14 ships and there's real data on
  whether desk-based pin capture actually gets used, per that phase's own
  new acceptance criteria around `has_pin` being measurable.
- **"Share" nav item removed pending a real spec** (found by a UX audit
  walking every page, 2026-08-16). `NavBar` linked to `/share` as one of
  PRD §8's five nav items, but no page, route, or backend ever existed
  behind it, and nothing in the PRD beyond the §8 wireframe caption
  describes what it should do — no public link, export, or share-token
  concept is specified anywhere. A dead link in primary nav is worse than
  a missing one, so it's removed (`nav-bar.tsx`) until there's an actual
  design to build against: what gets shared (a round? the coach brief?),
  with whom, and whether it's a public URL, a signed export, or something
  else.

- **Round review/verification is a dead end for the `.FIT`-upload path, and
  the dashboard can't tell an in-progress round from a finished one**
  (found by a full-app testing pass, 2026-08-21 — full write-up, code
  references, and live repro steps in `docs/KNOWN_ISSUES.md`'s Open
  section). Two compounding gaps: (1) `/rounds/[id]/audit`'s wizard
  reviews shots entirely client-side and never calls the backend —
  finishing it just says persistence "isn't built yet," discarding the
  user's work, even though the dashboard's own "audit needed" banner sends
  people there after every `.FIT` upload; manual entry
  (`/rounds/[id]/enter`) is the only ingestion path that actually saves
  anything. (2) No code path anywhere ever sets a `Round`'s status to
  `verified` — it's permanently `needs_audit` for every real round, only
  the seed script's demo data ever shows "Verified" — and the dashboard's
  Tiger 5 Meter / Clean Card Index render off whatever shots exist with no
  "this round isn't finished" signal beyond zero shots, so a round with
  one hole entered out of eighteen shows a misleadingly perfect 100% Clean
  Card Index. Needs a real design decision (what makes a round "done" —
  all 18 holes? an explicit user action?) before either half can be fixed,
  which is why this is recorded here rather than patched inline.
- **Manual-entry shot-entry label and Next.js 16 dev-server tsconfig drift**
  (found and fixed same pass, full-app testing pass, 2026-08-21 — see
  `docs/KNOWN_ISSUES.md`'s Fixed section for both). The enter-shots page's
  "· pinned" label, confusable with the unrelated hole-pin feature next to
  it, is now "· GPS set". Separately, `next dev`/`next build` on the
  Next.js 16.3.0 this repo is now on required `tsconfig.json`'s `jsx:
  "preserve"` → `"react-jsx"` (a real, mandatory requirement the version
  bump had never picked up, not a cosmetic reformat) and a new
  `.next/dev/types/**/*.ts` include path; both are now committed, and
  `next.config.ts`'s new `agentRules: false` plus a `.gitignore` backstop
  stop `next dev` from also writing uncommitted `AGENTS.md`/`CLAUDE.md`
  files into `apps/web/` on every run.

New findings go here first; they move into a phase once there's enough of a
theme to justify one.

## Cross-cutting (ongoing, not a single phase)

- **Data privacy:** delivered as Phase 7 — see [`docs/DATA_PRIVACY.md`](./DATA_PRIVACY.md) for the remaining non-engineering gap (legal review of the user-facing notice). The access-control hole that makes those endpoints reachable by anyone is Phase 10.
- **Player identity:** delivered as Phase 8 above — still not real authentication, by design; Phase 10 is where that gap actually closes.
- **CI:** keep `.github/workflows/ci.yml` green; add new test suites to the existing `backend`/`frontend`/`tools` jobs rather than creating parallel pipelines. Since Phase 12 that also means keeping `pyright`, `pip-audit` and both coverage steps green — a new dependency with a known CVE, or a new type error, fails the build.
- **Gaps are load-bearing, not decoration.** Every phase entry ends with what it didn't do, and Part III exists because those lists were written honestly enough to be actionable a dozen phases later. A phase that ships with an empty "gaps carried forward" section should be treated as under-reported rather than perfect.
