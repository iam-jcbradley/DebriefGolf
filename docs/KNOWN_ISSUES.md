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

None currently — the four entries below were the only ones found by the
2026-08-16 QA gut-check, and all four are now fixed.

## Fixed

- ~~**Stale service-layer README.** `apps/api/app/services/README.md` — the
  file `CLAUDE.md` explicitly points readers to first ("See
  `app/services/README.md` for what each module does and which phase built
  it") — hasn't been updated since Phase 5. It documents a
  `GET /api/bag/{user_id}` route shape Phase 10 deleted (identity comes from
  `CurrentUser`, no endpoint takes a `user_id`), and its last line still
  claims combine matching and the coach lesson brief export are "not yet
  implemented," though both shipped and were touched again through Phase 14.~~
  **Fixed.** Rewrote the README's route references to match `CurrentUser`
  (no more `{user_id}`, found in four places across the bag and practice
  route sections, not just the one the original report called out) and
  added the missing Phase 6/11/14 sections
  (`delivery_profile.py`, `practice_combines.py`, `shot_view.py`, the Phase
  14 `approach.py`/`geometry.py` changes), replacing the stale "not yet
  implemented" line with a pointer at `DEVELOPMENT_PLAN.md`'s own gap
  tracking instead of duplicating it here. Docs-only; no regression test —
  verified by reading it against the current route/service tree. *Found by:
  QA panel gut-check, 2026-08-16. Fixed: 2026-08-16.*

- ~~**Mapbox hole-replay markers hardcode hex colors that violate the style
  guide.** `apps/web/src/components/hole-replay/hole-replay-map.tsx:75-121`
  uses raw hex (`#0ca30c`, `#2a78d6`, `#d03b3b`, `#c9a227`, `#0b0b0b`)
  instead of the `--primary`/`--status-*` CSS custom properties
  `STYLE_GUIDE.md` requires ("one accent color," no second bright color).
  Its SVG sibling, `hole-replay-svg.tsx`, gets this right with
  `var(--primary)` etc. Likely drifted because no environment this project
  has run in has ever had a real `NEXT_PUBLIC_MAPBOX_TOKEN` to visually
  check it against — see the standing Mapbox verification limit in
  `CLAUDE.md`.~~ **Fixed.** mapbox-gl's `Marker`/paint APIs need a literal
  color, not a live `var(...)` reference, so a straight copy of the SVG's
  `var(--primary)` strings wasn't an option — added `resolveThemeColor()`,
  which reads the custom property's *computed* value off
  `document.documentElement` at marker-creation time, and pointed every
  marker/line at the same tokens `hole-replay-svg.tsx` uses (tee →
  `--foreground`, green → `--status-good`, pin/shot-path/non-short-sided
  shots → `--primary`, short-sided shots → `--status-critical`) so both
  views agree and both track the active light/dark theme. Regression test:
  `hole-replay-map.test.tsx` now sets the CSS custom properties on
  `document.documentElement` in `beforeEach` and asserts markers are created
  with the resolved values, not a hardcoded hex — it would fail if a color
  reverted to a literal. *Found by: QA panel gut-check, 2026-08-16. Fixed:
  2026-08-16.*

- ~~**Near-duplicate ~100-line bulk-upsert blocks in `rounds.py`.**
  `create_shots_bulk` and `create_pins_bulk` each independently implement
  the same shape: ownership check → 409 on no course → hole-number
  resolution → 422 on unknown hole → upsert-by-natural-key loop → commit →
  serialize. A fix to one (an ownership edge case, an extra validation) has
  nothing forcing it onto the other.~~ **Fixed.** Extracted the identical
  preamble — ownership check, course-assigned check, hole-number-to-id
  resolution, unknown-hole 422 — into `_resolve_round_holes()`, which both
  endpoints now call instead of maintaining their own copy. The upsert loops
  themselves stay separate: `Shot`'s natural key is `(hole_id,
  shot_number)` and `RoundHolePin`'s is `hole_id` alone, and the two entities
  serialize to different shapes, so unifying that part would trade a real
  duplication for a forced abstraction. No behavior change — the existing
  `test_rounds.py` bulk-shots/bulk-pins tests (ownership 404s, no-course
  409s, unknown-hole 422s, idempotent resubmits) all pass unmodified against
  the refactored code. *Found by: QA panel gut-check, 2026-08-16. Fixed:
  2026-08-16.*

- ~~**GeoJSON green-boundary ring parsing duplicated verbatim** in
  `rounds.py::_hole_geometry_contexts` and `courses.py::_serialize_course` —
  the same `json.loads(...)["coordinates"][0]` plus `lng, lat` → `LatLng`
  swap in two files. Small, but `geometry.py` already exists as the one
  place this kind of PostGIS/GeoJSON unwrapping should live.~~ **Fixed.**
  Added `geometry.py::green_boundary_ring()` and pointed both call sites at
  it. No behavior change — `test_hole_replay_routes.py` and
  `test_courses_routes.py`'s existing green-boundary assertions pass
  unmodified. *Found by: QA panel gut-check, 2026-08-16. Fixed: 2026-08-16.*

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

- ~~**`apps/web/Dockerfile`'s `prod` stage always failed:
  `COPY --from=build /app/public ./public` — `apps/web` has no `public/`
  directory.** This project uses the App Router's own `src/app/favicon.ico`
  convention, not a `public/` folder, so nothing has ever populated that
  path. Once the buildx-driver fix above let the build actually run, it got
  all the way through `pnpm build` (a real, successful `next build`) before
  failing on this COPY — a second, independent bug stacked behind the
  first, invisible until the first one was cleared. This Dockerfile has
  seemingly never produced a working prod image, in any environment that
  actually ran it to completion.~~ **Fixed.** Removed the `public/` COPY
  line — there's nothing at that path for any Next.js build here to
  produce, so there's nothing for the image to copy. *Found by: PR #21's
  second CI run, 2026-08-16. Fixed: 2026-08-16.*
