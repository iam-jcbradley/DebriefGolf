from app.services.practice_combines import (
    COMBINES,
    Weakness,
    detect_approach_weakness,
    detect_driver_dispersion_weakness,
    detect_iron_strike_weakness,
    detect_putting_lag_weakness,
    recommend_combines,
)


class TestDetectApproachWeakness:
    def test_flags_negative_average_sg_in_bracket(self) -> None:
        signal = detect_approach_weakness([-0.5, -0.3, -0.4])
        assert signal is not None
        assert signal.weakness == Weakness.approach_100_125

    def test_no_signal_when_average_is_positive(self) -> None:
        assert detect_approach_weakness([0.2, 0.1, 0.3]) is None

    def test_no_signal_below_minimum_sample_size(self) -> None:
        assert detect_approach_weakness([-1.0, -1.0]) is None

    def test_no_signal_with_no_shots(self) -> None:
        assert detect_approach_weakness([]) is None


class TestDetectDriverDispersionWeakness:
    def test_flags_lateral_stdev_above_threshold(self) -> None:
        signal = detect_driver_dispersion_weakness(18.0)
        assert signal is not None
        assert signal.weakness == Weakness.driver_dispersion

    def test_no_signal_within_target(self) -> None:
        assert detect_driver_dispersion_weakness(10.0) is None

    def test_no_signal_when_no_data(self) -> None:
        assert detect_driver_dispersion_weakness(None) is None


class TestDetectIronStrikeWeakness:
    def test_flags_low_average_smash_factor(self) -> None:
        signal = detect_iron_strike_weakness([1.20, 1.22, 1.18])
        assert signal is not None
        assert signal.weakness == Weakness.iron_strike_quality

    def test_no_signal_above_threshold(self) -> None:
        assert detect_iron_strike_weakness([1.35, 1.36, 1.38]) is None

    def test_no_signal_below_minimum_sample(self) -> None:
        assert detect_iron_strike_weakness([1.10, 1.10]) is None


class TestDetectPuttingLagWeakness:
    def test_flags_low_efficiency(self) -> None:
        signal = detect_putting_lag_weakness(50.0, lag_putt_count=6)
        assert signal is not None
        assert signal.weakness == Weakness.putting_lag_speed

    def test_no_signal_above_threshold(self) -> None:
        assert detect_putting_lag_weakness(85.0, lag_putt_count=6) is None

    def test_no_signal_below_minimum_sample(self) -> None:
        assert detect_putting_lag_weakness(0.0, lag_putt_count=1) is None

    def test_no_signal_when_none(self) -> None:
        assert detect_putting_lag_weakness(None, lag_putt_count=10) is None


class TestRecommendCombines:
    def test_every_weakness_has_exactly_one_combine(self) -> None:
        assert set(COMBINES.keys()) == set(Weakness)

    def test_maps_signals_to_the_matching_combine_in_order(self) -> None:
        signal = detect_approach_weakness([-1.0, -1.0, -1.0])
        assert signal is not None

        combines = recommend_combines([signal])

        assert len(combines) == 1
        assert combines[0].name == "9-Ball Wedge Matrix"
