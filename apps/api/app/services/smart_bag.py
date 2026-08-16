"""Smart Bag: per-club distance gapping with IQR-based outlier rejection
(PRD §5.3, §10 Phase 2).

The stats primitives here (`reject_outliers_iqr`, `compute_dispersion`)
operate on plain distance-sample lists, so the same engine can be fed from
either on-course GPS shot distances (`shot_carry_distance()` below, from
`Shot.start_distance_yards - end_distance_yards`) or R10/R50 launch monitor
carry/total numbers (Phase 1's `LaunchMonitorShot.carry_yards`) — both
reduce to "how far did this club hit it" samples.

Scope note: `ClubGappingStats.lateral` is wired up but nothing populates it
yet. PRD §5.3 wants lateral standard deviation per club, but that needs a
per-shot lateral-yards measurement (offset from a target line) that neither
data source captures today — on-course shots have a GPS point but no
target-line-relative offset, and the R10/R50 parser's fields don't include
one. That lands with Phase 4's dispersion-map work, which will have real
target lines to project against; this module is ready to accept
`lateral_by_club` samples the moment that exists.
"""

import statistics
from dataclasses import dataclass

import numpy as np

from app.services.shot_view import ShotView

DEFAULT_IQR_MULTIPLIER = 1.5
# Below this many samples, an IQR is too noisy to be a meaningful outlier
# fence, so every sample is kept as-is.
MIN_SAMPLES_FOR_IQR = 4

CLUB_ORDER = [
    "Driver", "3-Wood", "5-Wood", "7-Wood", "Hybrid",
    "2-Iron", "3-Iron", "4-Iron", "5-Iron", "6-Iron", "7-Iron", "8-Iron", "9-Iron",
    "PW", "GW", "AW", "SW", "LW", "Putter",
]
_CLUB_RANK = {club: i for i, club in enumerate(CLUB_ORDER)}


def reject_outliers_iqr(samples: list[float], k: float = DEFAULT_IQR_MULTIPLIER) -> list[float]:
    """Tukey's IQR rule: drop samples outside [Q1 - k*IQR, Q3 + k*IQR]."""
    if len(samples) < MIN_SAMPLES_FOR_IQR:
        return list(samples)
    arr = np.asarray(samples, dtype=float)
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    lower, upper = q1 - k * iqr, q3 + k * iqr
    return [float(x) for x in arr if lower <= x <= upper]


@dataclass(frozen=True)
class DispersionStats:
    count: int
    mean: float
    median: float
    stdev: float
    excluded_outliers: int


def compute_dispersion(samples: list[float], k: float = DEFAULT_IQR_MULTIPLIER) -> DispersionStats:
    if not samples:
        return DispersionStats(count=0, mean=0.0, median=0.0, stdev=0.0, excluded_outliers=0)

    filtered = reject_outliers_iqr(samples, k=k)
    return DispersionStats(
        count=len(filtered),
        mean=statistics.fmean(filtered),
        median=statistics.median(filtered),
        stdev=statistics.pstdev(filtered) if len(filtered) > 1 else 0.0,
        excluded_outliers=len(samples) - len(filtered),
    )


@dataclass(frozen=True)
class ClubGappingStats:
    club: str
    carry: DispersionStats
    lateral: DispersionStats | None = None


def compute_club_gapping(
    distances_by_club: dict[str, list[float]],
    lateral_by_club: dict[str, list[float]] | None = None,
    k: float = DEFAULT_IQR_MULTIPLIER,
) -> list[ClubGappingStats]:
    lateral_by_club = lateral_by_club or {}
    return [
        ClubGappingStats(
            club=club,
            carry=compute_dispersion(distances, k=k),
            lateral=(
                compute_dispersion(lateral_by_club[club], k=k) if club in lateral_by_club else None
            ),
        )
        for club, distances in distances_by_club.items()
    ]


def sort_by_club_order(stats: list[ClubGappingStats]) -> list[ClubGappingStats]:
    """Clubs not in `CLUB_ORDER` (custom/unrecognized names) sort last, in
    their original relative order."""
    return sorted(stats, key=lambda s: _CLUB_RANK.get(s.club, len(CLUB_ORDER)))


@dataclass(frozen=True)
class ClubGap:
    longer_club: str
    shorter_club: str
    carry_gap_yards: float


def compute_gaps(stats: list[ClubGappingStats]) -> list[ClubGap]:
    """Consecutive-club carry gaps, in bag order, for clubs with at least
    one surviving sample. Skips clubs `CLUB_ORDER` doesn't recognize —
    their relative distance ordering isn't knowable."""
    ordered = [s for s in sort_by_club_order(stats) if s.club in _CLUB_RANK and s.carry.count > 0]
    return [
        ClubGap(
            longer_club=longer.club,
            shorter_club=shorter.club,
            carry_gap_yards=round(longer.carry.mean - shorter.carry.mean, 1),
        )
        for longer, shorter in zip(ordered, ordered[1:], strict=False)
    ]


def shot_carry_distance(shot: ShotView) -> float | None:
    """Approximate on-course "carry" for a full-swing shot as the GPS
    distance closed: start_distance - end_distance. Not meaningful for
    putts (no club, or club == "Putter") — those don't measure a carry."""
    if not shot.club or shot.club == "Putter":
        return None
    return shot.start_distance_yards - shot.end_distance_yards
