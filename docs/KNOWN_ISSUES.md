# Known Issues

A running log of real problems found in this codebase — bugs, drift, and
maintainability hazards — separate from `DEVELOPMENT_PLAN.md`'s phases
(planned work) and its Backlog (deferred features). This is where the
**QA seat** of the review panel (`CLAUDE.md`'s "Review process") records
what it finds, whether or not it gets fixed immediately.

Convention, matching `DEVELOPMENT_PLAN.md`'s Backlog: an entry is written
once, in full, when found. Once fixed, the original description is
struck through and a **Fixed.** note explains what changed and points at
the regression test that proves it — the entry stays, it doesn't get
deleted, so the history of what broke and why is still here later.

## Open

- **Stale service-layer README.** `apps/api/app/services/README.md` — the
  file `CLAUDE.md` explicitly points readers to first ("See
  `app/services/README.md` for what each module does and which phase built
  it") — hasn't been updated since Phase 5. It documents a
  `GET /api/bag/{user_id}` route shape Phase 10 deleted (identity comes from
  `CurrentUser`, no endpoint takes a `user_id`), and its last line still
  claims combine matching and the coach lesson brief export are "not yet
  implemented," though both shipped and were touched again through Phase 14.
  *Found by: QA panel gut-check, 2026-08-16.*

- **Mapbox hole-replay markers hardcode hex colors that violate the style
  guide.** `apps/web/src/components/hole-replay/hole-replay-map.tsx:75-121`
  uses raw hex (`#0ca30c`, `#2a78d6`, `#d03b3b`, `#c9a227`, `#0b0b0b`)
  instead of the `--primary`/`--status-*` CSS custom properties
  `STYLE_GUIDE.md` requires ("one accent color," no second bright color).
  Its SVG sibling, `hole-replay-svg.tsx`, gets this right with
  `var(--primary)` etc. Likely drifted because no environment this project
  has run in has ever had a real `NEXT_PUBLIC_MAPBOX_TOKEN` to visually
  check it against — see the standing Mapbox verification limit in
  `CLAUDE.md`. *Found by: QA panel gut-check, 2026-08-16.*

- **Near-duplicate ~100-line bulk-upsert blocks in `rounds.py`.**
  `create_shots_bulk` and `create_pins_bulk` each independently implement
  the same shape: ownership check → 409 on no course → hole-number
  resolution → 422 on unknown hole → upsert-by-natural-key loop → commit →
  serialize. A fix to one (an ownership edge case, an extra validation) has
  nothing forcing it onto the other. *Found by: QA panel gut-check,
  2026-08-16.*

- **GeoJSON green-boundary ring parsing duplicated verbatim** in
  `rounds.py::_hole_geometry_contexts` and `courses.py::_serialize_course` —
  the same `json.loads(...)["coordinates"][0]` plus `lng, lat` → `LatLng`
  swap in two files. Small, but `geometry.py` already exists as the one
  place this kind of PostGIS/GeoJSON unwrapping should live. *Found by: QA
  panel gut-check, 2026-08-16.*

## Fixed

- ~~**`GET /practice/combines` can never recommend the Driver Dispersion
  combine.** `apps/api/app/api/routes/practice.py`'s `_on_course_club_gapping`
  called `compute_club_gapping(distances_by_club)` with no `lateral_by_club`
  argument — unlike its sibling in `bag.py::get_smart_bag`, which does the
  extra tee/green/shot-location join and passes `lateral_by_club=`. Because
  the practice-route copy skipped that join, every `ClubGappingStats.lateral`
  it produced was `None`, so `driver_lateral_stdev` was always `None`, so
  `detect_driver_dispersion_weakness(None)` always returned `None` —
  regardless of how wide a player's actual driver dispersion was. PRD
  §7.1's "30-Yard Corridor Test" combine was dead code in production, and
  nothing failed to reveal it: the existing tests only unit-tested the pure
  detector function, never the route's wiring from real GPS data to it.~~
  **Fixed.** Extracted the shared query+compute logic
  (`app/api/routes/_shot_queries.py`: `fetch_on_course_shots`,
  `fetch_shot_geometry_rows`, `club_gapping_with_lateral`) so `bag.py` and
  `practice.py` call the same function instead of maintaining independent
  copies — the exact fix for a duplicated-helper drift the QA lens exists
  to catch. `get_delivery_profile`'s Sim vs. Real-World gapping delta keeps
  a separate, deliberately lighter carry-only path
  (`_carry_only_club_gapping`) since it never reads `.lateral` and doesn't
  need the extra geometry join. Regression test:
  `test_practice_routes.py::TestPracticeCombinesEndpoint::test_flags_driver_dispersion_weakness_from_real_gps_lateral_spread`
  seeds real GPS-located driver shots with a lateral spread (pstdev ~21y)
  above the 15y threshold — confirmed to fail against the pre-fix code and
  pass against the fix. *Found by: QA panel gut-check, 2026-08-16. Fixed:
  2026-08-16.*

- ~~**`ruff check .` fails on `apps/api`.** 4 errors, all in
  `scripts/benchmark.py` (an unsorted import block, three `E501`
  line-too-long violations) — broken since the file was added in Phase 11.
  `DEVELOPMENT_PLAN.md` claims "ruff clean" as acceptance criteria for
  Phases 11 through 14; pyright genuinely was clean, so this looks like
  `scripts/` quietly falling outside whatever check actually ran before
  that got written down, not a doc-vs-code judgment call.~~ **Fixed.**
  `ruff check --fix` resolved the import sort; the three long lines were
  wrapped by hand. `ruff check .` now passes clean across the whole
  `apps/api` tree, verified directly. *Found by: QA panel gut-check,
  2026-08-16. Fixed: 2026-08-16.*

- ~~**The `docker` CI job fails outright, every time, on both matrix legs.**
  `.github/workflows/ci.yml`'s `docker` job passes `cache-to:
  type=gha,mode=max` to `docker/build-push-action@v6` without ever adding a
  `docker/setup-buildx-action` step, so the build runs on the default
  `docker` buildx driver — which can't export a GHA cache at all: "Cache
  export is not supported for the docker driver." This isn't the
  registry-access sandbox limit `DEVELOPMENT_PLAN.md`'s Phase 12 entry
  predicted; it's a real workflow bug, on `main`, that fails this job for
  every PR. `docs/DEVELOPMENT_PLAN.md` claimed this job as done in Phase
  12; it had never actually run to completion once.~~ **Fixed.** Added
  `docker/setup-buildx-action@v3` before the build step. Found and fixed
  live against a real PR (#21)'s first CI run, not a local check — the kind
  of thing that only surfaces by actually running the workflow for real.
  *Found by: PR #21's CI run, 2026-08-16. Fixed: 2026-08-16.*
