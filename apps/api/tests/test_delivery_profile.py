from datetime import UTC, datetime

from app.models.practice import PracticeShot
from app.services.delivery_profile import (
    ClubDeliveryProfile,
    SessionShotRow,
    compute_delivery_profile,
    compute_delivery_trend,
    compute_gapping_delta,
    face_to_path_deg,
)
from app.services.smart_bag import ClubGappingStats, DispersionStats


def _practice_shot(**kwargs) -> PracticeShot:
    defaults = dict(session_id=1, club="7-Iron")
    defaults.update(kwargs)
    return PracticeShot(**defaults)


class TestFaceToPathDeg:
    def test_computes_difference(self) -> None:
        shot = _practice_shot(face_angle_deg=2.0, club_path_deg=-1.5)
        assert face_to_path_deg(shot) == 3.5

    def test_missing_either_value_returns_none(self) -> None:
        assert face_to_path_deg(_practice_shot(face_angle_deg=None, club_path_deg=1.0)) is None
        assert face_to_path_deg(_practice_shot(face_angle_deg=1.0, club_path_deg=None)) is None


class TestComputeDeliveryProfile:
    def test_aggregates_per_club_averages(self) -> None:
        shots = [
            _practice_shot(club="7-Iron", smash_factor=1.30, carry_yards=150.0),
            _practice_shot(club="7-Iron", smash_factor=1.34, carry_yards=154.0),
            _practice_shot(club="Driver", smash_factor=1.48, carry_yards=250.0),
        ]

        profile = compute_delivery_profile(shots)

        by_club = {p.club: p for p in profile}
        assert by_club["7-Iron"].shot_count == 2
        assert by_club["7-Iron"].avg_smash_factor == 1.32
        assert by_club["7-Iron"].avg_carry_yards == 152.0
        assert by_club["Driver"].shot_count == 1

    def test_sorted_in_bag_order_not_input_order(self) -> None:
        shots = [_practice_shot(club="Putter"), _practice_shot(club="Driver")]
        profile = compute_delivery_profile(shots)
        assert [p.club for p in profile] == ["Driver", "Putter"]

    def test_missing_values_excluded_from_average(self) -> None:
        shots = [
            _practice_shot(club="7-Iron", smash_factor=1.30),
            _practice_shot(club="7-Iron", smash_factor=None),
        ]
        profile = compute_delivery_profile(shots)
        assert profile[0].avg_smash_factor == 1.30
        assert profile[0].shot_count == 2  # both shots still counted


class TestComputeDeliveryTrend:
    def test_groups_by_club_then_session_in_chronological_order(self) -> None:
        rows = [
            SessionShotRow(
                session_id=2,
                recorded_at=datetime(2026, 2, 1, tzinfo=UTC),
                shot=_practice_shot(club="Driver", carry_yards=260.0),
            ),
            SessionShotRow(
                session_id=1,
                recorded_at=datetime(2026, 1, 1, tzinfo=UTC),
                shot=_practice_shot(club="Driver", carry_yards=240.0),
            ),
        ]

        trend = compute_delivery_trend(rows)

        assert list(trend["Driver"][i].session_id for i in range(2)) == [1, 2]
        assert trend["Driver"][0].avg_carry_yards == 240.0
        assert trend["Driver"][1].avg_carry_yards == 260.0

    def test_no_rows_returns_empty(self) -> None:
        assert compute_delivery_trend([]) == {}


class TestComputeGappingDelta:
    def test_delta_is_range_minus_on_course(self) -> None:
        range_profiles = [
            ClubDeliveryProfile(
                club="Driver", shot_count=5, avg_club_path_deg=None, avg_face_angle_deg=None,
                avg_face_to_path_deg=None, avg_spin_axis_deg=None, avg_smash_factor=None,
                avg_carry_yards=260.0,
            )
        ]
        on_course_stats = [
            ClubGappingStats(
                club="Driver",
                carry=DispersionStats(
                    count=5, mean=245.0, median=245.0, stdev=5.0, excluded_outliers=0
                ),
            )
        ]

        deltas = compute_gapping_delta(range_profiles, on_course_stats)

        assert len(deltas) == 1
        assert deltas[0].club == "Driver"
        assert deltas[0].range_carry_mean_yards == 260.0
        assert deltas[0].on_course_carry_mean_yards == 245.0
        assert deltas[0].delta_yards == 15.0

    def test_club_present_in_only_one_source_gets_a_row_with_none_delta(self) -> None:
        range_profiles = [
            ClubDeliveryProfile(
                club="Driver", shot_count=5, avg_club_path_deg=None, avg_face_angle_deg=None,
                avg_face_to_path_deg=None, avg_spin_axis_deg=None, avg_smash_factor=None,
                avg_carry_yards=260.0,
            )
        ]

        deltas = compute_gapping_delta(range_profiles, [])

        assert len(deltas) == 1
        assert deltas[0].on_course_carry_mean_yards is None
        assert deltas[0].delta_yards is None
