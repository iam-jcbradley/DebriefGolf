from app.models.shot import Lie, Shot
from app.services.approach import (
    SHORT_SIDE_PROXIMITY_YARDS,
    ApproachLeave,
    classify_approach_leave,
)


def _approach(end_lie: Lie, end_distance: float) -> Shot:
    return Shot(
        round_id=1, hole_id=1, shot_number=1, club="7-Iron",
        start_lie=Lie.fairway, end_lie=end_lie,
        start_distance_yards=150, end_distance_yards=end_distance,
    )


def test_shot_that_reaches_the_green_is_on_green() -> None:
    shot = _approach(Lie.green, end_distance=5.0)
    assert classify_approach_leave(shot) == ApproachLeave.on_green


def test_tight_miss_from_sand_is_short_sided() -> None:
    shot = _approach(Lie.sand, end_distance=SHORT_SIDE_PROXIMITY_YARDS - 1)
    assert classify_approach_leave(shot) == ApproachLeave.short_sided


def test_roomy_miss_from_rough_is_safe_leave() -> None:
    shot = _approach(Lie.rough, end_distance=SHORT_SIDE_PROXIMITY_YARDS + 1)
    assert classify_approach_leave(shot) == ApproachLeave.safe_leave


def test_boundary_distance_counts_as_short_sided() -> None:
    shot = _approach(Lie.fringe, end_distance=SHORT_SIDE_PROXIMITY_YARDS)
    assert classify_approach_leave(shot) == ApproachLeave.short_sided


def test_tee_or_penalty_end_lie_is_unclassified() -> None:
    shot = _approach(Lie.penalty, end_distance=140)
    assert classify_approach_leave(shot) == ApproachLeave.unclassified


def test_recovery_lie_within_proximity_is_short_sided() -> None:
    shot = _approach(Lie.recovery, end_distance=5.0)
    assert classify_approach_leave(shot) == ApproachLeave.short_sided
