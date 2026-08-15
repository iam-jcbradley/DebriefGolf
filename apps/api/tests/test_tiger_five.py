from app.models.shot import Lie, Shot
from app.services.tiger_five import (
    BLOWN_RECOVERY_THRESHOLD_YARDS,
    PENALTY_INSIDE_THRESHOLD_YARDS,
    evaluate_hole,
    evaluate_round,
)


def _shot(**kwargs) -> Shot:
    defaults = dict(
        round_id=1, hole_id=1, shot_number=1, club="7-Iron",
        start_lie=Lie.fairway, end_lie=Lie.green,
        start_distance_yards=150, end_distance_yards=6.0, strokes_gained=None,
    )
    defaults.update(kwargs)
    return Shot(**defaults)


def _n_shots(n: int, **kwargs) -> list[Shot]:
    return [_shot(shot_number=i, **kwargs) for i in range(1, n + 1)]


class TestDoubleBogey:
    def test_par_is_not_double_bogey(self) -> None:
        result = evaluate_hole(1, par=4, shots=_n_shots(4))
        assert result.is_double_bogey_or_worse is False

    def test_bogey_is_not_double_bogey(self) -> None:
        result = evaluate_hole(1, par=4, shots=_n_shots(5))
        assert result.is_double_bogey_or_worse is False

    def test_double_bogey_flagged(self) -> None:
        result = evaluate_hole(1, par=4, shots=_n_shots(6))
        assert result.is_double_bogey_or_worse is True

    def test_worse_than_double_bogey_flagged(self) -> None:
        result = evaluate_hole(1, par=4, shots=_n_shots(8))
        assert result.is_double_bogey_or_worse is True


class TestThreePutt:
    def test_two_putts_not_flagged(self) -> None:
        shots = _n_shots(2, club="Driver") + _n_shots(2, club="Putter")
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.is_three_putt_or_worse is False

    def test_three_putts_flagged(self) -> None:
        shots = _n_shots(2, club="Driver") + _n_shots(3, club="Putter")
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.is_three_putt_or_worse is True


class TestParFiveBogey:
    def test_par_five_at_par_not_flagged(self) -> None:
        result = evaluate_hole(1, par=5, shots=_n_shots(5))
        assert result.is_par_five_bogey is False

    def test_par_five_bogey_flagged(self) -> None:
        result = evaluate_hole(1, par=5, shots=_n_shots(6))
        assert result.is_par_five_bogey is True

    def test_par_four_bogey_not_flagged_as_par_five_bogey(self) -> None:
        result = evaluate_hole(1, par=4, shots=_n_shots(5))
        assert result.is_par_five_bogey is False


class TestBlownRecovery:
    def test_negative_sg_short_game_shot_counts(self) -> None:
        shots = [_shot(start_lie=Lie.sand, start_distance_yards=20, strokes_gained=-0.6)]
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.blown_recoveries == 1

    def test_positive_sg_short_game_shot_does_not_count(self) -> None:
        shots = [_shot(start_lie=Lie.sand, start_distance_yards=20, strokes_gained=0.3)]
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.blown_recoveries == 0

    def test_unscored_shot_does_not_count(self) -> None:
        shots = [_shot(start_lie=Lie.sand, start_distance_yards=20, strokes_gained=None)]
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.blown_recoveries == 0

    def test_beyond_50_yards_does_not_count(self) -> None:
        shots = [
            _shot(
                start_lie=Lie.rough,
                start_distance_yards=BLOWN_RECOVERY_THRESHOLD_YARDS + 1,
                strokes_gained=-1.0,
            )
        ]
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.blown_recoveries == 0

    def test_tee_shot_never_counts_as_recovery(self) -> None:
        shots = [_shot(start_lie=Lie.tee, start_distance_yards=10, strokes_gained=-1.0)]
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.blown_recoveries == 0


class TestPenaltyInside150:
    def test_penalty_marker_from_inside_150_counts(self) -> None:
        shots = [
            _shot(
                start_lie=Lie.penalty, end_lie=Lie.penalty,
                start_distance_yards=PENALTY_INSIDE_THRESHOLD_YARDS - 1,
            )
        ]
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.penalties_inside_150 == 1

    def test_penalty_marker_from_outside_150_does_not_count(self) -> None:
        shots = [
            _shot(
                start_lie=Lie.penalty, end_lie=Lie.penalty,
                start_distance_yards=PENALTY_INSIDE_THRESHOLD_YARDS + 1,
            )
        ]
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.penalties_inside_150 == 0

    def test_non_penalty_shot_does_not_count(self) -> None:
        shots = [_shot(end_lie=Lie.green, start_distance_yards=100)]
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.penalties_inside_150 == 0

    def test_shot_that_only_ends_in_penalty_does_not_double_count(self) -> None:
        # The shot that went into the hazard also has end_lie == penalty, but
        # it's the same penalty event as the marker row that follows it — it
        # shouldn't be counted on its own (see app/db/seed.py hole 14).
        shots = [
            _shot(
                start_lie=Lie.fairway, end_lie=Lie.penalty,
                start_distance_yards=PENALTY_INSIDE_THRESHOLD_YARDS - 1,
            ),
            _shot(
                start_lie=Lie.penalty, end_lie=Lie.penalty,
                start_distance_yards=PENALTY_INSIDE_THRESHOLD_YARDS - 1,
            ),
        ]
        result = evaluate_hole(1, par=4, shots=shots)
        assert result.penalties_inside_150 == 1


class TestCleanCardIndex:
    def test_all_clean_holes_is_100(self) -> None:
        holes = [(i, 4, _n_shots(4)) for i in range(1, 19)]
        summary = evaluate_round(holes)
        assert summary.clean_card_index == 100.0

    def test_mixed_holes_computes_percentage(self) -> None:
        holes = [(1, 4, _n_shots(4)), (2, 4, _n_shots(5)), (3, 4, _n_shots(4)), (4, 4, _n_shots(4))]
        summary = evaluate_round(holes)
        assert summary.clean_card_index == 75.0

    def test_no_holes_is_zero_not_a_crash(self) -> None:
        summary = evaluate_round([])
        assert summary.clean_card_index == 0.0
        assert summary.holes == []


def test_evaluate_round_aggregates_across_holes() -> None:
    holes = [
        (1, 4, _n_shots(6)),  # double bogey
        (2, 5, _n_shots(6)),  # par 5 bogey
        (
            3,
            4,
            _n_shots(2, club="Driver") + _n_shots(3, club="Putter"),
        ),  # 3-putt
        (4, 4, _n_shots(4)),  # clean
    ]
    summary = evaluate_round(holes)

    assert summary.double_bogeys_or_worse == 1
    assert summary.par_five_bogeys == 1
    assert summary.three_putts == 1
    assert len(summary.holes) == 4
