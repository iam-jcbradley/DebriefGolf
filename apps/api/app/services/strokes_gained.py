"""Strokes Gained engine (PRD §5.1, §10 Phase 2).

`SG = Benchmark(start_lie, start_distance) - Benchmark(end_lie, end_distance) - 1`,
computed per shot via `app.services.benchmarks.expected_strokes()` and rolled
up into the OTT / APP / ARG / PUTT categories used throughout the PRD's UI
(§8 Round Snapshot).

A useful invariant this formula guarantees for free: summed across a
sequence of shots where each shot's end (lie, distance) is the next shot's
start (lie, distance) — i.e. any real chain of shots on a hole — the
per-shot terms telescope to
`Benchmark(first start) - Benchmark(last end) - total_strokes_taken`,
regardless of how any individual (lie, distance) pair is benchmarked. See
`tests/test_strokes_gained.py::test_sg_telescopes_across_a_hole`.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.models.benchmark import HANDICAP_BUCKETS
from app.models.shot import Lie, Shot
from app.services.benchmarks import expected_strokes

# Broadie's conventional Around-the-Green / Approach split.
ARG_THRESHOLD_YARDS = 30.0


class SGCategory(StrEnum):
    ott = "OTT"
    app = "APP"
    arg = "ARG"
    putt = "PUTT"


def nearest_handicap_bucket(handicap_index: float) -> int:
    """Round a continuous handicap index to the nearest seeded bucket
    (0, 5, 10, 15, 20, 25 — PRD §5.1)."""
    return min(HANDICAP_BUCKETS, key=lambda bucket: abs(bucket - handicap_index))


def categorize_shot(shot: Shot, hole_par: int) -> SGCategory:
    """Classify a shot into SG:OTT / APP / ARG / PUTT.

    - A putter (from any lie — the fringe/green "Texas wedge" case included)
      is always PUTT.
    - A tee shot on a par 4/5 is OTT; a par-3 tee shot is folded into
      APP/ARG by distance instead, matching the standard Strokes Gained
      convention that SG:OTT only covers driving holes.
    - Everything else is split on the classic ~30y Around-the-Green cutoff.
    """
    if shot.club == "Putter":
        return SGCategory.putt
    if shot.start_lie == Lie.green:
        return SGCategory.putt
    if shot.start_lie == Lie.tee and hole_par != 3:
        return SGCategory.ott
    if shot.start_distance_yards <= ARG_THRESHOLD_YARDS:
        return SGCategory.arg
    return SGCategory.app


def strokes_gained_for_shot(shot: Shot, handicap_bucket: int) -> float:
    start = expected_strokes(handicap_bucket, shot.start_lie, shot.start_distance_yards)
    end = expected_strokes(handicap_bucket, shot.end_lie, shot.end_distance_yards)
    return start - end - 1


@dataclass(frozen=True)
class ShotStrokesGained:
    shot_id: int | None
    category: SGCategory
    strokes_gained: float


@dataclass(frozen=True)
class RoundStrokesGainedSummary:
    handicap_bucket: int
    total: float
    by_category: dict[SGCategory, float]
    shots: list[ShotStrokesGained]


def compute_round_strokes_gained(
    shots_with_par: list[tuple[Shot, int]], handicap_index: float
) -> RoundStrokesGainedSummary:
    """`shots_with_par`: each shot paired with the par of the hole it was
    played on (needed for the par-3-tee-shot OTT/APP exception)."""
    bucket = nearest_handicap_bucket(handicap_index)
    by_category: dict[SGCategory, float] = dict.fromkeys(SGCategory, 0.0)
    results: list[ShotStrokesGained] = []

    for shot, hole_par in shots_with_par:
        category = categorize_shot(shot, hole_par)
        sg = strokes_gained_for_shot(shot, bucket)
        by_category[category] += sg
        results.append(ShotStrokesGained(shot_id=shot.id, category=category, strokes_gained=sg))

    return RoundStrokesGainedSummary(
        handicap_bucket=bucket,
        total=sum(by_category.values()),
        by_category=by_category,
        shots=results,
    )
