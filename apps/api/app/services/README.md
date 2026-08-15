# services

Business logic lives here: the Strokes Gained engine, Tiger 5 / Clean Card Index
evaluation, Smart Bag outlier rejection, .FIT/CSV parsers, and R10/R50 delivery
profiling. Built out across Phases 1, 2, and 5 of
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
  gapping. Lateral dispersion is wired up but unpopulated (see module
  docstring — needs data Phase 4 will add).
- `putting.py` — lag speed efficiency (>20ft putts) and start-line
  conversion (<6ft putts).
- `approach.py` — short-sided vs. safe-leave classification. A distance/lie
  proxy pending real pin-position geometry (Phase 4) — see module docstring.

Exposed via `GET /api/rounds/{id}/analytics` and `GET /api/bag/{user_id}`
(`app/api/routes/rounds.py`, `app/api/routes/bag.py`).

**Not yet implemented:** prescriptive combine matching and the coach lesson
brief export (Phase 5).
