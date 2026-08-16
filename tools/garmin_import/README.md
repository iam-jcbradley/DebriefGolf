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
- **The scorecard endpoints' JSON shape is now verified** — a real,
  sanitized sample of Garmin's raw `gcs-golfcommunity/api/v2/scorecard/
  {summary,detail}` REST responses (fetched via a browser-session-cookie
  userscript, not this tool) confirmed the field names `scorecard_mapper.py`
  relies on. `get_golf_shot_data` (per-shot telemetry) is still fully
  unverified — no sample of it, from any source, has been seen here. See
  `garmin_client.py`'s module docstring for the precise verification
  boundary, including the one hop (the `garminconnect` package's own
  wrapper methods vs. the raw REST API) that's still unconfirmed.
- **Scorecard data is not shot data.** Garmin's golf scorecard is what you
  tap into the Garmin Golf app as you play: per-hole strokes, fairways/GIR/
  putts, and course/tee metadata. There's no per-shot GPS, club, or lie in
  it anywhere (only a pin location per hole) — `import-scorecard` below can
  only ever populate score and course info, never `Shot` rows.
- The `.FIT` download path is the one piece of this with a fully-verified
  destination: it produces a real, standard `.FIT` file that DebriefGolf's
  existing upload endpoint already parses, and it's the only source of
  actual shot-level data (GPS, distances) this tool can get into DebriefGolf.

## Setup

```bash
cd tools/garmin_import
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GARMIN_EMAIL/PASSWORD and DEBRIEFGOLF_EMAIL/PASSWORD
```

`DEBRIEFGOLF_EMAIL`/`DEBRIEFGOLF_PASSWORD` must be a real DebriefGolf
account (create one via the web app, or `POST /api/auth/register`) — `upload`
and `import-scorecard` log in with it to get a session cookie, since identity
there comes from the cookie rather than a user-id parameter.

## Usage

```bash
python main.py status                    # test login, show token cache status
python main.py list --limit 10           # recent scorecard summaries
python main.py export <scorecard_id>     # full scorecard detail -> output/scorecard_<id>.json
python main.py shots <scorecard_id>      # shot-by-shot data -> output/shots_<id>.json
python main.py download-fit <activity_id>  # raw .FIT -> output/<activity_id>.fit

# Bridge into DebriefGolf: uploads a downloaded .FIT through the app's
# already-built, already-tested ingestion endpoint (POST /api/rounds/upload).
python main.py upload output/<activity_id>.fit --api-url http://localhost:8000

# Score + course only (no shots): creates/reuses a Course and creates a
# Round via POST /api/courses + POST /api/rounds, from the scorecard JSON.
python main.py import-scorecard <scorecard_id> --api-url http://localhost:8000
```

The first login prompts for a 2FA/MFA code if your account has it enabled.
After that, session tokens are cached in `.garmin_tokens/` — subsequent
runs resume from there instead of logging in again, until the session
expires.

## What actually plugs into DebriefGolf right now

- **`.FIT` files** (`download-fit` → `upload`): fully wired, and the only
  path that gets shot-level data (GPS, distances) into DebriefGolf. Reuses
  `POST /api/rounds/upload`, the same endpoint the web app's drag-and-drop
  uploader calls.
- **Scorecard JSON** (`import-scorecard`): wired, using the now-verified
  scorecard shape (`scorecard_mapper.py`). Creates a `Course` (par per hole,
  name/city/state — no yardage, Garmin's scorecard doesn't have it) and a
  `Round` (score, played-at date), always `needs_audit` since there are no
  shots and no real yardages yet. Course lookup is by exact name match
  (`GET /courses?q=...`) to avoid duplicating a course across imports —
  DebriefGolf's own de-dup is only by `osm_relation_id`, which a
  Garmin-sourced course doesn't have.
- **Raw scorecard/shot JSON** (`export`/`shots`): still exports to local
  files only. `shots` (`get_golf_shot_data`) has no verified shape and
  isn't mapped into anything — see the caveats above.
