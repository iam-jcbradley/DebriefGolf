"""Prescriptive practice combines (PRD §7.1, §10 Phase 6).

Maps a detected weakness signal to exactly the drill PRD §7.1's table pairs
it with — this is deliberately a fixed 1:1 mapping, not a generic "here's
what to work on" bucket, since the point of a *prescriptive* combine is that
it's the one drill shown to target the one weakness detected.

Each `detect_*` function is a pure function over numbers other services
already compute (round Strokes Gained, Smart Bag dispersion, R10/R50
delivery profile, putting mechanics) — this module doesn't touch the
database itself, matching the rest of app/services/.
"""

import statistics
from dataclasses import dataclass
from enum import StrEnum

# A shot short game/approach into the "traditional wedge" window is where
# distance control drills like the 9-Ball Wedge Matrix apply (PRD §7.1).
APPROACH_WEAKNESS_MIN_YARDS = 100.0
APPROACH_WEAKNESS_MAX_YARDS = 125.0
# Below-zero average Strokes Gained in that window means this player is
# losing strokes to the field from exactly the distance the drill targets.
APPROACH_WEAKNESS_SG_THRESHOLD = 0.0
MIN_APPROACH_SAMPLE = 3

# PRD §7.1's target metric for the 30-Yard Corridor Test is a <15y lateral
# miss; a driver whose *empirical* on-course lateral spread already exceeds
# that is the weakness the drill is meant to catch.
DRIVER_DISPERSION_LATERAL_STDEV_THRESHOLD_YARDS = 15.0

# PRD §7.1's Low-Point Compression target is smash factor >1.36; flag a
# player averaging meaningfully below that on their irons.
IRON_SMASH_FACTOR_THRESHOLD = 1.30
MIN_IRON_SAMPLE = 3

# PRD §7.1's Safety Circle Test target is >=80% of lag putts inside 3ft;
# flag a player who isn't clearing that bar today.
PUTTING_LAG_EFFICIENCY_THRESHOLD_PCT = 70.0
MIN_LAG_PUTT_SAMPLE = 3


class Weakness(StrEnum):
    approach_100_125 = "approach_100_125"
    driver_dispersion = "driver_dispersion"
    iron_strike_quality = "iron_strike_quality"
    putting_lag_speed = "putting_lag_speed"


@dataclass(frozen=True)
class Combine:
    weakness: Weakness
    name: str
    instructions: str
    target_metric: str
    video_search_url: str


COMBINES: dict[Weakness, Combine] = {
    Weakness.approach_100_125: Combine(
        weakness=Weakness.approach_100_125,
        name="9-Ball Wedge Matrix",
        instructions=(
            "Pick 3 targets between 100-125y. Hit 3 balls at each, alternating "
            "targets so no two consecutive shots share a pin."
        ),
        target_metric="≥7 of 9 finish inside a 20ft radius of the target",
        video_search_url="https://www.youtube.com/results?search_query=9+ball+wedge+matrix+drill",
    ),
    Weakness.driver_dispersion: Combine(
        weakness=Weakness.driver_dispersion,
        name="30-Yard Corridor Test",
        instructions=(
            "On the range, pick a 30-yard-wide corridor down the target line. Hit "
            "10 drivers, tracking spin axis and which land inside the corridor."
        ),
        target_metric="Spin axis within ±4°, lateral miss <15y",
        video_search_url="https://www.youtube.com/results?search_query=30+yard+corridor+driver+drill",
    ),
    Weakness.iron_strike_quality: Combine(
        weakness=Weakness.iron_strike_quality,
        name="Low-Point Compression",
        instructions=(
            "With a mid iron, hit 10 balls off a strip of impact tape or a towel "
            "one ball-width in front of the ball, focusing on ball-then-turf contact."
        ),
        target_metric="Smash factor >1.36, clean turf interaction (no fat/thin strikes)",
        video_search_url="https://www.youtube.com/results?search_query=low+point+compression+drill+irons",
    ),
    Weakness.putting_lag_speed: Combine(
        weakness=Weakness.putting_lag_speed,
        name="Safety Circle Test",
        instructions=(
            "From 20-40ft, putt 10 balls to a 3ft-radius circle chalked or "
            "tee-marked around the hole, varying starting distance each putt."
        ),
        target_metric="≥80% finish inside the 3ft ring",
        video_search_url="https://www.youtube.com/results?search_query=safety+circle+putting+drill",
    ),
}


@dataclass(frozen=True)
class WeaknessSignal:
    weakness: Weakness
    detail: str


def detect_approach_weakness(strokes_gained_in_bracket: list[float]) -> WeaknessSignal | None:
    """`strokes_gained_in_bracket`: SG values of every non-putt shot struck
    from 100-125y, across as many rounds as the caller wants to consider."""
    if len(strokes_gained_in_bracket) < MIN_APPROACH_SAMPLE:
        return None
    avg = statistics.fmean(strokes_gained_in_bracket)
    if avg >= APPROACH_WEAKNESS_SG_THRESHOLD:
        return None
    return WeaknessSignal(
        weakness=Weakness.approach_100_125,
        detail=(
            f"Averaging {avg:+.2f} strokes gained on {len(strokes_gained_in_bracket)} shots "
            f"from {APPROACH_WEAKNESS_MIN_YARDS:.0f}-{APPROACH_WEAKNESS_MAX_YARDS:.0f}y."
        ),
    )


def detect_driver_dispersion_weakness(
    driver_lateral_stdev_yards: float | None,
) -> WeaknessSignal | None:
    if driver_lateral_stdev_yards is None:
        return None
    if driver_lateral_stdev_yards <= DRIVER_DISPERSION_LATERAL_STDEV_THRESHOLD_YARDS:
        return None
    return WeaknessSignal(
        weakness=Weakness.driver_dispersion,
        detail=(
            f"Driver lateral dispersion is {driver_lateral_stdev_yards:.1f}y (1 stdev), "
            f"above the {DRIVER_DISPERSION_LATERAL_STDEV_THRESHOLD_YARDS:.0f}y corridor target."
        ),
    )


def detect_iron_strike_weakness(
    iron_smash_factors: list[float],
) -> WeaknessSignal | None:
    """`iron_smash_factors`: R10/R50 `PracticeShot.smash_factor` values for
    every iron shot on file (`app.services.delivery_profile`)."""
    if len(iron_smash_factors) < MIN_IRON_SAMPLE:
        return None
    avg = statistics.fmean(iron_smash_factors)
    if avg >= IRON_SMASH_FACTOR_THRESHOLD:
        return None
    return WeaknessSignal(
        weakness=Weakness.iron_strike_quality,
        detail=f"Average iron smash factor is {avg:.2f} over {len(iron_smash_factors)} shots.",
    )


def detect_putting_lag_weakness(
    lag_efficiency_pct: float | None, lag_putt_count: int
) -> WeaknessSignal | None:
    if lag_efficiency_pct is None or lag_putt_count < MIN_LAG_PUTT_SAMPLE:
        return None
    if lag_efficiency_pct >= PUTTING_LAG_EFFICIENCY_THRESHOLD_PCT:
        return None
    return WeaknessSignal(
        weakness=Weakness.putting_lag_speed,
        detail=(
            f"{lag_efficiency_pct:.0f}% of {lag_putt_count} lag putts finished inside 3ft, "
            f"below the {PUTTING_LAG_EFFICIENCY_THRESHOLD_PCT:.0f}% bar."
        ),
    )


def recommend_combines(signals: list[WeaknessSignal]) -> list[Combine]:
    """One combine per detected signal, in the same order — callers that
    want a stable UI order can sort `signals` first."""
    return [COMBINES[signal.weakness] for signal in signals]
