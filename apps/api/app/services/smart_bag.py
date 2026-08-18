"""Smart Bag: per-club distance gapping with IQR-based outlier rejection
(PRD §5.3, §10 Phase 2).

`reject_outliers_iqr` and `compute_dispersion` are the stats primitives:
Tukey's IQR fence, then count/mean/median/stdev over the survivors. Until
Phase 16, on-course carry samples reached them by walking every `Shot` a
player ever recorded in Python (`Shot.start_distance_yards -
end_distance_yards`, filtered to full-swing shots) before calling
`compute_dispersion` per club. That walk is gone: `GET /bag` and
`GET /practice/delivery` now get carry dispersion pre-computed from
`app/api/routes/_shot_queries.py`'s `club_carry_dispersion_sql`, which
reproduces the same fence and aggregation as a single SQL query (verified
to agree with these Python functions in `tests/test_shot_queries.py`), and
hand it to `build_club_gapping` below rather than `compute_dispersion`
directly. `reject_outliers_iqr`/`compute_dispersion` remain the primitives
lateral dispersion still uses (see the scope note below) and the reference
implementation the SQL push-down is checked against.

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


def build_club_gapping(
    carry_by_club: dict[str, DispersionStats],
    lateral_by_club: dict[str, list[float]] | None = None,
    k: float = DEFAULT_IQR_MULTIPLIER,
) -> list[ClubGappingStats]:
    """Pairs each club's carry dispersion (already computed — by
    `app/api/routes/_shot_queries.py`'s SQL push-down, in every current
    caller) with its lateral dispersion. Lateral still goes through
    `compute_dispersion` here: it isn't pushed into SQL (see this module's
    docstring for why), so it still arrives as raw samples."""
    lateral_by_club = lateral_by_club or {}
    return [
        ClubGappingStats(
            club=club,
            carry=carry,
            lateral=(
                compute_dispersion(lateral_by_club[club], k=k) if club in lateral_by_club else None
            ),
        )
        for club, carry in carry_by_club.items()
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
