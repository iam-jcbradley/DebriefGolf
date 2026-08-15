"""Flat-earth projection helpers for hole geometry (PRD §5.3, §10 Phase 4).

Golf holes span at most a few hundred yards, so a flat-earth (equirectangular)
approximation is accurate to a fraction of an inch over the whole hole —
nowhere near enough curvature to matter, and far simpler than a proper
geodesic library. This mirrors the same approximation `app/db/seed.py` uses
to generate demo course geometry, so demo data and this math agree.

The main thing this unlocks: Smart Bag's lateral dispersion (PRD §5.3) had
no data source as of Phase 2 (`app/services/smart_bag.py`'s docstring) — a
shot's GPS point relative to the hole's tee->green aim line is exactly that
data source, and both already exist in the schema (`Hole.tee_location`,
`Hole.green_center`, `Shot.location`).
"""

import math
from dataclasses import dataclass

# Matches app/db/seed.py's approximation: yards per degree of latitude is
# effectively constant; yards per degree of longitude shrinks by cos(lat).
YARDS_PER_DEGREE_LAT = 121_000.0


@dataclass(frozen=True)
class LatLng:
    lat: float
    lng: float


def local_yards(origin: LatLng, point: LatLng) -> tuple[float, float]:
    """`point`'s offset from `origin` in local flat-earth yards, as
    `(east_yards, north_yards)`."""
    north = (point.lat - origin.lat) * YARDS_PER_DEGREE_LAT
    east = (point.lng - origin.lng) * YARDS_PER_DEGREE_LAT * math.cos(math.radians(origin.lat))
    return east, north


@dataclass(frozen=True)
class AimLineOffset:
    # Distance from the tee toward the green, along the aim line (yards).
    # Negative means behind the tee.
    longitudinal_yards: float
    # Perpendicular distance from the aim line (yards). Positive = right of
    # the tee->green direction, negative = left.
    lateral_yards: float


@dataclass(frozen=True)
class ShotGeometryRow:
    """One shot's raw lat/lng plus its hole's tee/green lat/lng — the shape
    `app/api/routes/bag.py` pulls out of a `ST_X`/`ST_Y` query, kept
    DB-agnostic here so the aggregation logic is unit-testable without one."""

    club: str
    shot_lat: float
    shot_lng: float
    tee_lat: float
    tee_lng: float
    green_lat: float
    green_lng: float


def compute_lateral_by_club(rows: list[ShotGeometryRow]) -> dict[str, list[float]]:
    """Groups lateral aim-line offsets by club, skipping any hole whose
    tee/green coincide (no aim line to project onto — shouldn't happen with
    real course data, but a degenerate hole shouldn't take down the whole
    Smart Bag response)."""
    lateral_by_club: dict[str, list[float]] = {}
    for row in rows:
        tee = LatLng(row.tee_lat, row.tee_lng)
        green = LatLng(row.green_lat, row.green_lng)
        shot_point = LatLng(row.shot_lat, row.shot_lng)
        try:
            offset = offset_from_aim_line(tee, green, shot_point)
        except ValueError:
            continue
        lateral_by_club.setdefault(row.club, []).append(offset.lateral_yards)
    return lateral_by_club


def offset_from_aim_line(tee: LatLng, green: LatLng, point: LatLng) -> AimLineOffset:
    """Decomposes `point` into components along and across the tee->green
    aim line, both in yards."""
    aim_east, aim_north = local_yards(tee, green)
    aim_length = math.hypot(aim_east, aim_north)
    if aim_length == 0:
        raise ValueError("tee and green coincide — no aim line to project onto")

    aim_unit = (aim_east / aim_length, aim_north / aim_length)
    # 90° clockwise from the aim direction = "right" when facing the green.
    perp_unit = (aim_unit[1], -aim_unit[0])

    point_east, point_north = local_yards(tee, point)
    longitudinal = point_east * aim_unit[0] + point_north * aim_unit[1]
    lateral = point_east * perp_unit[0] + point_north * perp_unit[1]

    return AimLineOffset(longitudinal_yards=longitudinal, lateral_yards=lateral)
