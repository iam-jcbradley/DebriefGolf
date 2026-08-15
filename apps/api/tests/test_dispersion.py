import pytest

from app.services.dispersion import compute_dispersion_ellipse, is_within_ellipse


class TestComputeDispersionEllipse:
    def test_bounds_match_known_mean_and_stdev(self) -> None:
        ellipse = compute_dispersion_ellipse(
            longitudinal_mean_yards=150.0, longitudinal_stdev_yards=10.0,
            lateral_mean_yards=2.0, lateral_stdev_yards=5.0, k=1.5,
        )
        assert ellipse.center_longitudinal_yards == 150.0
        assert ellipse.center_lateral_yards == 2.0
        assert ellipse.semi_major_yards == pytest.approx(15.0)
        assert ellipse.semi_minor_yards == pytest.approx(7.5)
        assert ellipse.k == 1.5

    def test_default_k_is_used_when_omitted(self) -> None:
        ellipse = compute_dispersion_ellipse(100.0, 10.0, 0.0, 4.0)
        assert ellipse.k == 1.5
        assert ellipse.semi_major_yards == pytest.approx(15.0)
        assert ellipse.semi_minor_yards == pytest.approx(6.0)

    def test_zero_stdev_gives_a_degenerate_point_ellipse(self) -> None:
        ellipse = compute_dispersion_ellipse(150.0, 0.0, 0.0, 0.0)
        assert ellipse.semi_major_yards == 0.0
        assert ellipse.semi_minor_yards == 0.0

    def test_negative_stdev_raises(self) -> None:
        with pytest.raises(ValueError, match="standard deviation"):
            compute_dispersion_ellipse(150.0, -1.0, 0.0, 5.0)
        with pytest.raises(ValueError, match="standard deviation"):
            compute_dispersion_ellipse(150.0, 10.0, 0.0, -1.0)

    def test_non_positive_k_raises(self) -> None:
        with pytest.raises(ValueError, match="k must be > 0"):
            compute_dispersion_ellipse(150.0, 10.0, 0.0, 5.0, k=0)
        with pytest.raises(ValueError, match="k must be > 0"):
            compute_dispersion_ellipse(150.0, 10.0, 0.0, 5.0, k=-1)


class TestIsWithinEllipse:
    def test_center_point_is_within(self) -> None:
        ellipse = compute_dispersion_ellipse(150.0, 10.0, 0.0, 5.0, k=1.0)
        assert is_within_ellipse(ellipse, 150.0, 0.0) is True

    def test_point_on_the_major_axis_boundary_is_within(self) -> None:
        ellipse = compute_dispersion_ellipse(150.0, 10.0, 0.0, 5.0, k=1.0)
        assert is_within_ellipse(ellipse, 160.0, 0.0) is True  # exactly at +semi_major

    def test_point_just_past_the_major_axis_boundary_is_outside(self) -> None:
        ellipse = compute_dispersion_ellipse(150.0, 10.0, 0.0, 5.0, k=1.0)
        assert is_within_ellipse(ellipse, 160.01, 0.0) is False

    def test_point_on_the_minor_axis_boundary_is_within(self) -> None:
        ellipse = compute_dispersion_ellipse(150.0, 10.0, 0.0, 5.0, k=1.0)
        assert is_within_ellipse(ellipse, 150.0, 5.0) is True

    def test_diagonal_point_exactly_on_boundary(self) -> None:
        # semi_major=4, semi_minor=3; (4*0.6, 3*0.8) satisfies 0.6^2+0.8^2=1 exactly.
        ellipse = compute_dispersion_ellipse(0.0, 4.0, 0.0, 3.0, k=1.0)
        assert is_within_ellipse(ellipse, 2.4, 2.4) is True

    def test_diagonal_point_outside(self) -> None:
        ellipse = compute_dispersion_ellipse(0.0, 4.0, 0.0, 3.0, k=1.0)
        assert is_within_ellipse(ellipse, 3.0, 3.0) is False

    def test_degenerate_point_ellipse_only_contains_the_center(self) -> None:
        ellipse = compute_dispersion_ellipse(150.0, 0.0, 0.0, 0.0)
        assert is_within_ellipse(ellipse, 150.0, 0.0) is True
        assert is_within_ellipse(ellipse, 150.1, 0.0) is False
