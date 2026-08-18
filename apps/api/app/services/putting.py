"""Putting mechanics split (PRD §5.2, §10 Phase 2): lag speed efficiency on
long putts, and start-line conversion (make rate) on short putts.

- **Lag speed efficiency**: of putts starting beyond 20ft, what fraction
  finish within a 3ft "safe zone" of the hole? A low number points at speed
  control on longer putts rather than aim.
- **Start-line conversion**: of putts starting inside 6ft, what fraction go
  in? A low number points at read/start-line rather than speed.

`Shot.start_distance_yards`/`end_distance_yards` are in yards; the 20ft/6ft/
3ft thresholds from the PRD are converted to yards (÷3) here.
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from app.models.shot import Lie
from app.services.shot_view import ShotView

LAG_PUTT_THRESHOLD_YARDS = 20 / 3
SHORT_PUTT_THRESHOLD_YARDS = 6 / 3
LAG_PROXIMITY_GOOD_YARDS = 3 / 3


def is_putt(shot: ShotView) -> bool:
    return shot.club == "Putter"


@dataclass(frozen=True)
class PuttingMechanics:
    lag_putt_count: int
    lag_putts_within_3ft: int
    lag_efficiency_pct: float | None
    average_lag_proximity_yards: float | None
    short_putt_count: int
    short_putts_made: int
    start_line_conversion_pct: float | None


def evaluate_putting(shots: Sequence[ShotView]) -> PuttingMechanics:
    putts = [s for s in shots if is_putt(s)]
    lag_putts = [p for p in putts if p.start_distance_yards > LAG_PUTT_THRESHOLD_YARDS]
    short_putts = [p for p in putts if p.start_distance_yards < SHORT_PUTT_THRESHOLD_YARDS]

    lag_within_3ft = [p for p in lag_putts if p.end_distance_yards <= LAG_PROXIMITY_GOOD_YARDS]
    short_made = [p for p in short_putts if p.end_lie == Lie.hole]

    return PuttingMechanics(
        lag_putt_count=len(lag_putts),
        lag_putts_within_3ft=len(lag_within_3ft),
        lag_efficiency_pct=(
            round(100 * len(lag_within_3ft) / len(lag_putts), 1) if lag_putts else None
        ),
        average_lag_proximity_yards=(
            round(statistics.fmean(p.end_distance_yards for p in lag_putts), 2)
            if lag_putts
            else None
        ),
        short_putt_count=len(short_putts),
        short_putts_made=len(short_made),
        start_line_conversion_pct=(
            round(100 * len(short_made) / len(short_putts), 1) if short_putts else None
        ),
    )
