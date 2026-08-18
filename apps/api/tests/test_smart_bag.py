from app.services.smart_bag import (
    ClubGappingStats,
    build_club_gapping,
    compute_dispersion,
    compute_gaps,
    reject_outliers_iqr,
    sort_by_club_order,
)


class TestRejectOutliersIqr:
    def test_too_few_samples_returned_unchanged(self) -> None:
        samples = [150.0, 200.0, 5000.0]  # only 3 samples, below MIN_SAMPLES_FOR_IQR
        assert reject_outliers_iqr(samples) == samples

    def test_synthetic_outlier_is_excluded(self) -> None:
        samples = [148.0, 150.0, 151.0, 149.0, 152.0, 400.0]  # 400 is a bogus outlier
        filtered = reject_outliers_iqr(samples)
        assert 400.0 not in filtered
        assert set(filtered) == {148.0, 150.0, 151.0, 149.0, 152.0}

    def test_tight_cluster_keeps_everything(self) -> None:
        samples = [148.0, 149.0, 150.0, 151.0, 152.0]
        assert reject_outliers_iqr(samples) == samples


class TestComputeDispersion:
    def test_empty_samples(self) -> None:
        stats = compute_dispersion([])
        assert stats.count == 0
        assert stats.mean == 0.0
        assert stats.excluded_outliers == 0

    def test_basic_stats(self) -> None:
        stats = compute_dispersion([148.0, 150.0, 152.0])
        assert stats.count == 3
        assert stats.mean == 150.0
        assert stats.median == 150.0
        assert stats.excluded_outliers == 0

    def test_outlier_excluded_from_reported_stats(self) -> None:
        samples = [148.0, 150.0, 151.0, 149.0, 152.0, 400.0]
        stats = compute_dispersion(samples)
        assert stats.count == 5
        assert stats.excluded_outliers == 1
        assert stats.mean < 200  # would be ~192 if the outlier were included

    def test_single_sample_has_zero_stdev(self) -> None:
        stats = compute_dispersion([150.0])
        assert stats.stdev == 0.0


class TestBuildClubGapping:
    """`build_club_gapping` pairs already-computed carry `DispersionStats`
    (the SQL push-down's output — see tests/test_shot_queries.py) with
    lateral dispersion, still computed here from raw samples."""

    def test_multiple_clubs_independent_stats(self) -> None:
        stats = build_club_gapping(
            {
                "Driver": compute_dispersion([250.0, 255.0, 245.0]),
                "7-Iron": compute_dispersion([150.0, 152.0, 148.0]),
            }
        )
        by_club = {s.club: s for s in stats}
        assert by_club["Driver"].carry.mean == 250.0
        assert by_club["7-Iron"].carry.mean == 150.0
        assert by_club["Driver"].lateral is None

    def test_lateral_stats_populated_when_provided(self) -> None:
        stats = build_club_gapping(
            {"Driver": compute_dispersion([250.0, 255.0, 245.0])},
            lateral_by_club={"Driver": [-5.0, 3.0, -1.0]},
        )
        assert stats[0].lateral is not None
        assert stats[0].lateral.count == 3


class TestClubGaps:
    def test_sort_by_club_order(self) -> None:
        stats = [
            ClubGappingStats(club="7-Iron", carry=compute_dispersion([150])),
            ClubGappingStats(club="Driver", carry=compute_dispersion([250])),
            ClubGappingStats(club="PW", carry=compute_dispersion([120])),
        ]
        ordered = sort_by_club_order(stats)
        assert [s.club for s in ordered] == ["Driver", "7-Iron", "PW"]

    def test_unknown_club_sorts_last(self) -> None:
        stats = [
            ClubGappingStats(club="Mystery Club", carry=compute_dispersion([100])),
            ClubGappingStats(club="Driver", carry=compute_dispersion([250])),
        ]
        ordered = sort_by_club_order(stats)
        assert [s.club for s in ordered] == ["Driver", "Mystery Club"]

    def test_compute_gaps_between_consecutive_clubs(self) -> None:
        stats = [
            ClubGappingStats(club="Driver", carry=compute_dispersion([250, 250, 250])),
            ClubGappingStats(club="3-Wood", carry=compute_dispersion([230, 230, 230])),
            ClubGappingStats(club="7-Iron", carry=compute_dispersion([150, 150, 150])),
        ]
        gaps = compute_gaps(stats)
        assert len(gaps) == 2
        assert gaps[0].longer_club == "Driver"
        assert gaps[0].shorter_club == "3-Wood"
        assert gaps[0].carry_gap_yards == 20.0
        assert gaps[1].carry_gap_yards == 80.0

    def test_unrecognized_club_excluded_from_gaps(self) -> None:
        stats = [
            ClubGappingStats(club="Driver", carry=compute_dispersion([250])),
            ClubGappingStats(club="Mystery Club", carry=compute_dispersion([200])),
            ClubGappingStats(club="7-Iron", carry=compute_dispersion([150])),
        ]
        gaps = compute_gaps(stats)
        assert len(gaps) == 1
        assert gaps[0].longer_club == "Driver"
        assert gaps[0].shorter_club == "7-Iron"

    def test_club_with_no_surviving_samples_excluded_from_gaps(self) -> None:
        stats = [
            ClubGappingStats(club="Driver", carry=compute_dispersion([250])),
            ClubGappingStats(club="3-Wood", carry=compute_dispersion([])),
            ClubGappingStats(club="7-Iron", carry=compute_dispersion([150])),
        ]
        gaps = compute_gaps(stats)
        assert len(gaps) == 1
        assert gaps[0].shorter_club == "7-Iron"
