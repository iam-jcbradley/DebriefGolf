"""Maps a raw Garmin Connect scorecard `.../scorecard/detail` response into
DebriefGolf's `POST /courses` and `POST /rounds` request shapes.

The raw shape mapped here — top-level `scorecardDetails` (one entry with a
`scorecard` object) and `courseSnapshots` (one entry with `name`/`city`/
`state`/`holePars`) — is verified against a real, sanitized sample fetched
directly from `https://connect.garmin.com/modern/proxy/gcs-golfcommunity/
api/v2/scorecard/detail?scorecard-ids=<id>` via a browser-session-cookie
userscript (not this tool's own code path). `GarminImportClient.get_scorecard`
calls the same golf-community API through the `garminconnect` package's
`get_golf_scorecard` wrapper; whether that wrapper's return value is
byte-identical to the raw REST response above is not independently verified
in this environment (no live account to round-trip against — see
`garmin_client.py`'s module docstring), so treat that one hop as high
confidence rather than proven.

Notably absent from this payload: hole yardage, and anything shot-level
(club, GPS, lie). Garmin's golf scorecard is a strokes/par/handicap
record, not shot telemetry — that only comes from a `.FIT` file
(`download-fit` + `upload`). Every mapped hole gets `yardage=0` as a result,
and the mapped round is always `needs_audit` so a human fills in real
yardages (and, if they want shot-level data, pairs this round with an
uploaded `.FIT` for the same time) before it counts as verified.
"""

from __future__ import annotations

from typing import Any


class ScorecardMappingError(Exception):
    pass


def _scorecard(detail: dict[str, Any]) -> dict[str, Any]:
    entries = detail.get("scorecardDetails") or []
    if len(entries) != 1:
        raise ScorecardMappingError(
            f"Expected exactly one scorecardDetails entry, got {len(entries)}"
        )
    scorecard = entries[0].get("scorecard")
    if scorecard is None:
        raise ScorecardMappingError("scorecardDetails[0] has no 'scorecard' field")
    return scorecard


def _course_snapshot(detail: dict[str, Any]) -> dict[str, Any]:
    snapshots = detail.get("courseSnapshots") or []
    if len(snapshots) != 1:
        raise ScorecardMappingError(
            f"Expected exactly one courseSnapshots entry, got {len(snapshots)} — "
            "scorecards spanning two different course snapshots (e.g. a front "
            "nine and back nine recorded as separate courses) aren't supported."
        )
    return snapshots[0]


def _parse_hole_pars(hole_pars: str) -> list[int]:
    """Garmin encodes par-per-hole as one digit per hole (e.g. '445435354'
    for a 9-hole course) — confirmed by summing digits against
    frontNinePar/backNinePar/roundPar in a real sanitized sample."""
    if not hole_pars:
        raise ScorecardMappingError("Course snapshot has no 'holePars' field")
    return [int(ch) for ch in hole_pars]


def map_course_payload(detail: dict[str, Any]) -> dict[str, Any]:
    """Builds a `CourseCreateIn`-shaped payload for `POST /courses`."""
    snapshot = _course_snapshot(detail)
    if "name" not in snapshot:
        raise ScorecardMappingError("Course snapshot has no 'name' field")
    pars = _parse_hole_pars(snapshot.get("holePars", ""))
    return {
        "name": snapshot["name"],
        "city": snapshot.get("city"),
        "state": snapshot.get("state"),
        "holes": [{"number": i + 1, "par": par, "yardage": 0} for i, par in enumerate(pars)],
    }


def map_round_payload(detail: dict[str, Any], course_id: int) -> dict[str, Any]:
    """Builds a `RoundCreateIn`-shaped payload for `POST /rounds`."""
    scorecard = _scorecard(detail)
    if "startTime" not in scorecard:
        raise ScorecardMappingError("Scorecard has no 'startTime' field")
    return {
        "course_id": course_id,
        "played_at": scorecard["startTime"],
        "total_score": scorecard.get("strokes"),
        "status": "needs_audit",
    }
