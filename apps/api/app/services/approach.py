"""Short-sided vs. safe-leave classification for missed-green approach shots
(PRD §5.2).

This is a distance/lie-based **proxy**, not true short-siding. Real
short-siding is about the shot's miss *angle* relative to that day's actual
pin position — missing long/left when the pin is back-right leaves plenty of
green to work with (safe leave); missing short/right of that same pin
leaves almost none (short-sided) — regardless of how far off the green you
are. Detecting that needs a per-round pin location and a green-boundary
containment/angle query, and this schema only stores a *static*
`Hole.green_center`/`green_boundary` (no per-round pin, since pins move
daily in real golf). That's Phase 4 (dispersion maps) territory — see
`docs/DEVELOPMENT_PLAN.md`.

Until then, `classify_approach_leave()` flags a shot that missed the green
and left a notably tight recovery distance as a *candidate* short-sided
miss, for the audit wizard to confirm — it is not asserting geometric fact.
"""

from enum import StrEnum

from app.models.shot import Lie, Shot

SHORT_SIDE_PROXIMITY_YARDS = 10.0

_OFF_GREEN_RECOVERY_LIES = {Lie.sand, Lie.rough, Lie.recovery, Lie.fringe}


class ApproachLeave(StrEnum):
    on_green = "on_green"
    short_sided = "short_sided"
    safe_leave = "safe_leave"
    unclassified = "unclassified"


def classify_approach_leave(shot: Shot) -> ApproachLeave:
    if shot.end_lie == Lie.green:
        return ApproachLeave.on_green
    if shot.end_lie not in _OFF_GREEN_RECOVERY_LIES:
        return ApproachLeave.unclassified
    if shot.end_distance_yards <= SHORT_SIDE_PROXIMITY_YARDS:
        return ApproachLeave.short_sided
    return ApproachLeave.safe_leave
