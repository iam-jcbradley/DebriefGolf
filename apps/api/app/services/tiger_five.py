"""Tiger 5 scoring-killer evaluator + Clean Card Index (PRD §5.2, §10 Phase 2).

The "Tiger 5" are the five error types the PRD singles out as the biggest
score-killers: double bogeys or worse, 3-putts, par-5 bogeys, blown
short-game recoveries inside 50y, and penalties taken from inside 150y.

Hole score is derived as the number of recorded `Shot` rows for that hole —
every stroke, including an explicit stroke-and-distance penalty marker row,
is one recorded shot (see `app/db/seed.py`'s hole 2 for that pattern), so a
plain count is correct without any special-casing here.

Clean Card Index (CCI) uses the traditional golf sense of a "clean card":
the percentage of holes played at par or better (no bogeys at all) — a
stricter, simpler bar than "no Tiger 5 violation", and the one usually
meant by the term.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from app.models.shot import Lie, Shot

BLOWN_RECOVERY_THRESHOLD_YARDS = 50.0
PENALTY_INSIDE_THRESHOLD_YARDS = 150.0

# Lies from which a shot isn't a "short-game recovery opportunity" — tee
# shots and putts don't count as recoveries, and a penalty marker row (which
# represents the stroke itself, not a played shot) has no strokes_gained
# outcome worth judging as "blown".
_NON_RECOVERY_LIES = {Lie.tee, Lie.green, Lie.penalty}


@dataclass(frozen=True)
class HoleResult:
    hole_number: int
    par: int
    score: int
    is_double_bogey_or_worse: bool
    is_three_putt_or_worse: bool
    is_par_five_bogey: bool
    blown_recoveries: int
    penalties_inside_150: int

    @property
    def is_clean(self) -> bool:
        return self.score <= self.par


@dataclass(frozen=True)
class TigerFiveSummary:
    holes: list[HoleResult]
    double_bogeys_or_worse: int
    three_putts: int
    par_five_bogeys: int
    blown_recoveries_inside_50: int
    penalties_inside_150: int
    clean_card_index: float  # 0-100, rounded to 1 decimal


def evaluate_hole(
    hole_number: int,
    par: int,
    shots: list[Shot],
    strokes_gained: Mapping[int, float | None] | None = None,
) -> HoleResult:
    """`shots`: every recorded `Shot` row for this hole, in stroke order.

    Blown-recovery detection needs each shot's Strokes Gained. Pass
    `strokes_gained` (shot id -> SG) to supply freshly-computed values;
    omit it to read the persisted `Shot.strokes_gained` column. The
    parameter exists because `GET /rounds/{id}/analytics` computes SG for
    its own response anyway, and used to *write* those values back to the
    database purely so this function could read them off the ORM objects —
    a GET that mutated every shot in the round on every dashboard load.
    """
    score = len(shots)
    putts = sum(1 for s in shots if s.club == "Putter")

    def _sg(shot: Shot) -> float | None:
        if strokes_gained is None:
            return shot.strokes_gained
        return strokes_gained.get(shot.id)

    blown_recoveries = sum(
        1
        for s in shots
        if s.start_lie not in _NON_RECOVERY_LIES
        and s.start_distance_yards <= BLOWN_RECOVERY_THRESHOLD_YARDS
        and _sg(s) is not None
        and _sg(s) < 0
    )
    # Count the penalty-stroke marker row itself (start_lie == end_lie ==
    # penalty — see app/db/seed.py hole 14 for the pattern), not every row
    # that happens to *end* in a penalty lie: the shot that went into the
    # hazard also ends in `penalty`, and counting both would double-count
    # what is really one penalty stroke.
    penalties_inside_150 = sum(
        1
        for s in shots
        if s.start_lie == Lie.penalty
        and s.end_lie == Lie.penalty
        and s.start_distance_yards <= PENALTY_INSIDE_THRESHOLD_YARDS
    )

    return HoleResult(
        hole_number=hole_number,
        par=par,
        score=score,
        is_double_bogey_or_worse=(score - par) >= 2,
        is_three_putt_or_worse=putts >= 3,
        is_par_five_bogey=(par == 5 and (score - par) >= 1),
        blown_recoveries=blown_recoveries,
        penalties_inside_150=penalties_inside_150,
    )


def evaluate_round(
    holes: list[tuple[int, int, list[Shot]]],
    strokes_gained: Mapping[int, float | None] | None = None,
) -> TigerFiveSummary:
    """`holes`: one `(hole_number, par, shots_for_that_hole)` per hole.
    `strokes_gained`: see `evaluate_hole`."""
    results = [
        evaluate_hole(number, par, shots, strokes_gained) for number, par, shots in holes
    ]
    total_holes = len(results)
    clean_holes = sum(1 for h in results if h.is_clean)
    cci = round(100 * clean_holes / total_holes, 1) if total_holes else 0.0

    return TigerFiveSummary(
        holes=results,
        double_bogeys_or_worse=sum(1 for h in results if h.is_double_bogey_or_worse),
        three_putts=sum(1 for h in results if h.is_three_putt_or_worse),
        par_five_bogeys=sum(1 for h in results if h.is_par_five_bogey),
        blown_recoveries_inside_50=sum(h.blown_recoveries for h in results),
        penalties_inside_150=sum(h.penalties_inside_150 for h in results),
        clean_card_index=cci,
    )
