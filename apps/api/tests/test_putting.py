from app.models.shot import Lie, Shot
from app.services.putting import evaluate_putting


def _putt(start: float, end: float, holed: bool = False) -> Shot:
    return Shot(
        round_id=1, hole_id=1, shot_number=1, club="Putter",
        start_lie=Lie.green, end_lie=Lie.hole if holed else Lie.green,
        start_distance_yards=start, end_distance_yards=0 if holed else end,
    )


def _full_swing_shot() -> Shot:
    return Shot(
        round_id=1, hole_id=1, shot_number=1, club="7-Iron",
        start_lie=Lie.fairway, end_lie=Lie.green,
        start_distance_yards=150, end_distance_yards=6.0,
    )


class TestLagPutts:
    def test_long_putt_left_close_counts_within_3ft(self) -> None:
        putts = [_putt(start=10.0, end=0.9)]  # 30ft putt left 2.7ft away
        result = evaluate_putting(putts)
        assert result.lag_putt_count == 1
        assert result.lag_putts_within_3ft == 1
        assert result.lag_efficiency_pct == 100.0

    def test_long_putt_left_far_does_not_count_within_3ft(self) -> None:
        putts = [_putt(start=10.0, end=2.0)]  # left it 6ft away
        result = evaluate_putting(putts)
        assert result.lag_putts_within_3ft == 0
        assert result.lag_efficiency_pct == 0.0

    def test_short_putt_excluded_from_lag_putt_count(self) -> None:
        putts = [_putt(start=1.0, end=0.2)]  # ~3ft putt, below the 20ft lag threshold
        result = evaluate_putting(putts)
        assert result.lag_putt_count == 0
        assert result.lag_efficiency_pct is None

    def test_no_lag_putts_returns_none_not_zero_division(self) -> None:
        result = evaluate_putting([])
        assert result.lag_efficiency_pct is None
        assert result.average_lag_proximity_yards is None


class TestStartLineConversion:
    def test_short_putt_made_counts(self) -> None:
        putts = [_putt(start=1.0, end=0, holed=True)]  # ~3ft, made
        result = evaluate_putting(putts)
        assert result.short_putt_count == 1
        assert result.short_putts_made == 1
        assert result.start_line_conversion_pct == 100.0

    def test_short_putt_missed_counts_but_not_made(self) -> None:
        putts = [_putt(start=1.0, end=0.3)]  # ~3ft, missed, left ~1ft
        result = evaluate_putting(putts)
        assert result.short_putt_count == 1
        assert result.short_putts_made == 0
        assert result.start_line_conversion_pct == 0.0

    def test_long_putt_excluded_from_short_putt_count(self) -> None:
        putts = [_putt(start=10.0, end=0, holed=True)]  # 30ft putt made, not a "short putt"
        result = evaluate_putting(putts)
        assert result.short_putt_count == 0
        assert result.start_line_conversion_pct is None

    def test_mixed_short_putts_computes_percentage(self) -> None:
        putts = [
            _putt(start=1.0, end=0, holed=True),
            _putt(start=1.5, end=0, holed=True),
            _putt(start=0.5, end=0.2),
        ]
        result = evaluate_putting(putts)
        assert result.short_putt_count == 3
        assert result.short_putts_made == 2
        assert result.start_line_conversion_pct == round(100 * 2 / 3, 1)


def test_non_putter_shots_are_ignored() -> None:
    shots = [_full_swing_shot(), _putt(start=1.0, end=0, holed=True)]
    result = evaluate_putting(shots)
    assert result.short_putt_count == 1  # only the putt counted
