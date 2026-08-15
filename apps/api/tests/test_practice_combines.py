from app.services.practice_combines import (
    COMBINES,
    EXPECTED_SMASH_FACTOR_BY_IRON,
    Weakness,
    detect_approach_weakness,
    detect_driver_dispersion_weakness,
    detect_iron_strike_weakness,
    detect_putting_lag_weakness,
    recommend_combines,
)


class TestDetectApproachWeakness:
    def test_flags_negative_average_sg_in_bracket(self) -> None:
        signal = detect_approach_weakness([-0.5, -0.3, -0.4, -0.2, -0.6])
        assert signal is not None
        assert signal.weakness == Weakness.approach_100_125

    def test_no_signal_when_average_is_positive(self) -> None:
        assert detect_approach_weakness([0.2, 0.1, 0.3, 0.1, 0.2]) is None

    def test_no_signal_below_minimum_sample_size(self) -> None:
        assert detect_approach_weakness([-1.0, -1.0, -1.0, -1.0]) is None

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
    def test_flags_a_club_averaging_meaningfully_below_its_expected_smash_factor(self) -> None:
        # 7-Iron's expected value is 1.33; these average 1.20, well below it.
        signal = detect_iron_strike_weakness({"7-Iron": [1.18, 1.20, 1.22]})
        assert signal is not None
        assert signal.weakness == Weakness.iron_strike_quality
        assert "7-Iron" in signal.detail

    def test_no_signal_when_at_or_above_expected_for_that_club(self) -> None:
        assert detect_iron_strike_weakness({"7-Iron": [1.33, 1.34, 1.35]}) is None

    def test_no_signal_within_the_noise_buffer(self) -> None:
        # 0.03 below expected (1.33) is inside the 0.05 buffer.
        assert detect_iron_strike_weakness({"7-Iron": [1.30, 1.30, 1.30]}) is None

    def test_no_signal_below_minimum_samples_for_that_club(self) -> None:
        assert detect_iron_strike_weakness({"7-Iron": [1.10, 1.10]}) is None

    def test_a_long_iron_is_judged_against_its_own_higher_expectation(self) -> None:
        # 1.30 is fine for a 9-Iron (expected ~1.28) but a real deficit for
        # a 3-Iron (expected ~1.41) — a single flat cutoff would get this
        # wrong in one direction or the other.
        assert detect_iron_strike_weakness({"9-Iron": [1.30, 1.30, 1.30]}) is None
        signal = detect_iron_strike_weakness({"3-Iron": [1.30, 1.30, 1.30]})
        assert signal is not None

    def test_flags_on_the_worst_club_not_diluted_by_a_fine_one(self) -> None:
        # A real 3-Iron problem (deficit 0.11) shouldn't get averaged away
        # by a perfectly fine 9-Iron (deficit ~0.00) — a coach needs to
        # know the 3-Iron specifically needs work, not a washed-out mean.
        signal = detect_iron_strike_weakness(
            {
                "9-Iron": [1.30, 1.30, 1.30],  # expected 1.28, deficit -0.02 (fine)
                "3-Iron": [1.30, 1.30, 1.30],  # expected 1.41, deficit 0.11 (a real problem)
            }
        )
        assert signal is not None
        assert "3-Iron" in signal.detail

    def test_no_signal_when_every_qualifying_club_is_within_its_own_buffer(self) -> None:
        signal = detect_iron_strike_weakness(
            {
                "9-Iron": [1.30, 1.30, 1.30],  # expected 1.28, deficit -0.02
                "8-Iron": [1.29, 1.29, 1.29],  # expected 1.30, deficit 0.01
            }
        )
        assert signal is None

    def test_unrecognized_club_names_are_ignored(self) -> None:
        assert detect_iron_strike_weakness({"Rescue Club": [1.10, 1.10, 1.10]}) is None

    def test_every_expected_club_is_a_recognized_iron(self) -> None:
        assert set(EXPECTED_SMASH_FACTOR_BY_IRON.keys()) == {
            "2-Iron", "3-Iron", "4-Iron", "5-Iron", "6-Iron", "7-Iron", "8-Iron", "9-Iron",
        }


class TestDetectPuttingLagWeakness:
    def test_flags_low_efficiency(self) -> None:
        signal = detect_putting_lag_weakness(50.0, lag_putt_count=6)
        assert signal is not None
        assert signal.weakness == Weakness.putting_lag_speed

    def test_no_signal_above_threshold(self) -> None:
        assert detect_putting_lag_weakness(85.0, lag_putt_count=6) is None

    def test_flags_short_of_the_prd_target_even_if_not_terrible(self) -> None:
        # Calibrated to PRD §7.1's own 80% target, not a softer bar.
        assert detect_putting_lag_weakness(75.0, lag_putt_count=6) is not None

    def test_no_signal_below_minimum_sample(self) -> None:
        assert detect_putting_lag_weakness(0.0, lag_putt_count=1) is None

    def test_no_signal_when_none(self) -> None:
        assert detect_putting_lag_weakness(None, lag_putt_count=10) is None


class TestRecommendCombines:
    def test_every_weakness_has_exactly_one_combine(self) -> None:
        assert set(COMBINES.keys()) == set(Weakness)

    def test_maps_signals_to_the_matching_combine_in_order(self) -> None:
        signal = detect_approach_weakness([-1.0, -1.0, -1.0, -1.0, -1.0])
        assert signal is not None

        combines = recommend_combines([signal])

        assert len(combines) == 1
        assert combines[0].name == "9-Ball Wedge Matrix"
