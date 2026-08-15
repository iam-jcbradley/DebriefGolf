# services

Business logic lives here: the Strokes Gained engine, Tiger 5 / Clean Card Index
evaluation, Smart Bag outlier rejection, .FIT/CSV parsers, R10/R50 delivery
profiling, and hole-geometry/dispersion math. Built out across Phases 1, 2, 3,
4, and 5 of [`docs/DEVELOPMENT_PLAN.md`](../../../../docs/DEVELOPMENT_PLAN.md).

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

Exposed via `GET /api/rounds/{id}/analytics` and `GET /api/bag/{user_id}`
(`app/api/routes/rounds.py`, `app/api/routes/bag.py`).

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
and the `dispersion_ellipse` field added to `GET /api/bag/{user_id}`
(`app/api/routes/rounds.py`, `app/api/routes/bag.py`).

**Not yet implemented:** prescriptive combine matching and the coach lesson
brief export (Phase 5).
