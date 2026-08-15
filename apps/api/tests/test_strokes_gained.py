import pytest

from app.models.benchmark import HANDICAP_BUCKETS
from app.models.shot import Lie, Shot
from app.services.benchmarks import expected_strokes
from app.services.strokes_gained import (
    ARG_THRESHOLD_YARDS,
    SGCategory,
    categorize_shot,
    compute_round_strokes_gained,
    nearest_handicap_bucket,
    strokes_gained_for_shot,
)


def _shot(**kwargs) -> Shot:
    defaults = dict(
        round_id=1, hole_id=1, shot_number=1, club="7-Iron",
        start_lie=Lie.fairway, end_lie=Lie.green,
        start_distance_yards=150, end_distance_yards=6.0,
    )
    defaults.update(kwargs)
    return Shot(**defaults)


def test_nearest_handicap_bucket_exact_and_rounded() -> None:
    assert nearest_handicap_bucket(0) == 0
    assert nearest_handicap_bucket(5) == 5
    assert nearest_handicap_bucket(12) == 10
    assert nearest_handicap_bucket(13) == 15
    assert nearest_handicap_bucket(24) == 25
    assert nearest_handicap_bucket(-3) == 0
    assert nearest_handicap_bucket(99) == 25


def test_nearest_handicap_bucket_tie_breaks_to_lower_bucket() -> None:
    assert nearest_handicap_bucket(2.5) == 0
    assert nearest_handicap_bucket(7.5) == 5


def test_strokes_gained_for_shot_matches_hand_computed_value() -> None:
    shot = _shot(start_lie=Lie.fairway, start_distance_yards=150, end_lie=Lie.green,
                 end_distance_yards=6.0)
    expected = (
        expected_strokes(0, Lie.fairway, 150) - expected_strokes(0, Lie.green, 6.0) - 1
    )
    assert strokes_gained_for_shot(shot, 0) == pytest.approx(expected)


def test_holed_shot_gains_the_full_remaining_benchmark() -> None:
    # a 3ft putt that goes in: SG = ES(green, 1yd) - ES(hole, 0) - 1 = ES(green,1yd) - 1
    shot = _shot(club="Putter", start_lie=Lie.green, end_lie=Lie.hole,
                 start_distance_yards=1.0, end_distance_yards=0)
    expected = expected_strokes(10, Lie.green, 1.0) - 1
    assert strokes_gained_for_shot(shot, 10) == pytest.approx(expected)


class TestCategorizeShot:
    def test_putter_is_always_putt_regardless_of_lie(self) -> None:
        shot = _shot(club="Putter", start_lie=Lie.fringe, start_distance_yards=5)
        assert categorize_shot(shot, hole_par=4) == SGCategory.putt

    def test_green_lie_without_explicit_club_is_putt(self) -> None:
        shot = _shot(club=None, start_lie=Lie.green, start_distance_yards=2)
        assert categorize_shot(shot, hole_par=4) == SGCategory.putt

    def test_tee_shot_on_par_4_is_ott(self) -> None:
        shot = _shot(club="Driver", start_lie=Lie.tee, start_distance_yards=400)
        assert categorize_shot(shot, hole_par=4) == SGCategory.ott

    def test_tee_shot_on_par_5_is_ott(self) -> None:
        shot = _shot(club="Driver", start_lie=Lie.tee, start_distance_yards=520)
        assert categorize_shot(shot, hole_par=5) == SGCategory.ott

    def test_tee_shot_on_par_3_is_not_ott(self) -> None:
        shot = _shot(club="7-Iron", start_lie=Lie.tee, start_distance_yards=175)
        assert categorize_shot(shot, hole_par=3) != SGCategory.ott
        assert categorize_shot(shot, hole_par=3) == SGCategory.app

    def test_short_full_swing_shot_is_arg(self) -> None:
        shot = _shot(club="SW", start_lie=Lie.sand, start_distance_yards=ARG_THRESHOLD_YARDS)
        assert categorize_shot(shot, hole_par=4) == SGCategory.arg

    def test_long_full_swing_shot_is_app(self) -> None:
        shot = _shot(club="7-Iron", start_lie=Lie.fairway,
                     start_distance_yards=ARG_THRESHOLD_YARDS + 0.01)
        assert categorize_shot(shot, hole_par=4) == SGCategory.app


def test_sg_telescopes_across_a_hole() -> None:
    """Sum of per-shot SG across a hole always equals
    Benchmark(first start) - Benchmark(last end) - strokes_taken, regardless
    of the lies/distances in between, as long as each shot's end matches the
    next shot's start exactly (true of any real recorded shot sequence)."""
    bucket = 15
    shots = [
        _shot(shot_number=1, club="Driver", start_lie=Lie.tee, end_lie=Lie.fairway,
              start_distance_yards=400, end_distance_yards=150),
        _shot(shot_number=2, club="7-Iron", start_lie=Lie.fairway, end_lie=Lie.penalty,
              start_distance_yards=150, end_distance_yards=150),
        _shot(shot_number=3, club=None, start_lie=Lie.penalty, end_lie=Lie.penalty,
              start_distance_yards=150, end_distance_yards=150),
        _shot(shot_number=4, club="PW", start_lie=Lie.penalty, end_lie=Lie.green,
              start_distance_yards=150, end_distance_yards=6.0),
        _shot(shot_number=5, club="Putter", start_lie=Lie.green, end_lie=Lie.hole,
              start_distance_yards=6.0, end_distance_yards=0),
    ]

    total_sg = sum(strokes_gained_for_shot(s, bucket) for s in shots)

    from app.services.benchmarks import expected_strokes as es

    expected_total = es(bucket, Lie.tee, 400) - es(bucket, Lie.hole, 0) - len(shots)
    assert total_sg == pytest.approx(expected_total)


def test_compute_round_strokes_gained_sums_by_category() -> None:
    shots_with_par = [
        (_shot(shot_number=1, club="Driver", start_lie=Lie.tee, end_lie=Lie.fairway,
               start_distance_yards=400, end_distance_yards=150), 4),
        (_shot(shot_number=2, club="7-Iron", start_lie=Lie.fairway, end_lie=Lie.green,
               start_distance_yards=150, end_distance_yards=6.0), 4),
        (_shot(shot_number=3, club="Putter", start_lie=Lie.green, end_lie=Lie.hole,
               start_distance_yards=6.0, end_distance_yards=0), 4),
    ]

    summary = compute_round_strokes_gained(shots_with_par, handicap_index=12)

    assert summary.handicap_bucket == 10
    assert summary.by_category[SGCategory.ott] != 0
    assert summary.by_category[SGCategory.app] != 0
    assert summary.by_category[SGCategory.putt] != 0
    assert summary.by_category[SGCategory.arg] == 0
    assert summary.total == pytest.approx(sum(summary.by_category.values()))
    assert len(summary.shots) == 3
    assert [r.category for r in summary.shots] == [
        SGCategory.ott, SGCategory.app, SGCategory.putt,
    ]


def test_all_handicap_buckets_produce_finite_sg() -> None:
    shot = _shot()
    for bucket in HANDICAP_BUCKETS:
        sg = strokes_gained_for_shot(shot, bucket)
        assert isinstance(sg, float)
