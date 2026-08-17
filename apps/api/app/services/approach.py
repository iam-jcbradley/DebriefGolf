"""Short-sided vs. safe-leave classification for missed-green approach shots
(PRD §5.2, §10 Phase 14).

Two classification methods, chosen per-shot depending on what's available:

**Geometric** (Phase 14): real short-siding is about the shot's miss angle
relative to that day's actual pin, not just how far away it ended up. A
miss on the pin's side of the green, where little green lies between ball
and hole, is short-sided regardless of exact distance; the same distance on
the opposite side, with the whole green to work with, is a safe leave.
Needs three things this schema didn't have before Phase 14: a per-round pin
(`RoundHolePin` — pins move daily in real golf, so `Hole.green_center` alone
was never going to be enough), the hole's green boundary polygon, and the
shot's own GPS location.

**Proxy** (Phases 2-13): whenever any of those three is missing — no pin
recorded this round, the course has no green boundary on file (OSM coverage
is inconsistent, see `osm_courses.py`), or this particular shot has no GPS
point — classification falls back to the original distance/lie heuristic.
Not an error case: most rounds in this database predate Phase 14 and will
use this path indefinitely unless someone goes back and adds a pin.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.models.shot import Lie, Shot
from app.services.geometry import LatLng, green_extent_beyond_point, offset_from_aim_line

SHORT_SIDE_PROXIMITY_YARDS = 10.0

# Calibration, not validated golf-instruction data — same caveat this
# codebase already carries for SCRATCH_CURVES (app/services/benchmarks.py)
# and EXPECTED_SMASH_FACTOR_BY_IRON (app/services/practice_combines.py). A
# miss counts as short-sided when the green available on its side of the
# pin is less than this fraction of what's available on the opposite side.
SHORT_SIDE_GREEN_RATIO = 0.5

_OFF_GREEN_RECOVERY_LIES = {Lie.sand, Lie.rough, Lie.recovery, Lie.fringe}


class ApproachLeave(StrEnum):
    on_green = "on_green"
    short_sided = "short_sided"
    safe_leave = "safe_leave"
    unclassified = "unclassified"


@dataclass(frozen=True)
class HoleGeometryContext:
    """What `classify_approach_leave` needs to attempt the real geometric
    rule. Every field optional — missing any of it (no pin, no green
    boundary) falls back to the proxy, not an error. Callers build this
    from raw-column queries (`ST_Y`/`ST_X`), never from `Hole`/`RoundHolePin`
    ORM objects directly — those hand back non-JSON-serializable
    `WKBElement`s, and this module stays free of any database session either
    way (`app/services/README.md`)."""

    tee: LatLng | None = None
    green_center: LatLng | None = None
    green_boundary: list[LatLng] | None = None
    pin: LatLng | None = None


def classify_approach_leave(
    shot: Shot,
    shot_location: LatLng | None = None,
    geometry: HoleGeometryContext | None = None,
) -> ApproachLeave:
    if shot.end_lie == Lie.green:
        return ApproachLeave.on_green
    if shot.end_lie not in _OFF_GREEN_RECOVERY_LIES:
        return ApproachLeave.unclassified

    geometric = (
        _classify_geometrically(shot_location, geometry)
        if shot_location is not None and geometry is not None
        else None
    )
    if geometric is not None:
        return geometric

    if shot.end_distance_yards <= SHORT_SIDE_PROXIMITY_YARDS:
        return ApproachLeave.short_sided
    return ApproachLeave.safe_leave


def _classify_geometrically(
    miss: LatLng, geometry: HoleGeometryContext
) -> ApproachLeave | None:
    """`None` means "can't attempt this" — caller falls back to the proxy.
    Distinct from returning a real verdict; a degenerate green shape (e.g.
    no green on either side of the pin, which shouldn't happen with real
    OSM data but isn't worth crashing over) is also a `None`, not a
    guess."""
    if geometry.tee is None or geometry.green_center is None or geometry.pin is None:
        return None
    if not geometry.green_boundary:
        return None

    try:
        miss_lateral = offset_from_aim_line(geometry.tee, geometry.green_center, miss).lateral_yards
        pin_lateral = offset_from_aim_line(
            geometry.tee, geometry.green_center, geometry.pin
        ).lateral_yards
        extent_right, extent_left = green_extent_beyond_point(
            geometry.green_boundary, geometry.tee, geometry.green_center, geometry.pin
        )
    except ValueError:
        # Tee and green coincide — degenerate hole geometry, not this
        # function's job to fix. Same "skip, don't crash the batch" choice
        # geometry.py's own compute_lateral_by_club already makes.
        return None

    miss_is_right = miss_lateral >= pin_lateral
    extent_toward_miss = extent_right if miss_is_right else extent_left
    extent_away_from_miss = extent_left if miss_is_right else extent_right

    if extent_away_from_miss <= 0:
        return None

    if extent_toward_miss < SHORT_SIDE_GREEN_RATIO * extent_away_from_miss:
        return ApproachLeave.short_sided
    return ApproachLeave.safe_leave
