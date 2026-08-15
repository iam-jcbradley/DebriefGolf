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

# --- Calibration notes ---
#
# Every threshold below is grounded one of two ways, and each detector's
# docstring says which:
#
# 1. **Matched to the combine's own PRD §7.1 target metric** (driver
#    dispersion, putting lag) — the detector fires exactly when the player
#    hasn't yet met the bar the drill itself is designed to clear. This is
#    the strongest grounding available: it's not a guess, it's the same
#    number the product already commits to elsewhere.
# 2. **Grounded in commonly-published launch-monitor averages** (iron
#    strike quality) where PRD gives one flat number but the real
#    expectation varies by club — e.g. TrackMan's publicly shared average
#    smash-factor-by-club figures. These are order-of-magnitude accurate,
#    widely repeated in golf instruction content, hand-authored into this
#    table rather than transcribed from a licensed dataset — the same
#    caveat `app/models/benchmark.py`'s `SCRATCH_CURVES` already carries
#    for Strokes Gained.
#
# The approach-100-125y detector is the one exception: there's no PRD
# target metric in the same units as on-course Strokes Gained to align to,
# so it uses SG < 0 relative to the player's own handicap bucket (i.e.
# "losing strokes to your own baseline from this distance") — this
# implementation's own calibration, not sourced from either PRD or a
# published benchmark.

# A shot short game/approach into the "traditional wedge" window is where
# distance control drills like the 9-Ball Wedge Matrix apply (PRD §7.1).
APPROACH_WEAKNESS_MIN_YARDS = 100.0
APPROACH_WEAKNESS_MAX_YARDS = 125.0
APPROACH_WEAKNESS_SG_THRESHOLD = 0.0
# 3 shots from this precise a distance bracket is easy to hit by chance in
# one bad round; 5 asks for a small pattern across (typically) 2+ rounds.
MIN_APPROACH_SAMPLE = 5

# PRD §7.1's target metric for the 30-Yard Corridor Test is a <15y lateral
# miss; a driver whose *empirical* on-course lateral spread already exceeds
# that is the weakness the drill is meant to catch.
DRIVER_DISPERSION_LATERAL_STDEV_THRESHOLD_YARDS = 15.0

# Expected average smash factor per iron (see calibration note above) —
# smash factor falls with loft (more of the club's energy goes into spin
# and launch angle, less into ball speed), so a single flat cutoff across
# every iron either misses long-iron strikers who are actually struggling
# or wrongly flags short-iron/wedge players who are hitting it fine for
# that club. Only covers `app.services.smart_bag.CLUB_ORDER`'s "N-Iron"
# entries (2-9) — PW/GW/AW/SW/LW are wedges, out of this weakness's scope.
EXPECTED_SMASH_FACTOR_BY_IRON: dict[str, float] = {
    "2-Iron": 1.42,
    "3-Iron": 1.41,
    "4-Iron": 1.39,
    "5-Iron": 1.38,
    "6-Iron": 1.36,
    "7-Iron": 1.33,
    "8-Iron": 1.30,
    "9-Iron": 1.28,
}
# Flag a club as underperforming once its average falls this far below its
# own expected value — a small buffer so normal shot-to-shot noise on a
# handful of swings doesn't trip the detector.
IRON_SMASH_FACTOR_DEFICIT_THRESHOLD = 0.05
MIN_IRON_SAMPLES_PER_CLUB = 3

# PRD §7.1's Safety Circle Test target is >=80% of lag putts inside 3ft;
# flag a player who isn't clearing that bar today.
PUTTING_LAG_EFFICIENCY_THRESHOLD_PCT = 80.0
# Lag putts (>20ft) are a minority of a round's ~14-18 putts; 5 typically
# needs 2+ rounds on file, enough to smooth over one unusually bad putting
# day.
MIN_LAG_PUTT_SAMPLE = 5


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


@dataclass(frozen=True)
class _IronDeficit:
    club: str
    avg_smash_factor: float
    expected: float
    shot_count: int

    @property
    def deficit(self) -> float:
        return self.expected - self.avg_smash_factor


def detect_iron_strike_weakness(
    smash_factor_by_iron: dict[str, list[float]],
) -> WeaknessSignal | None:
    """`smash_factor_by_iron`: R10/R50 `PracticeShot.smash_factor` values
    (`app.services.delivery_profile`), grouped by club — *not* flattened
    into one list, since "underperforming" only means something relative
    to each club's own expected smash factor (see
    `EXPECTED_SMASH_FACTOR_BY_IRON`'s calibration note above).

    Flags on the single worst-performing qualifying club, not an average
    deficit across every iron: averaging would let one genuinely bad club
    (a real problem) get diluted by the rest of an otherwise-fine bag,
    which is the opposite of "prescriptive" — the whole point is to name
    which specific club needs the drill.
    """
    deficits: list[_IronDeficit] = []
    for club, factors in smash_factor_by_iron.items():
        expected = EXPECTED_SMASH_FACTOR_BY_IRON.get(club)
        if expected is None or len(factors) < MIN_IRON_SAMPLES_PER_CLUB:
            continue
        avg = statistics.fmean(factors)
        deficits.append(
            _IronDeficit(
                club=club, avg_smash_factor=avg, expected=expected, shot_count=len(factors)
            )
        )

    if not deficits:
        return None

    worst = max(deficits, key=lambda d: d.deficit)
    if worst.deficit < IRON_SMASH_FACTOR_DEFICIT_THRESHOLD:
        return None

    return WeaknessSignal(
        weakness=Weakness.iron_strike_quality,
        detail=(
            f"{worst.club} is averaging {worst.avg_smash_factor:.2f} smash factor "
            f"(expected ~{worst.expected:.2f}) over {worst.shot_count} shots."
        ),
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
