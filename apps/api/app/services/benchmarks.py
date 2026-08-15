"""Strokes Gained benchmark curves: "expected strokes to hole out" from a given
lie and distance, split by handicap bucket (PRD §5.1, §10 Phase 1).

This is a hand-authored *approximation* of the shape of Mark Broadie's published
Strokes Gained baseline tables (Every Shot Counts) — internally consistent and
monotonic, but not a transcription of licensed PGA Tour/Arccos data. Swap
`SCRATCH_CURVES` for licensed figures before this feeds anything user-facing.

Only a scratch (0-handicap) curve is authored per lie. Other handicap buckets
are derived by scaling the "extra strokes above the guaranteed final stroke"
by a per-bucket factor (`HANDICAP_FACTORS`) — full-swing lies scale more with
handicap than short-game lies, matching the general pattern that skill gaps
show up more off the tee/approach than on short putts.

The Phase 2 Strokes Gained engine computes
`SG = expected_strokes(bucket, start_lie, start_dist) -
      expected_strokes(bucket, end_lie, end_dist) - 1`
using `expected_strokes()` below.
"""

from app.models.benchmark import HANDICAP_BUCKETS
from app.models.shot import Lie

# (distance_yards, scratch_expected_strokes_to_hole_out), sorted ascending by distance.
SCRATCH_CURVES: dict[Lie, list[tuple[float, float]]] = {
    Lie.tee: [
        (50, 2.35), (75, 2.45), (100, 2.55), (125, 2.65), (150, 2.72), (175, 2.80),
        (200, 2.92), (225, 3.05), (250, 3.20), (275, 3.45), (300, 3.65), (325, 3.85),
        (350, 3.95), (375, 4.05), (400, 4.15), (425, 4.25), (450, 4.35), (475, 4.45),
        (500, 4.55), (550, 4.75), (600, 4.95),
    ],
    Lie.fairway: [
        (10, 2.25), (20, 2.40), (30, 2.48), (50, 2.58), (75, 2.66), (100, 2.71),
        (125, 2.76), (150, 2.80), (175, 2.87), (200, 2.98), (225, 3.12), (250, 3.28),
    ],
    Lie.rough: [
        (10, 2.38), (20, 2.55), (30, 2.63), (50, 2.72), (75, 2.80), (100, 2.85),
        (125, 2.90), (150, 2.95), (175, 3.02), (200, 3.13), (225, 3.27), (250, 3.42),
    ],
    Lie.sand: [
        (5, 2.55), (10, 2.62), (20, 2.72), (30, 2.80), (50, 2.90), (75, 3.00), (100, 3.15),
    ],
    Lie.recovery: [
        (5, 2.70), (10, 2.80), (20, 2.92), (30, 3.02), (50, 3.15), (75, 3.28),
        (100, 3.42), (150, 3.70),
    ],
    Lie.green: [
        (0.33, 1.001), (0.67, 1.01), (1.0, 1.04), (1.67, 1.10), (2.0, 1.14), (3.0, 1.26),
        (4.0, 1.37), (5.0, 1.47), (7.0, 1.61), (10.0, 1.75), (13.3, 1.83), (16.7, 1.89),
        (20.0, 1.93), (26.7, 2.01), (33.3, 2.08),
    ],
    Lie.fringe: [
        (0.5, 1.15), (1.0, 1.22), (2.0, 1.35), (3.0, 1.45), (5.0, 1.58),
        (7.0, 1.68), (10.0, 1.78), (15.0, 1.90),
    ],
}

_FULL_SWING_LIES = {Lie.tee, Lie.fairway, Lie.rough, Lie.sand, Lie.recovery}
_SHORT_GAME_LIES = {Lie.green, Lie.fringe}

HANDICAP_FACTORS: dict[int, dict[str, float]] = {
    0: {"full_swing": 1.00, "short_game": 1.00},
    5: {"full_swing": 1.07, "short_game": 1.04},
    10: {"full_swing": 1.15, "short_game": 1.08},
    15: {"full_swing": 1.24, "short_game": 1.13},
    20: {"full_swing": 1.34, "short_game": 1.18},
    25: {"full_swing": 1.45, "short_game": 1.24},
}

assert set(HANDICAP_FACTORS) == set(HANDICAP_BUCKETS)


def _category(lie: Lie) -> str:
    if lie in _FULL_SWING_LIES:
        return "full_swing"
    if lie in _SHORT_GAME_LIES:
        return "short_game"
    raise ValueError(f"No strokes-gained benchmark category for lie={lie!r}")


def _interpolate(curve: list[tuple[float, float]], distance_yards: float) -> float:
    if distance_yards <= curve[0][0]:
        return curve[0][1]
    if distance_yards >= curve[-1][0]:
        return curve[-1][1]
    for (d0, s0), (d1, s1) in zip(curve, curve[1:], strict=False):
        if d0 <= distance_yards <= d1:
            fraction = (distance_yards - d0) / (d1 - d0)
            return s0 + fraction * (s1 - s0)
    raise AssertionError("unreachable: curve is sorted and bounds are checked above")


def expected_strokes(handicap_bucket: int, lie: Lie, distance_yards: float) -> float:
    """Expected number of strokes to hole out from `lie` at `distance_yards`,
    for a golfer of the given `handicap_bucket` (must be one of `HANDICAP_BUCKETS`).

    Interpolates linearly between the nearest seeded distance points for that
    lie, clamping to the curve's endpoints outside its authored range.
    """
    if distance_yards < 0:
        raise ValueError("distance_yards must be >= 0")
    if distance_yards == 0:
        return 0.0
    if handicap_bucket not in HANDICAP_FACTORS:
        raise ValueError(
            f"handicap_bucket must be one of {HANDICAP_BUCKETS}, got {handicap_bucket}"
        )
    if lie not in SCRATCH_CURVES:
        raise ValueError(f"No strokes-gained benchmark curve defined for lie={lie!r}")

    scratch = _interpolate(SCRATCH_CURVES[lie], distance_yards)
    factor = HANDICAP_FACTORS[handicap_bucket][_category(lie)]
    return 1 + (scratch - 1) * factor


def generate_benchmark_rows() -> list[dict]:
    """One row per (handicap bucket, lie, seeded distance point) — the full
    cross product used to populate `strokes_gained_benchmark` (see `make seed`).
    """
    return [
        dict(
            handicap_bucket=bucket,
            lie=lie,
            distance_yards=distance,
            expected_strokes=expected_strokes(bucket, lie, distance),
        )
        for bucket in HANDICAP_BUCKETS
        for lie, curve in SCRATCH_CURVES.items()
        for distance, _ in curve
    ]
