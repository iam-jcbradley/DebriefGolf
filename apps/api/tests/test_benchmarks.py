import pytest

from app.models.benchmark import HANDICAP_BUCKETS
from app.models.shot import Lie
from app.services.benchmarks import (
    SCRATCH_CURVES,
    expected_strokes,
    generate_benchmark_rows,
)


def test_expected_strokes_at_seeded_scratch_points_matches_curve() -> None:
    # bucket 0 has factor 1.0, so expected_strokes should equal the raw curve value exactly.
    for lie, curve in SCRATCH_CURVES.items():
        for distance, scratch_value in curve:
            assert expected_strokes(0, lie, distance) == pytest.approx(scratch_value)


def test_distance_zero_is_always_zero_strokes() -> None:
    for bucket in HANDICAP_BUCKETS:
        assert expected_strokes(bucket, Lie.green, 0) == 0.0
        assert expected_strokes(bucket, Lie.tee, 0) == 0.0


def test_monotonic_increasing_in_distance() -> None:
    for lie, curve in SCRATCH_CURVES.items():
        distances = [d for d, _ in curve]
        values = [expected_strokes(10, lie, d) for d in distances]
        assert values == sorted(values)


def test_monotonic_increasing_in_handicap_for_full_swing_lie() -> None:
    values = [expected_strokes(bucket, Lie.fairway, 150) for bucket in HANDICAP_BUCKETS]
    assert values == sorted(values)
    assert values[0] < values[-1]


def test_monotonic_increasing_in_handicap_for_short_game_lie() -> None:
    values = [expected_strokes(bucket, Lie.green, 10) for bucket in HANDICAP_BUCKETS]
    assert values == sorted(values)
    assert values[0] < values[-1]


def test_sand_worse_than_fairway_at_same_distance() -> None:
    for bucket in HANDICAP_BUCKETS:
        assert expected_strokes(bucket, Lie.sand, 30) > expected_strokes(bucket, Lie.fairway, 30)


def test_recovery_worst_full_swing_lie() -> None:
    for bucket in HANDICAP_BUCKETS:
        recovery = expected_strokes(bucket, Lie.recovery, 50)
        for lie in (Lie.tee, Lie.fairway, Lie.rough, Lie.sand):
            assert recovery >= expected_strokes(bucket, lie, 50)


def test_interpolation_between_seeded_points() -> None:
    # fairway curve has (100, 2.71) and (125, 2.76) for scratch — midpoint distance
    # should land between those two values.
    low = expected_strokes(0, Lie.fairway, 100)
    mid = expected_strokes(0, Lie.fairway, 112.5)
    high = expected_strokes(0, Lie.fairway, 125)
    assert low < mid < high


def test_distance_clamped_outside_curve_range() -> None:
    shortest = SCRATCH_CURVES[Lie.tee][0][0]
    longest = SCRATCH_CURVES[Lie.tee][-1][0]
    assert expected_strokes(0, Lie.tee, 1) == expected_strokes(0, Lie.tee, shortest)
    assert expected_strokes(0, Lie.tee, 10_000) == expected_strokes(0, Lie.tee, longest)


def test_unknown_handicap_bucket_raises() -> None:
    with pytest.raises(ValueError, match="handicap_bucket"):
        expected_strokes(7, Lie.fairway, 100)


def test_lie_without_benchmark_curve_raises() -> None:
    with pytest.raises(ValueError, match="lie"):
        expected_strokes(0, Lie.hole, 100)


def test_penalty_lie_is_fairway_equivalent_plus_one_stroke() -> None:
    for bucket in HANDICAP_BUCKETS:
        for distance in (10, 100, 300):
            assert expected_strokes(bucket, Lie.penalty, distance) == pytest.approx(
                1 + expected_strokes(bucket, Lie.fairway, distance)
            )


def test_negative_distance_raises() -> None:
    with pytest.raises(ValueError, match="distance_yards"):
        expected_strokes(0, Lie.fairway, -1)


def test_generate_benchmark_rows_covers_full_cross_product() -> None:
    rows = generate_benchmark_rows()
    expected_count = len(HANDICAP_BUCKETS) * sum(len(curve) for curve in SCRATCH_CURVES.values())
    assert len(rows) == expected_count

    seen = {(r["handicap_bucket"], r["lie"], r["distance_yards"]) for r in rows}
    assert len(seen) == expected_count  # no duplicate keys
    assert all(r["expected_strokes"] > 0 for r in rows)
