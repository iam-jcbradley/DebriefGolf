# services

Business logic lives here: the Strokes Gained engine, Tiger 5 / Clean Card Index
evaluation, Smart Bag outlier rejection, .FIT/CSV parsers, R10/R50 delivery
profiling, practice-combine detection, hole-geometry/dispersion/short-siding
math, and OSM course lookup. Built out across Phases 1–14 of
[`docs/DEVELOPMENT_PLAN.md`](../../../../docs/DEVELOPMENT_PLAN.md).

**Implemented (Phase 1):**
- `benchmarks.py` — Strokes Gained benchmark curves (expected strokes to hole
  out, per lie + handicap bucket) and the `expected_strokes()` lookup the SG
  engine subtracts to compute Strokes Gained.
- `parsers/fit_parser.py` — Garmin `.FIT` activity file parsing (GPS track +
  metadata), gracefully flagging unparseable/sparse files `casual_practice`.
- `parsers/launch_monitor_parser.py` — Approach R10/R50 CSV/JSON delivery
  data parsing, tolerant of header naming variance.

**Implemented (Phase 2):**
- `strokes_gained.py` — `SG = Benchmark(start) - Benchmark(end) - 1` per
  shot, categorized into OTT / APP / ARG / PUTT.
- `tiger_five.py` — double-bogeys+, 3-putts, par-5 bogeys, blown recoveries
  inside 50y, penalties inside 150y, and the Clean Card Index.
- `smart_bag.py` — IQR-outlier-rejected per-club carry dispersion + club
  gapping. Lateral dispersion (mean/stdev per club) is now populated from
  real GPS-derived aim-line offsets computed in `geometry.py` (Phase 4).
- `putting.py` — lag speed efficiency (>20ft putts) and start-line
  conversion (<6ft putts).
- `approach.py` — short-sided vs. safe-leave classification. A distance/lie
  proxy pending real pin-position geometry (Phase 4) — see module docstring.

Exposed via `GET /api/rounds/{id}/analytics` and `GET /api/bag`
(`app/api/routes/rounds.py`, `app/api/routes/bag.py`). Both take identity from
`CurrentUser` (Phase 10) rather than a `{user_id}` path parameter — see
`app/api/deps.py`.

**Implemented (Phase 3):**
- `garmin_oauth.py` — Garmin Connect OAuth 2.0 + PKCE plumbing (authorize
  URL construction, signed state token, code-for-token exchange). Real and
  tested (mocked token endpoint) but unverifiable against Garmin's actual
  servers in this environment — see module docstring.

Exposed via `app/api/routes/garmin_auth.py`.

**Implemented (Phase 4):**
- `geometry.py` — Flat-earth (equirectangular) projection sized for
  golf-hole-scale distances. `offset_from_aim_line()` resolves any GPS point
  into `(longitudinal_yards, lateral_yards)` relative to a hole's tee→green
  line; `compute_lateral_by_club()` batches this per shot to feed
  `smart_bag.py`'s previously-unpopulated lateral dispersion stats. Mirrored
  in TypeScript at `apps/web/src/lib/hole-replay/projection.ts` so the
  frontend's hole-replay SVG agrees with the backend's math pixel-for-pixel.
- `dispersion.py` — `compute_dispersion_ellipse()` turns a club's
  longitudinal/lateral mean+stdev into a `k`-scaled ellipse (default
  `k=1.5`); `is_within_ellipse()` checks point containment (boundary
  inclusive) for future "sucker pin" strategy alerts — built and tested, not
  yet wired to a real per-round pin position (see `approach.py`'s note on
  the same missing-pin-geometry gap).

Exposed via `GET /api/rounds/{id}/holes`, `GET /api/rounds/{id}/holes/{n}/replay`,
and the `dispersion_ellipse` field added to `GET /api/bag`
(`app/api/routes/rounds.py`, `app/api/routes/bag.py`).

**Implemented (Phase 5):**
- `osm_courses.py` — Searches OpenStreetMap's Overpass API (free, keyless)
  for a golf course by name, then resolves each hole's tee/green by
  nearest-endpoint matching against separate `golf=tee`/`golf=green`
  features (OSM doesn't relation-link these to their hole in most
  mappings), reusing `geometry.py`'s flat-earth yard-distance for both the
  matching and the computed yardage. Every field is optional — coverage is
  inconsistent — so this always degrades to manual entry rather than
  failing. Unverifiable against the real Overpass API in this environment
  (blocked by the sandbox's egress policy, same as Mapbox) — see module
  docstring.

Exposed via `GET /api/courses/search-osm` and
`GET /api/courses/search-osm/{type}/{id}`; course/round/shot persistence
itself (`POST /api/courses`, `POST /api/rounds`,
`POST /api/rounds/{id}/shots/bulk`) lives directly in
`app/api/routes/courses.py` / `app/api/routes/rounds.py` rather than a
services module — it's CRUD, not business logic.

**Implemented (Phase 6):**
- `delivery_profile.py` — per-club aggregate launch-monitor delivery numbers
  (Club Path, Face Angle, derived Face-to-Path, Spin Axis, Smash Factor,
  Carry), a per-club per-session trend, and the Sim vs. Real-World Gapping
  Delta against `smart_bag.py`'s on-course carry — reuses that engine rather
  than duplicating it.
- `practice_combines.py` — detects the four PRD §7.1 weaknesses (Approach
  100-125y SG, Driver dispersion, Iron smash factor, Putting lag efficiency)
  from data already computed elsewhere and maps each to its fixed PRD §7.1
  combine. Per-club expected-smash-factor bands
  (`EXPECTED_SMASH_FACTOR_BY_IRON`) replace one flat cutoff since smash
  factor falls with loft; driver dispersion and putting lag are matched
  exactly to their own PRD §7.1 target metrics (15y, 80%).

Exposed via `GET /api/practice/delivery` and `GET /api/practice/combines`
(`app/api/routes/practice.py`), both taking identity from `CurrentUser`; also
feeds the 1-Page Coach-Ready Lesson Brief PDF
(`apps/web/src/lib/coach-brief/coach-brief-document.tsx`), which reuses the
same weakness → combine mapping rather than a second one.

**Implemented (Phase 11):**
- `shot_view.py` — the `ShotView` protocol that lets `smart_bag.py`,
  `putting.py`, and `practice_combines.py` accept either a full `Shot` ORM
  instance or the raw-column rows `GET /bag` and the practice endpoints
  select instead, for the "all of this user's shots" queries where building
  full ORM instances measurably dominates query cost.

**Implemented (Phase 14):**
- `geometry.py` gained `green_extent_beyond_point()` — how much green lies
  beyond a point along the pin-relative miss axis, the geometric primitive
  real short-siding needs.
- `approach.py` — short-sided vs. safe-leave classification, now geometric
  (miss angle relative to the round's actual per-round pin and the green
  boundary polygon) whenever a pin, green boundary, and shot GPS location
  are all on file; falls back to the original distance/lie proxy otherwise,
  which is still the common case for rounds that predate Phase 14.

**Not yet implemented:** nothing tracked here is outstanding as of Phase 14 —
see `docs/DEVELOPMENT_PLAN.md`'s per-phase "Gaps carried forward" sections
for what's still open at the feature level.
