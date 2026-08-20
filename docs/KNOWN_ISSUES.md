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

The entries below marked *(Part IV panel)* come from the five-perspective
review that produced Part IV of `DEVELOPMENT_PLAN.md`. Findings that seat
scheduled into a phase are **not** repeated here — only what it explicitly
declined to schedule, per this file's purpose.

**One meta-finding worth acting on before any individual entry:** three of
the QA seat's highest-confidence findings (D3, A1, and the stale
`smart_bag.py` docstring below) are *recurrences of issues this file has
already logged and marked Fixed*, each time in an unfixed sibling file. A
"check the sibling" step when closing an entry here would have caught all
three for free.

- **Two putting/scoring definitions are product decisions nobody has
  ruled on, and the current behavior isn't written down.** *(Part IV
  panel.)* Both are one-line changes once someone rules; what matters is
  that the present behavior stops being rediscovered. **(a) 3-putt
  detection counts putts played from off the green.**
  `app/services/tiger_five.py:77` is `sum(1 for s in shots if s.club ==
  "Putter")` regardless of lie, while its sibling
  `strokes_gained.py:48-52` deliberately handles the Texas-wedge case and
  documents it — so the two modules classify the same shot differently and
  only one explains itself. Failure scenario: par 4, Putter from the fringe
  (12y → 1.5y), Putter (1.5y → 0.4y), Putter holed. Score 3 = par, so the
  hole counts as clean in the Clean Card Index while `three_putts` reports
  1. `tests/test_tiger_five.py:43-52` only ever uses on-green putts.
  **(b) Putting boundary values fall into no bucket at all.**
  `app/services/putting.py:43-44` uses strict `>` and `<` against `20/3`
  and `6/3` yards, where every other threshold in the codebase is inclusive
  (`strokes_gained.py:53` `<= 30`, `tiger_five.py:105` `<= 50`,
  `approach.py:105` `<= 10`). Failure scenario: a manually-entered 2.0-yard
  (exactly 6ft) putt is in neither `short_putts` nor `lag_putts` and
  silently disappears from both `start_line_conversion_pct` and
  `lag_efficiency_pct`. `tests/test_putting.py` has no boundary test,
  unlike `tests/test_approach.py:96,134` which does exactly this. Add the
  boundary tests either way, whichever way the definitions land.

- **Four low-probability robustness gaps, to batch into whatever phase next
  touches these files** rather than making a phase of them. *(Part IV
  panel.)* **(1)** `create_course` does no scalar validation:
  `courses.py:46-51`'s `_polygon` indexes `ring[0]`/`ring[-1]` unguarded
  with the `len >= 3` check living only at the one call site (`:258`), so
  the helper is a landmine for the next caller; `par`, `yardage` and
  `number` are unvalidated (`courses.py:26-28`), and `par=0` makes every
  hole a double bogey at `tiger_five.py:118`. **(2)** `PATCH /auth/me`
  bounds `handicap_index` not at all (`auth.py:207-215`) — Pydantic accepts
  `"NaN"` for a float, after which every `abs(bucket - nan)` comparison in
  `nearest_handicap_bucket` (`strokes_gained.py:36-39`) returns False and it
  silently falls through to bucket 0. **(3)** `signing.decode`
  (`core/signing.py:88`) does `data["exp"] < time.time()`, which raises
  `TypeError` on a non-numeric `exp`; `read_session_token`/`read_reset_token`
  catch only `TokenError`, so it surfaces as a 500. Not attacker-reachable
  (the payload is HMAC-signed), hence robustness rather than security. Also
  `security.py:71`'s `isinstance(user_id, int)` accepts `True`. **(4)**
  `fit_parser.py:87` catches only `(FitParseError, OSError)`, so a truncated
  file that makes fitparse raise `struct.error`/`ValueError`/`IndexError`
  propagates as a 500 — contradicting the module's own "Never raises"
  docstring at `:71-74` and PRD §4.3's "a corrupted file still creates a
  round, it isn't rejected."

- **Two pieces of collected-then-discarded state, latent until the features
  that would read them exist.** *(Part IV panel.)* Noted here rather than
  scheduled, because each belongs *on* its future item. **(a)** The audit
  wizard asks the user for lag proximity and throws it away:
  `src/lib/audit/review-queue.ts:131` stores `puttRouteResult:
  { lagProximityFeet }` but — unlike the `made` branch at `:133-134`, which
  correctly writes `endLie`/`endDistanceYards` — never writes the number
  back to `endDistanceYards`, and `puttRouteResult` is read nowhere.
  `evaluate_putting` reads `end_distance_yards`, which is exactly the number
  the wizard just collected. Harmless only because the wizard has no submit
  path — which Phase 18 adds, and it shares `DraftShot` with the manual-entry
  flow that already submits. **(b)** `GarminConnection.expires_at` is
  written (`garmin_auth.py:58-71`) and read nowhere: no refresh, no expiry
  check.

- **Small, real, and not worth a phase on their own — good opportunistic
  work for whoever is already in the file.** *(Part IV panel.)*
  `_CLUB_RANK` plus a club-order sort exists twice under near-identical
  names (`smart_bag.py:47`'s `sort_by_club_order` over `ClubGappingStats`,
  `delivery_profile.py:24`'s `_sort_by_club_order` over `str`).
  `nextShotNumberForHole` is duplicated verbatim in `enter/page.tsx:70-72`
  and `audit/page.tsx:19-21`. `rounds.py:369` commits (expiring every
  object) and then calls `session.refresh(shot)` once per shot at `:372` —
  ~90 extra SELECTs on an 18-hole submit — and `get_hole_replay`
  (`rounds.py:705`) fetches `_shot_locations` for the whole round to use one
  hole's worth; `scripts/benchmark.py` is the tool, and per `CLAUDE.md`,
  measure before changing. Four `react-hooks/set-state-in-effect` lint
  warnings remain by deliberate rule-downgrade (see `eslint.config.mjs`),
  two of which — `enter/page.tsx:56` and `current-user.tsx:73` — are the
  effects implicated in the flaky test below.

- **Stale docstrings and a non-existent design token, in load-bearing
  places.** *(Part IV panel.)* `GET /rounds/{id}/analytics`'s docstring
  (`rounds.py:540-544`) still claims it "also persists the computed
  `Shot.strokes_gained` back onto each shot" — the body comment 40 lines
  below says the opposite, and `CLAUDE.md` names this endpoint's
  read-only-ness as a rule, so the docstring contradicts the convention a
  reader hits first. `app/services/smart_bag.py:26-36` still asserts in the
  present tense that "`ClubGappingStats.lateral` is wired up but nothing
  populates it yet" and describes the Phase-2 Python walk that Phase 16
  replaced; both statements have been false since Phase 4 and Phase 16
  respectively — in the module `CLAUDE.md`'s own README pointer directs
  readers to. And `course-geometry-map-svg.tsx:80,82` uses
  `var(--status-positive, #2a9d5c)`, a token that **does not exist** in
  `globals.css` (only `--status-good/warning/serious/critical` do), so it
  always falls through to the literal — the course builder renders a
  different green from `hole-replay-svg.tsx:143`'s `--status-good` for the
  same concept, in both themes. Relatedly, the raw-hex fix this file already
  logged as Fixed for `hole-replay-map.tsx` was never applied to its sibling:
  `course-geometry-map.tsx:102,107,112` still passes `"#0b0b0b"`,
  `"#2a9d5c"`, `"#d08a00"` straight to `mapboxgl.Marker` (and
  `course-geometry-map-svg.tsx:86,88,90` repeats all three), with `#d08a00`
  a fourth bright hue backed by no token at all. `resolveThemeColor` — the
  only correct way to feed a design token into a Mapbox API — is file-private
  in `hole-replay-map.tsx:18` and should be extracted.

- **`src/app/rounds/[id]/enter/page.test.tsx`'s "submits the round and
  redirects to the round detail page" test is flaky under the full
  suite.** **Root-caused by the Part IV panel's QA seat — two independent
  causes, both cheap to fix.** *(a) The assertion is synchronous while the
  handler still has two IndexedDB round trips to go.* Line 159 is a bare
  `expect(mockPush).toHaveBeenCalledWith("/rounds/42")` immediately after
  `await user.click(...)`, but `handleSubmitRound` (`enter/page.tsx:117-119`)
  does `await submitRoundShots` → `await clear()` → `clearDraft()` →
  `openDb()` resolving on `request.onsuccess`, then a transaction resolving
  on `tx.oncomplete` (`draft-store.ts:63-71`) → *only then* `router.push`.
  `await user.click()` flushes microtasks and its own `setTimeout(0)` turns;
  it does not wait for fake-indexeddb's deferred event callbacks. On an idle
  loop those turns happen to suffice, on a loaded one they don't — which
  matches it reproducing only under CI load. The tell: the sibling test at
  `:180-185` wraps its equivalent assertion in `waitFor` for exactly this
  reason, so one test omits a pattern the same file already uses.
  *(b) Ambient un-awaited network work bleeds across test boundaries.*
  `renderWithProviders` mounts `CurrentUserProvider`, which calls the **real**
  `getCurrentUser()` — `@/lib/api` is mocked with `importOriginal` and only
  four functions are overridden (`:29-38`) — producing repeated
  `ECONNREFUSED 127.0.0.1:8000` from `current-user.tsx:59`, with rejections
  surfacing against a *different* test than the one that started them. Each
  calls `setUser(null)` outside `act()`, re-rendering the tree mid-test. All
  seven `renderWithProviders` files do this; `vitest.setup.ts` installs no
  `fetch` stub. **Fix:** (i) wrap line 159's assertion in `waitFor`; (ii)
  stub `getCurrentUser` (or global `fetch`) in `test-utils.tsx` /
  `vitest.setup.ts` — which also removes ~40 stderr stack traces per run.
  Original report follows. It fails intermittently with `expected "vi.fn()" to be called
  with arguments: [ '/rounds/42' ] — Number of calls: 0` — the mocked
  `router.push` never fires, meaning the submit handler didn't complete in
  time. Run in isolation (`pnpm vitest run
  src/app/rounds/[id]/enter/page.test.tsx`) it passes reliably, every time
  (3/3 in a row); it only misfires as part of the full `pnpm test` run, in
  the same position each time it happens (after ~60 other test files),
  which points at cross-file state bleeding into this test — an un-awaited
  promise, a shared mock, or fake-timer state left over from an earlier
  file — rather than a bug in the page itself. Not yet root-caused. Surfaced
  repeatedly (and reproducibly) while rebasing Dependabot PRs #7, #10, and
  #20 across several fresh CI runs on unrelated diffs (a `requests` version
  bump, a `garminconnect` version bump, a `react`/`react-dom` bump) — same
  failure, same test, each time only inside the full-suite run. *Found by:
  Dependabot PR review, 2026-08-17.*

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
