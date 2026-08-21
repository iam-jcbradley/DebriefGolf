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

- **`src/app/rounds/[id]/enter/page.test.tsx`'s "submits the round and
  redirects to the round detail page" test is flaky under the full
  suite.** It fails intermittently with `expected "vi.fn()" to be called
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

- **The audit wizard never submits a reviewed round to the backend — the
  `.FIT`-upload ingestion path dead-ends and silently discards the user's
  work.** `POST /rounds/upload` (Phase 1/3) only extracts a GPS track; the
  Phase 3 design was for `/rounds/[id]/audit` to be where those points get
  segmented into shots and reviewed. The dashboard's "Round uploaded — audit
  needed" banner (`isPendingAnalytics`, shown whenever a round has zero
  shots) links straight to it. But `AuditWizard`
  (`src/components/audit-wizard/audit-wizard.tsx`) and its parent page
  (`src/app/rounds/[id]/audit/page.tsx`) only ever call
  `setShots`/`useAuditDraft` — grepping the whole `audit-wizard/` and
  `lib/audit/` trees for `submitRoundShots` or any other `@/lib/api` import
  turns up nothing. Working through the wizard to completion lands on "All
  caught up ... Submitting a reviewed round back to Debrief Golf needs a
  course assigned to it first — that flow isn't built yet (see
  docs/DEVELOPMENT_PLAN.md Phase 3/4)" — text left over from Phase 3, and
  now also factually wrong: Phase 5 added course assignment at round
  creation, so a round reaching the wizard always has one. Reproduced
  live: uploaded `tests/fixtures/corrupted.fit` (flagged `casual_practice`,
  as designed), followed the dashboard's own "Open the audit wizard" link,
  added and fully reviewed a shot, hit "All caught up" — `GET
  /rounds/{id}/shots` for that round still returns `[]`. Phase 5's own goal
  line claims "it also finally wires up the audit wizard's client-only
  draft state ... to real persistence," but what actually shipped was a
  *separate*, new page (`/rounds/[id]/enter`) with a real
  `submitRoundShots` call — the original `/audit` wizard was never touched,
  and the gap was never recorded as carried-forward anywhere. Net effect:
  the only working ingestion path today is manual entry
  (`/rounds/new` → `/rounds/[id]/enter`); the `.FIT`-upload path the
  dashboard actively promotes leads users to lose their review work. *Found
  by: full-app testing pass, 2026-08-21.*

- **No code path ever marks a `Round` `verified`, so the dashboard can't
  tell a genuinely clean round from a barely-started one.** Grepping all of
  `apps/api/app/` for `RoundStatus.verified` turns up exactly one hit:
  `app/db/seed.py`'s hardcoded demo round. There is no `PATCH /rounds/{id}`
  endpoint and no other write path that changes `status` after creation —
  every round created through a real flow (manual entry or `.FIT` upload)
  defaults to `needs_audit` (`app/api/routes/rounds.py:253`) and stays
  there forever, so the "Needs audit" vs. "Verified" distinction
  `rounds/page.tsx`'s `STATUS_LABELS`/`STATUS_CLASSES` render is dead for
  every real user — only the seeded demo account ever shows "Verified."
  Compounding this, the dashboard's Tiger 5 Meter doesn't fall back to
  `status` either: `isPendingAnalytics` only detects *zero* shots (the
  `.FIT`-upload-with-nothing-reviewed-yet case above), so a round with a
  handful of shots but far short of 18 holes — the normal in-progress state
  for manual entry, which the Backlog's "Faster manual entry" item already
  notes happens hole-by-hole over multiple sessions — renders the full
  Round Snapshot and Tiger 5 Disaster Meter as if the round were finished.
  Reproduced live: created a round via `/rounds/new`, entered 3 shots for
  hole 1 of 18 via `/rounds/[id]/enter`, submitted. The dashboard's "Where
  It Went Wrong" panel showed 0 for every Tiger 5 category and a **100%
  Clean Card Index** — a real golfer checking their dashboard mid-entry
  would see a falsely reassuring "perfect round" for data that's one hole
  out of eighteen. This is presumably the same root cause as the audit-wizard
  gap above: `verified` looks designed to mean "reviewed and complete," but
  nothing ever sets it, so no signal exists anywhere for "this round isn't
  done yet" beyond the zero-shots case. *Found by: full-app testing pass,
  2026-08-21.*

- **Four files trip `react-hooks/set-state-in-effect`, an ESLint warning
  `pnpm lint`/CI don't fail on.** `src/app/rounds/[id]/enter/page.tsx:56`,
  `src/app/rounds/[id]/page.tsx:62`, `src/app/rounds/page.tsx:45`, and
  `src/lib/current-user.tsx:73` all call `setState` synchronously inside a
  `useEffect` body (clearing prior state before an async fetch, or setting
  `loading`), which `eslint-plugin-react-hooks` flags as able to trigger a
  cascading extra render. `apps/web/package.json`'s `lint` script is plain
  `eslint` with no `--max-warnings 0`, so these show up green in CI (`pnpm
  lint` exits 0) and are easy to miss without reading the job's full log.
  Not verified as a real user-visible bug — the standard fix (moving the
  reset into the state updater that starts the fetch, or an early-return
  guard) touches core data-loading effects in four different files, which
  is real design/testing work, not a drop-in edit — so left as a
  documented finding rather than fixed in the same pass this was found in.
  *Found by: full-app testing pass, 2026-08-21.*

## Fixed

- ~~**Ambiguous "· pinned" label in the manual-entry shot list.**
  `src/app/rounds/[id]/enter/page.tsx`'s per-shot summary line appended "
  · pinned" whenever `shot.location` was set — i.e., whenever *that shot's
  own* GPS location had been clicked. The same page already uses "pin" for
  a distinct, separately-tracked concept (the hole's actual flag position
  for the day, set via the adjacent "Set today's pin" mode in
  `HoleShotEntry`), so a shot with a GPS location and a hole with a
  recorded pin both showed pin-flavored language for two different
  things.~~ **Fixed.** Changed the label to "· GPS set", which describes
  what's actually true (this shot has a location) without colliding with
  the hole-pin terminology used two lines above it in the same UI.
  `page.test.tsx`'s "adds a shot with a GPS location and lists it" test
  updated to assert the new text. *Found by: full-app testing pass,
  2026-08-21. Fixed: 2026-08-21.*

- ~~**`next dev` (Next.js 16.3.0) writes `apps/web/AGENTS.md` +
  `apps/web/CLAUDE.md` and rewrites `apps/web/tsconfig.json` on every run,
  none of it gitignored.** Confirmed by starting the dev server for this
  testing pass and running `git status` immediately after: two new
  untracked files, plus `tsconfig.json`'s `jsx` silently changed from
  `preserve` to `react-jsx` (Next 16's own console output calls this a
  "mandatory" change, not a suggestion) and `.next/dev/types/**/*.ts` added
  to `include`. Every contributor who runs `pnpm dev` locally gets this
  same churn in `git status`, and the generated `apps/web/CLAUDE.md` — its
  entire content is `@AGENTS.md` — risked eventually getting committed by
  accident and shadowing this repo's real root `CLAUDE.md` for any tooling
  that reads directory-local instructions.~~ **Fixed.** Set `agentRules:
  false` in `apps/web/next.config.ts` so the generator doesn't run at all,
  gitignored `apps/web/{AGENTS,CLAUDE}.md` as a backstop in case a
  contributor's Next version doesn't honor that flag, and committed the
  `tsconfig.json` change for real (`jsx: react-jsx`, the new
  `.next/dev/types` include path) instead of leaving it as permanent
  working-tree drift — it turned out to be a genuine, mandatory
  requirement of the Next 16 upgrade that had never been applied, not a
  cosmetic auto-format. Verified with a clean `pnpm dev` restart (no new
  untracked files) and a full `pnpm build` (compiles, typechecks, and
  prerenders all 13 routes). *Found by: full-app testing pass, 2026-08-21.
  Fixed: 2026-08-21.*

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
