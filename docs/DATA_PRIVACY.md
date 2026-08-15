# Data Privacy & Retention (Working Draft)

Status: **engineering to-dos delivered; user-facing notice still needs legal review before launch.** This translates PRD §9.2 into concrete engineering to-dos. The to-do list below now has real endpoints and UI behind every item, but the privacy notice text itself (`/settings/privacy`) is explicitly labeled "Draft — pending legal review" in the product and should not be treated as a finished policy until reviewed.

## Why this matters

Debrief Golf processes two categories of data that trigger GDPR/CCPA obligations:

1. **Precise location data** — GPS shot coordinates, hole/green geometry, and derived dispersion patterns.
2. **Third-party OAuth data** — Garmin Connect account linkage (OAuth 2.0 tokens) and the scorecard/activity data pulled through it.

**Boundary note (Phase 5):** [`tools/garmin_import/`](../tools/garmin_import/) is a separate, personal-use CLI that authenticates to Garmin Connect with the user's own email/password (there's no OAuth path for this — see that tool's README for why) and caches session tokens *locally, on the user's own machine*. It never sends those credentials, or the session tokens derived from them, to this app's backend or database — only the `.FIT` files it downloads get uploaded, through the same `POST /api/rounds/upload` endpoint a manual drag-and-drop upload would use. This document's "Third-party OAuth data" category still accurately describes everything this app itself stores; the CLI tool's local credential handling is out of scope for this app's data-privacy surface by design, not by omission.

## To-dos before handling real user data (target: by Phase 3, per `docs/DEVELOPMENT_PLAN.md` — delivered in the Data Privacy & Retention phase)

- [x] **Legal basis for processing** — stated in the `/settings/privacy` notice ("Why" section): data is processed to provide the diagnostic features the user directly uses, not for advertising or resale. Not yet reviewed by counsel — the page says so explicitly.
- [x] **Data retention policy** — now explicit rather than implicit: round/shot/practice data is retained until the user deletes their account (no automatic expiry — nothing in the PRD calls for one, and inventing an auto-purge schedule nobody asked for would be its own risk); Garmin OAuth tokens are overwritten on reconnection and deleted immediately on disconnect (`DELETE /api/auth/garmin/{user_id}`, unchanged from Phase 3).
- [x] **User-initiated deletion** — `DELETE /api/users/{user_id}` (`app/api/routes/privacy.py`) is a real hard delete, not a soft flag: every `Shot` and `Round` the user owns, every `PracticeShot`/`PracticeSession`, every `VirtualRound`, the `GarminConnection` row, and finally the `User` row itself, in FK-safe order. `Course`/`Hole` rows are deliberately untouched — they're shared reference geometry other users' rounds may reference, not this user's data. Exposed in `/settings/privacy` behind a type-DELETE-to-confirm step, since this is irreversible.
- [x] **Data export** — `GET /api/users/{user_id}/export` returns the user's profile, rounds (with shots), R10/R50 practice sessions (with shots), and virtual rounds as JSON; raw OAuth token strings are deliberately excluded (only `garmin_connected: bool`) since those are credentials held on the user's behalf, not data about them. `/settings/privacy` downloads it as a file.
- [x] **CCPA "right to know" / "do not sell"** — stated plainly in the `/settings/privacy` notice's "Sharing" section: no sale of user data, no third-party sharing beyond what running the service requires.
- [x] **Minimization in Smart Bag baselines** — re-verified while building deletion: `StrokesGainedBenchmark` (`app/models/benchmark.py`) is seeded from a fixed hand-authored curve (`SCRATCH_CURVES`), not aggregated from real user shot data — see Phase 1's note on that table. There is currently no pipeline that rolls user shots into a shared baseline, so this checklist item has no code to write yet; noting it here so it isn't silently dropped if such a pipeline is ever built.

## Non-goals for this stub

This document does not attempt to write the actual public-facing privacy policy or terms of service — that requires legal review. The `/settings/privacy` notice is a good-faith draft of that copy, not a substitute for it, and says so in the product.
