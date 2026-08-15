# Garmin import (personal use)

Pulls your own golf data out of Garmin Connect using the same consumer
login the Garmin Connect app/website uses — **not** Garmin's official
Health/Developer API, which requires a paid developer account (see
[`docs/DEVELOPMENT_PLAN.md`](../../docs/DEVELOPMENT_PLAN.md) Phase 5 for
why that pivot happened). This is a personal-use automation tool, not a
DebriefGolf backend feature: it runs entirely on your machine, and your
Garmin credentials never touch the DebriefGolf API or database.

## Before you use this

- **Almost certainly outside Garmin's Terms of Service.** This is the same
  category of tool as many personal Strava-sync/analytics scripts —
  widely used for personal data export, not sanctioned or supported by
  Garmin. Use your own account and your own data; don't run it often
  enough to look like abuse (Garmin can and does rate-limit or lock
  accounts that authenticate unusually).
- **Fragile by nature.** Garmin can change their login flow or add
  stronger bot detection at any time, with no notice, and this tool has
  no way to anticipate that.
- **The golf-specific endpoints' exact JSON shape is unverified.** The
  *method signatures* below (`get_golf_summary`, `get_golf_scorecard`,
  `get_golf_shot_data`) are real, taken from the installed
  `garminconnect` package's source — but nobody has run this against a
  live account from this codebase, so the actual field names inside each
  response are provisional. `export`/`shots` just dump whatever comes
  back to a JSON file; there's no DebriefGolf schema mapper yet (see
  "Next step" below).
- The `.FIT` download path is the one piece of this with a fully-verified
  destination: it produces a real, standard `.FIT` file that DebriefGolf's
  existing upload endpoint already parses.

## Setup

```bash
cd tools/garmin_import
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GARMIN_EMAIL / GARMIN_PASSWORD
```

## Usage

```bash
python main.py status                    # test login, show token cache status
python main.py list --limit 10           # recent scorecard summaries
python main.py export <scorecard_id>     # full scorecard detail -> output/scorecard_<id>.json
python main.py shots <scorecard_id>      # shot-by-shot data -> output/shots_<id>.json
python main.py download-fit <activity_id>  # raw .FIT -> output/<activity_id>.fit

# Bridge into DebriefGolf: uploads a downloaded .FIT through the app's
# already-built, already-tested ingestion endpoint (POST /api/rounds/upload).
python main.py upload output/<activity_id>.fit --user-id 1 --api-url http://localhost:8000
```

The first login prompts for a 2FA/MFA code if your account has it enabled.
After that, session tokens are cached in `.garmin_tokens/` — subsequent
runs resume from there instead of logging in again, until the session
expires.

## What actually plugs into DebriefGolf right now

- **`.FIT` files** (`download-fit` → `upload`): fully wired. This reuses
  `POST /api/rounds/upload`, the same endpoint the web app's drag-and-drop
  uploader calls — real, tested, no guessing involved.
- **Scorecard/shot JSON** (`export`/`shots`): exports to local files only.
  Building an automatic mapper into DebriefGolf's `Course`/`Round`/`Shot`
  schema needs a real sample payload to get field names right — guessing
  at an undocumented, reverse-engineered API's shape and shipping it as if
  tested would be worse than not having it. **Next step:** run `export`
  and `shots` against a real scorecard, then use a sanitized sample to
  build that mapper for real.
