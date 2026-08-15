# services

Business logic lives here: the Strokes Gained engine, Tiger 5 / Clean Card Index
evaluation, Smart Bag outlier rejection, .FIT/CSV parsers, and R10/R50 delivery
profiling. Built out across Phases 1, 2, and 5 of
[`docs/DEVELOPMENT_PLAN.md`](../../../../docs/DEVELOPMENT_PLAN.md).

**Implemented (Phase 1):**
- `benchmarks.py` — Strokes Gained benchmark curves (expected strokes to hole
  out, per lie + handicap bucket) and the `expected_strokes()` lookup the
  Phase 2 SG engine will subtract to compute Strokes Gained.
- `parsers/fit_parser.py` — Garmin `.FIT` activity file parsing (GPS track +
  metadata), gracefully flagging unparseable/sparse files `casual_practice`.
- `parsers/launch_monitor_parser.py` — Approach R10/R50 CSV/JSON delivery
  data parsing, tolerant of header naming variance.

**Not yet implemented:** the Strokes Gained engine, Tiger 5 evaluator, Smart
Bag outlier rejection (Phase 2); prescriptive combine matching and coach
lesson brief export (Phase 5).
