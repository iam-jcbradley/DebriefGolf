import pytest

from app.services.geometry import (
    YARDS_PER_DEGREE_LAT,
    LatLng,
    ShotGeometryRow,
    compute_lateral_by_club,
    local_yards,
    offset_from_aim_line,
)

# A due-north aim line makes the expected offsets hand-computable: with the
# tee at the equator and the green directly north, the aim line's "east"
# component is exactly zero, so longitudinal = north-offset and
# lateral = east-offset, with no rotation to account for.
TEE = LatLng(lat=0.0, lng=0.0)


def _green(yardage: float) -> LatLng:
    return LatLng(lat=yardage / YARDS_PER_DEGREE_LAT, lng=0.0)


def _east_of_tee(yards: float) -> LatLng:
    return LatLng(lat=0.0, lng=yards / YARDS_PER_DEGREE_LAT)  # cos(0) == 1


def _north_of_tee(yards: float) -> LatLng:
    return LatLng(lat=yards / YARDS_PER_DEGREE_LAT, lng=0.0)


class TestLocalYards:
    def test_origin_offset_is_zero(self) -> None:
        east, north = local_yards(TEE, TEE)
        assert east == pytest.approx(0.0)
        assert north == pytest.approx(0.0)

    def test_north_offset(self) -> None:
        east, north = local_yards(TEE, _north_of_tee(100))
        assert north == pytest.approx(100.0)
        assert east == pytest.approx(0.0, abs=1e-6)

    def test_east_offset(self) -> None:
        east, north = local_yards(TEE, _east_of_tee(50))
        assert east == pytest.approx(50.0)
        assert north == pytest.approx(0.0, abs=1e-6)


class TestOffsetFromAimLine:
    def test_point_at_green_is_full_longitudinal_no_lateral(self) -> None:
        green = _green(400)
        offset = offset_from_aim_line(TEE, green, green)
        assert offset.longitudinal_yards == pytest.approx(400.0)
        assert offset.lateral_yards == pytest.approx(0.0, abs=1e-6)

    def test_point_at_tee_is_zero_both_ways(self) -> None:
        offset = offset_from_aim_line(TEE, _green(400), TEE)
        assert offset.longitudinal_yards == pytest.approx(0.0, abs=1e-6)
        assert offset.lateral_yards == pytest.approx(0.0, abs=1e-6)

    def test_point_east_of_aim_line_is_positive_lateral(self) -> None:
        green = _green(400)
        point = LatLng(lat=200 / YARDS_PER_DEGREE_LAT, lng=15 / YARDS_PER_DEGREE_LAT)
        offset = offset_from_aim_line(TEE, green, point)
        assert offset.longitudinal_yards == pytest.approx(200.0)
        assert offset.lateral_yards == pytest.approx(15.0)

    def test_point_west_of_aim_line_is_negative_lateral(self) -> None:
        green = _green(400)
        point = LatLng(lat=200 / YARDS_PER_DEGREE_LAT, lng=-15 / YARDS_PER_DEGREE_LAT)
        offset = offset_from_aim_line(TEE, green, point)
        assert offset.lateral_yards == pytest.approx(-15.0)

    def test_point_behind_tee_is_negative_longitudinal(self) -> None:
        green = _green(400)
        point = _north_of_tee(-20)
        offset = offset_from_aim_line(TEE, green, point)
        assert offset.longitudinal_yards == pytest.approx(-20.0)

    def test_point_beyond_green_is_longitudinal_greater_than_hole_length(self) -> None:
        green = _green(400)
        point = _north_of_tee(420)
        offset = offset_from_aim_line(TEE, green, point)
        assert offset.longitudinal_yards == pytest.approx(420.0)

    def test_raises_when_tee_and_green_coincide(self) -> None:
        with pytest.raises(ValueError, match="coincide"):
            offset_from_aim_line(TEE, TEE, TEE)


def _row(club: str, lateral_yards: float, longitudinal_yards: float = 150.0) -> ShotGeometryRow:
    green = _green(400)
    point = LatLng(
        lat=longitudinal_yards / YARDS_PER_DEGREE_LAT,
        lng=lateral_yards / YARDS_PER_DEGREE_LAT,
    )
    return ShotGeometryRow(
        club=club,
        shot_lat=point.lat, shot_lng=point.lng,
        tee_lat=TEE.lat, tee_lng=TEE.lng,
        green_lat=green.lat, green_lng=green.lng,
    )


class TestComputeLateralByClub:
    def test_groups_offsets_by_club(self) -> None:
        rows = [_row("7-Iron", 5.0), _row("7-Iron", -3.0), _row("Driver", 12.0)]
        result = compute_lateral_by_club(rows)
        assert result["7-Iron"] == pytest.approx([5.0, -3.0])
        assert result["Driver"] == pytest.approx([12.0])

    def test_empty_input_gives_empty_result(self) -> None:
        assert compute_lateral_by_club([]) == {}

    def test_skips_a_degenerate_hole_without_failing_the_batch(self) -> None:
        degenerate = ShotGeometryRow(
            club="7-Iron",
            shot_lat=0.0, shot_lng=0.0,
            tee_lat=0.0, tee_lng=0.0,
            green_lat=0.0, green_lng=0.0,  # tee == green
        )
        rows = [degenerate, _row("7-Iron", 5.0)]
        result = compute_lateral_by_club(rows)
        assert result["7-Iron"] == pytest.approx([5.0])
