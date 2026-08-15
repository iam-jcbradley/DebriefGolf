# Data Privacy & Retention (Working Draft)

Status: **stub — needs legal review before launch.** This translates PRD §9.2 into concrete engineering to-dos; it is not a finished policy and should not be presented to users as one until reviewed.

## Why this matters

Debrief Golf processes two categories of data that trigger GDPR/CCPA obligations:

1. **Precise location data** — GPS shot coordinates, hole/green geometry, and derived dispersion patterns.
2. **Third-party OAuth data** — Garmin Connect account linkage (OAuth 2.0 tokens) and the scorecard/activity data pulled through it.

**Boundary note (Phase 5):** [`tools/garmin_import/`](../tools/garmin_import/) is a separate, personal-use CLI that authenticates to Garmin Connect with the user's own email/password (there's no OAuth path for this — see that tool's README for why) and caches session tokens *locally, on the user's own machine*. It never sends those credentials, or the session tokens derived from them, to this app's backend or database — only the `.FIT` files it downloads get uploaded, through the same `POST /api/rounds/upload` endpoint a manual drag-and-drop upload would use. This document's "Third-party OAuth data" category still accurately describes everything this app itself stores; the CLI tool's local credential handling is out of scope for this app's data-privacy surface by design, not by omission.

## To-dos before handling real user data (target: by Phase 3, per `docs/DEVELOPMENT_PLAN.md`)

- [ ] **Legal basis for processing** — document the basis (consent vs. contract necessity) for GPS and OAuth data processing; surface it in a user-facing privacy notice at signup / Garmin account linking.
- [ ] **Data retention policy** — define concrete retention windows for rounds, shot coordinates, and OAuth tokens (e.g. tokens refreshed/rotated, revoked on disconnect; round data retained until user deletion). No retention period is currently defined — this is a placeholder that must be set explicitly, not left implicit.
- [ ] **User-initiated deletion** — a "delete my data" flow that removes a user's spatial (shot/hole geometry) and scorecard records, and revokes stored Garmin OAuth tokens. Should be a real deletion (or documented anonymization), not a soft/hidden flag.
- [ ] **Data export** — GDPR gives users a right to access/portability; plan a JSON/CSV export of a user's own rounds and shots alongside the deletion flow.
- [ ] **CCPA "right to know" / "do not sell"** — confirm whether any data is shared with third parties (e.g. analytics providers) and disclose accordingly; Debrief Golf does not currently plan to sell user data, but this should be stated explicitly in the privacy notice once written.
- [ ] **Minimization in Smart Bag baselines** — PRD §4.3 already flags corrupted/incomplete rounds as "Casual Practice" to avoid polluting baselines; extend this thinking to ensure deleted-user data doesn't linger in aggregate baselines derived from their shots.

## Non-goals for this stub

This document does not attempt to write the actual public-facing privacy policy or terms of service — that requires legal review. It exists so the engineering work (deletion endpoints, retention jobs, export endpoints) has a checklist to build against ahead of that review.
