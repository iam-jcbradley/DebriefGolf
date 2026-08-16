"""Garmin Connect data export (personal-use, reverse-engineered SSO — not
the official Garmin Health API, which requires a paid developer account;
see docs/DEVELOPMENT_PLAN.md Phase 5). Runs entirely on your own machine:
your Garmin email/password are used once to establish a session, then only
the resulting session tokens are cached locally in `.garmin_tokens/` —
nothing here ever sends your Garmin credentials to the DebriefGolf backend
or database. That's a deliberate boundary, not an oversight: it keeps
docs/DATA_PRIVACY.md's "third-party OAuth data" framing accurate rather
than silently expanding what this app touches.

Built against `garminconnect==0.3.5`'s actual installed source (inspected
directly, not just its README) since this whole integration is
reverse-engineered and undocumented by Garmin itself:
- `Garmin(email, password, return_on_mfa=True)` constructs a client.
- `.login(tokenstore=path)` loads cached tokens from `path` first,
  falling back to a real credential login and caching the result there —
  no separate "resume from cache" call needed.
- MFA: `.login()` returns `("needs_mfa", None)` when the account has 2FA
  enabled; complete it with `.resume_login({}, code)` (the first argument
  is unused by this version — kept only for API-shape compatibility, see
  `garminconnect/client.py`'s `resume_login`), then persist tokens with
  the low-level client's own `.dump(path)`.
- Golf-specific endpoints (`get_golf_summary`/`get_golf_scorecard`/
  `get_golf_shot_data`) are themselves reverse-engineered by
  garminconnect's maintainers, not documented by Garmin — their *method
  signatures* are verified against the installed package. Their response
  *shape* is only partly verified, and by a different route than this
  tool's own code: a real, sanitized sample of the raw REST responses
  (fetched by a browser-session-cookie userscript hitting
  `https://connect.garmin.com/modern/proxy/gcs-golfcommunity/api/v2/
  scorecard/summary` and `.../scorecard/detail?scorecard-ids=<id>` directly)
  confirms `get_golf_summary`'s and `get_golf_scorecard`'s *target API*
  returns `{scorecardSummaries: [...]}` and `{scorecardDetails: [{scorecard:
  {...}, scorecardStats: {...}}], courseSnapshots: [{...}]}` respectively —
  see `scorecard_mapper.py`, which maps that confirmed shape. Whether the
  `garminconnect` package's wrapper methods return that exact JSON
  byte-for-byte (rather than transforming it) is still unverified in this
  environment, since Garmin's SSO/Connect hosts are blocked by this
  sandbox's network policy (confirmed via its proxy status endpoint — same
  boundary as this project's Mapbox/OSM integrations); treat that one hop
  as high confidence, not proven. `get_golf_shot_data`'s response shape
  remains fully provisional — no sample of it, verified or otherwise, has
  been seen from this codebase.

Caveats worth knowing before relying on this:
- Almost certainly outside Garmin's Terms of Service for automated
  access — this is the same category of tool as many personal
  Strava-sync/analytics scripts, not something Garmin provides or
  supports. Use your own account, your own data, at your own risk; don't
  run it aggressively enough to look like abuse.
- Fragile by nature: Garmin can change their web login flow, add stronger
  bot detection, or rate-limit/lock an account that authenticates
  unusually often, none of which this tool can anticipate or work around.
- `garth` (the library this ecosystem used to depend on) is deprecated;
  garminconnect no longer requires it, which is why it's not in
  requirements.txt despite being mentioned in earlier drafts of this idea.
- Pinned to `0.3.5`, not `0.3.2`, specifically for a security fix
  (PYSEC-2026-3467, CWE-732): versions up to 0.3.4 wrote the token store to
  disk with whatever the process umask allowed, so `.garmin_tokens/` could
  end up world-readable (containing a live Garmin refresh token) on a
  shared host. Re-verified against the 0.3.5 installed source before
  bumping — every method this module calls (`login`, `resume_login`,
  `get_golf_summary`, `get_golf_scorecard`, `get_golf_shot_data`,
  `get_activities`, `download_activity`, `client.dump`) has the identical
  signature it had at 0.3.2, and the full mocked test suite still passes.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)


class GarminImportError(Exception):
    pass


class MfaRequiredError(GarminImportError):
    """The account needs a 2FA/MFA code to finish logging in. Call
    `GarminImportClient.resume_mfa(code)` with the code Garmin sent you,
    then retry whatever you were doing."""


class GarminImportClient:
    """Thin wrapper around `garminconnect.Garmin` scoped to what
    DebriefGolf's manual-entry workflow needs: log in (with token caching
    and MFA support), list/export golf scorecards and shot data, and
    download a `.FIT` file for an activity."""

    def __init__(self, email: str, password: str, tokenstore: str | Path) -> None:
        self.tokenstore = str(tokenstore)
        self._garmin = Garmin(email=email, password=password, return_on_mfa=True)
        self._logged_in = False

    def login(self) -> None:
        """Logs in, resuming from cached tokens in `tokenstore` when
        possible (skipping a fresh SSO round trip entirely). Raises
        `MfaRequiredError` if the account needs a 2FA code — call
        `resume_mfa(code)` to finish."""
        try:
            needs_mfa, _ = self._garmin.login(tokenstore=self.tokenstore)
        except GarminConnectAuthenticationError as exc:
            raise GarminImportError(
                f"Authentication failed — check GARMIN_EMAIL/GARMIN_PASSWORD: {exc}"
            ) from exc
        except GarminConnectConnectionError as exc:
            raise GarminImportError(f"Could not reach Garmin: {exc}") from exc
        except GarminConnectTooManyRequestsError as exc:
            raise GarminImportError(
                f"Rate limited by Garmin — wait before retrying: {exc}"
            ) from exc

        if needs_mfa == "needs_mfa":
            raise MfaRequiredError()
        self._logged_in = True

    def resume_mfa(self, mfa_code: str) -> None:
        """Completes a login that raised `MfaRequiredError`."""
        self._garmin.resume_login({}, mfa_code)
        # Mirrors what a clean (non-MFA) login does internally — cache
        # tokens now that the session is actually established, so the
        # next run can skip both the password login and MFA.
        self._garmin.client.dump(self.tokenstore)
        self._logged_in = True

    def _require_login(self) -> None:
        if not self._logged_in:
            raise GarminImportError(
                "Not logged in — call login() (and resume_mfa() if needed) first."
            )

    def token_status(self) -> dict[str, Any]:
        """A lightweight status check — whether cached tokens exist on
        disk and whether this instance has completed a login — without
        forcing a fresh one."""
        return {
            "tokenstore": self.tokenstore,
            "tokenstore_exists": Path(self.tokenstore).exists(),
            "logged_in": self._logged_in,
            "display_name": getattr(self._garmin, "display_name", None),
        }

    def list_scorecards(self, limit: int = 20) -> list[dict[str, Any]]:
        """Recent golf scorecard summaries. Target API's shape is verified
        (module docstring); this wrapper method's own output isn't
        independently confirmed to match."""
        self._require_login()
        return self._garmin.get_golf_summary(start=0, limit=limit)

    def get_scorecard(self, scorecard_id: str) -> dict[str, Any]:
        """Full detail for one scorecard (per-hole scores, fairway
        hit/miss, putts — no club tracking or shot GPS, see module
        docstring). Target API's shape is verified; `scorecard_mapper.py`
        maps it into DebriefGolf's schema."""
        self._require_login()
        return self._garmin.get_golf_scorecard(scorecard_id)

    def get_shot_data(self, scorecard_id: str, hole_numbers: str | None = None) -> dict[str, Any]:
        """Shot-by-shot telemetry for a scorecard. Unverified response
        shape — this is the richest endpoint for DebriefGolf's purposes
        (real per-shot data) if its field names hold up under real use."""
        self._require_login()
        kwargs: dict[str, Any] = {}
        if hole_numbers:
            kwargs["hole_numbers"] = hole_numbers
        return self._garmin.get_golf_shot_data(scorecard_id, **kwargs)

    def list_golf_activities(self, limit: int = 20) -> list[dict[str, Any]]:
        """Activities Garmin tags as golf — range/R10 sessions, and full
        rounds if recorded as an activity rather than only a scorecard."""
        self._require_login()
        activities = self._garmin.get_activities(start=0, limit=limit, activitytype="golf")
        return activities if isinstance(activities, list) else activities.get("activities", [])

    def download_fit(self, activity_id: str, output_dir: str | Path) -> Path:
        """Downloads an activity's original export (a zip containing the
        real `.FIT` file) and extracts the `.FIT` into `output_dir`. The
        result is a real, standard `.FIT` file — hand it to DebriefGolf's
        existing `POST /api/rounds/upload` (see `main.py`'s `upload`
        command) exactly as if it came from a manual export."""
        self._require_login()
        raw = self._garmin.download_activity(
            activity_id, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL
        )
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(BytesIO(raw)) as zf:
            fit_names = [name for name in zf.namelist() if name.lower().endswith(".fit")]
            if not fit_names:
                raise GarminImportError(
                    f"Downloaded archive for activity {activity_id} has no .FIT file "
                    f"(contents: {zf.namelist()})"
                )
            data = zf.read(fit_names[0])

        out_path = output_dir / f"{activity_id}.fit"
        out_path.write_bytes(data)
        return out_path
