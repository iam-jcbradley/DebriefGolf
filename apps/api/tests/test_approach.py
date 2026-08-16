from app.models.shot import Lie, Shot
from app.services.approach import (
    SHORT_SIDE_GREEN_RATIO,
    SHORT_SIDE_PROXIMITY_YARDS,
    ApproachLeave,
    HoleGeometryContext,
    classify_approach_leave,
)
from app.services.geometry import YARDS_PER_DEGREE_LAT, LatLng

# Same due-north-aim-line trick test_geometry.py uses: with the tee at the
# equator and the green directly north, longitudinal = north-offset and
# lateral = east-offset, with no rotation to hand-compute around.
TEE = LatLng(lat=0.0, lng=0.0)
GREEN = LatLng(lat=400 / YARDS_PER_DEGREE_LAT, lng=0.0)


def _point(longitudinal_yards: float, lateral_yards: float) -> LatLng:
    return LatLng(
        lat=longitudinal_yards / YARDS_PER_DEGREE_LAT, lng=lateral_yards / YARDS_PER_DEGREE_LAT
    )


# A green centered on the aim line, +-15 yards laterally and 390-410
# longitudinally — a simple rectangle, real enough to hand-verify extents
# against.
GREEN_BOUNDARY = [
    _point(390, -15),
    _point(390, 15),
    _point(410, 15),
    _point(410, -15),
]


def _approach(end_lie: Lie, end_distance: float) -> Shot:
    return Shot(
        round_id=1, hole_id=1, shot_number=1, club="7-Iron",
        start_lie=Lie.fairway, end_lie=end_lie,
        start_distance_yards=150, end_distance_yards=end_distance,
    )


class TestOnGreenAndUnclassified:
    def test_shot_that_reaches_the_green_is_on_green(self) -> None:
        shot = _approach(Lie.green, end_distance=5.0)
        assert classify_approach_leave(shot) == ApproachLeave.on_green

    def test_tee_or_penalty_end_lie_is_unclassified(self) -> None:
        shot = _approach(Lie.penalty, end_distance=140)
        assert classify_approach_leave(shot) == ApproachLeave.unclassified


class TestGeometricRule:
    """Hand-computed quadrant cases: a pin tucked toward each edge of the
    green, missed on the tight side (short-sided) and the roomy side (safe
    leave). Regression coverage for the actual rule Phase 14 exists to add
    — see app/services/geometry.py's green_extent_beyond_point for the
    extent math these numbers depend on."""

    def test_pin_tucked_left_miss_left_is_short_sided(self) -> None:
        # Pin at lateral -10: 5 yards of green to its left (edge at -15),
        # 25 yards to its right (edge at +15). A miss further left (-12)
        # is on the 5-yard side.
        geometry = HoleGeometryContext(
            tee=TEE, green_center=GREEN, green_boundary=GREEN_BOUNDARY, pin=_point(400, -10)
        )
        shot = _approach(Lie.fringe, end_distance=25)  # far enough proxy would say "safe"
        result = classify_approach_leave(shot, shot_location=_point(400, -12), geometry=geometry)
        assert result == ApproachLeave.short_sided

    def test_pin_tucked_left_miss_right_is_safe_leave(self) -> None:
        geometry = HoleGeometryContext(
            tee=TEE, green_center=GREEN, green_boundary=GREEN_BOUNDARY, pin=_point(400, -10)
        )
        shot = _approach(Lie.rough, end_distance=25)
        result = classify_approach_leave(shot, shot_location=_point(400, 5), geometry=geometry)
        assert result == ApproachLeave.safe_leave

    def test_pin_tucked_right_miss_right_is_short_sided(self) -> None:
        # Mirror image: pin at +10, 5 yards to its right, 25 to its left.
        geometry = HoleGeometryContext(
            tee=TEE, green_center=GREEN, green_boundary=GREEN_BOUNDARY, pin=_point(400, 10)
        )
        shot = _approach(Lie.sand, end_distance=25)
        result = classify_approach_leave(shot, shot_location=_point(400, 12), geometry=geometry)
        assert result == ApproachLeave.short_sided

    def test_pin_tucked_right_miss_left_is_safe_leave(self) -> None:
        geometry = HoleGeometryContext(
            tee=TEE, green_center=GREEN, green_boundary=GREEN_BOUNDARY, pin=_point(400, 10)
        )
        shot = _approach(Lie.recovery, end_distance=25)
        result = classify_approach_leave(shot, shot_location=_point(400, -5), geometry=geometry)
        assert result == ApproachLeave.safe_leave

    def test_ratio_boundary_is_exact(self) -> None:
        # Pin dead center (extent 15 both sides). A miss exactly at the
        # SHORT_SIDE_GREEN_RATIO cutoff should not count as short-sided —
        # the rule is a strict "<", not "<=".
        geometry = HoleGeometryContext(
            tee=TEE, green_center=GREEN, green_boundary=GREEN_BOUNDARY, pin=_point(400, 0)
        )
        cutoff_lateral = 15 * SHORT_SIDE_GREEN_RATIO  # green extent on the far side is 15
        shot = _approach(Lie.fringe, end_distance=25)
        result = classify_approach_leave(
            shot, shot_location=_point(400, -(15 - cutoff_lateral)), geometry=geometry
        )
        assert result == ApproachLeave.safe_leave

    def test_on_green_skips_geometry_entirely(self) -> None:
        geometry = HoleGeometryContext(
            tee=TEE, green_center=GREEN, green_boundary=GREEN_BOUNDARY, pin=_point(400, -10)
        )
        shot = _approach(Lie.green, end_distance=3)
        result = classify_approach_leave(shot, shot_location=_point(400, -12), geometry=geometry)
        assert result == ApproachLeave.on_green


class TestFallsBackToTheProxy:
    """The distance/lie proxy from before Phase 14, now the fallback path
    for whenever the geometric rule can't run — no pin, no green boundary,
    or no shot GPS. These are the same cases the pre-Phase-14 version of
    this module asserted; they describe the fallback now, not the primary
    rule."""

    def test_tight_miss_from_sand_is_short_sided(self) -> None:
        shot = _approach(Lie.sand, end_distance=SHORT_SIDE_PROXIMITY_YARDS - 1)
        assert classify_approach_leave(shot) == ApproachLeave.short_sided

    def test_roomy_miss_from_rough_is_safe_leave(self) -> None:
        shot = _approach(Lie.rough, end_distance=SHORT_SIDE_PROXIMITY_YARDS + 1)
        assert classify_approach_leave(shot) == ApproachLeave.safe_leave

    def test_boundary_distance_counts_as_short_sided(self) -> None:
        shot = _approach(Lie.fringe, end_distance=SHORT_SIDE_PROXIMITY_YARDS)
        assert classify_approach_leave(shot) == ApproachLeave.short_sided

    def test_recovery_lie_within_proximity_is_short_sided(self) -> None:
        shot = _approach(Lie.recovery, end_distance=5.0)
        assert classify_approach_leave(shot) == ApproachLeave.short_sided

    def test_no_pin_falls_back_to_proxy(self) -> None:
        geometry = HoleGeometryContext(
            tee=TEE, green_center=GREEN, green_boundary=GREEN_BOUNDARY, pin=None
        )
        shot = _approach(Lie.fringe, end_distance=SHORT_SIDE_PROXIMITY_YARDS - 1)
        result = classify_approach_leave(shot, shot_location=_point(400, -12), geometry=geometry)
        assert result == ApproachLeave.short_sided

    def test_no_green_boundary_falls_back_to_proxy(self) -> None:
        geometry = HoleGeometryContext(
            tee=TEE, green_center=GREEN, green_boundary=None, pin=_point(400, -10)
        )
        shot = _approach(Lie.rough, end_distance=SHORT_SIDE_PROXIMITY_YARDS + 1)
        result = classify_approach_leave(shot, shot_location=_point(400, -12), geometry=geometry)
        assert result == ApproachLeave.safe_leave

    def test_no_shot_location_falls_back_to_proxy(self) -> None:
        geometry = HoleGeometryContext(
            tee=TEE, green_center=GREEN, green_boundary=GREEN_BOUNDARY, pin=_point(400, -10)
        )
        shot = _approach(Lie.sand, end_distance=SHORT_SIDE_PROXIMITY_YARDS - 1)
        result = classify_approach_leave(shot, shot_location=None, geometry=geometry)
        assert result == ApproachLeave.short_sided

    def test_degenerate_hole_geometry_falls_back_rather_than_raising(self) -> None:
        geometry = HoleGeometryContext(
            tee=TEE, green_center=TEE, green_boundary=GREEN_BOUNDARY, pin=TEE
        )
        shot = _approach(Lie.rough, end_distance=SHORT_SIDE_PROXIMITY_YARDS + 1)
        result = classify_approach_leave(shot, shot_location=_point(400, -12), geometry=geometry)
        assert result == ApproachLeave.safe_leave
