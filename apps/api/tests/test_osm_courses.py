import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.services.osm_courses import (
    OsmLookupError,
    fetch_course_geometry,
    search_courses,
)


def _response(status_code: int, json_body: dict | None = None, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    if json_body is not None:
        response.json.return_value = json_body
    return response


class TestSearchCourses:
    def test_returns_named_matches(self) -> None:
        body = {
            "elements": [
                {
                    "type": "way",
                    "id": 123456,
                    "center": {"lat": 33.7, "lon": -78.9},
                    "tags": {
                        "name": "Pinehurst Creek Golf Club",
                        "leisure": "golf_course",
                        "addr:city": "Pawleys Island",
                        "addr:state": "SC",
                    },
                },
                {
                    "type": "relation",
                    "id": 789,
                    "center": {"lat": 40.0, "lon": -75.0},
                    "tags": {"name": "Other Creek Golf Club"},
                },
            ]
        }
        with patch("httpx.AsyncClient.post", return_value=_response(200, body)):
            results = asyncio.run(search_courses("Creek"))

        assert len(results) == 2
        first = results[0]
        assert first.osm_type == "way"
        assert first.osm_id == 123456
        assert first.name == "Pinehurst Creek Golf Club"
        assert first.city == "Pawleys Island"
        assert first.state == "SC"
        assert first.center.lat == pytest.approx(33.7)
        assert first.center.lng == pytest.approx(-78.9)

        second = results[1]
        assert second.city is None
        assert second.state is None

    def test_skips_elements_without_a_name(self) -> None:
        body = {"elements": [{"type": "way", "id": 1, "tags": {"leisure": "golf_course"}}]}
        with patch("httpx.AsyncClient.post", return_value=_response(200, body)):
            results = asyncio.run(search_courses("anything"))
        assert results == []

    def test_non_200_raises_lookup_error(self) -> None:
        with patch(
            "httpx.AsyncClient.post", return_value=_response(504, text="Gateway Timeout")
        ):
            with pytest.raises(OsmLookupError, match="504"):
                asyncio.run(search_courses("anything"))


# A hole running due north for ~277 yards (same fixture geometry used
# elsewhere in the test suite, e.g. tests/test_hole_replay_routes.py) with a
# tee node exactly at its start and a green way centered on its end.
_TEE_LAT, _TEE_LNG = 33.7000, -78.9000
_GREEN_LAT, _GREEN_LNG = 33.7025, -78.9000


def _hole_element(number: str | None = "1", par: str | None = "4") -> dict:
    tags = {"golf": "hole"}
    if number is not None:
        tags["ref"] = number
    if par is not None:
        tags["par"] = par
    return {
        "type": "way",
        "id": 111,
        "tags": tags,
        "geometry": [{"lat": _TEE_LAT, "lon": _TEE_LNG}, {"lat": _GREEN_LAT, "lon": _GREEN_LNG}],
    }


def _tee_node_element() -> dict:
    return {"type": "node", "id": 222, "tags": {"golf": "tee"}, "lat": _TEE_LAT, "lon": _TEE_LNG}


def _green_way_element() -> dict:
    d = 0.0001
    return {
        "type": "way",
        "id": 333,
        "tags": {"golf": "green"},
        "geometry": [
            {"lat": _GREEN_LAT - d, "lon": _GREEN_LNG - d},
            {"lat": _GREEN_LAT - d, "lon": _GREEN_LNG + d},
            {"lat": _GREEN_LAT + d, "lon": _GREEN_LNG + d},
            {"lat": _GREEN_LAT + d, "lon": _GREEN_LNG - d},
        ],
    }


class TestFetchCourseGeometry:
    def test_matches_hole_to_nearest_tee_and_green(self) -> None:
        geometry_body = {
            "elements": [_hole_element(), _tee_node_element(), _green_way_element()]
        }
        course_body = {
            "elements": [
                {
                    "type": "way",
                    "id": 999,
                    "tags": {"name": "Test Creek GC", "addr:city": "Testville", "addr:state": "SC"},
                }
            ]
        }
        with patch(
            "httpx.AsyncClient.post",
            side_effect=[_response(200, geometry_body), _response(200, course_body)],
        ):
            detail = asyncio.run(fetch_course_geometry("way", 999))

        assert detail.name == "Test Creek GC"
        assert detail.city == "Testville"
        assert len(detail.holes) == 1

        hole = detail.holes[0]
        assert hole.number == 1
        assert hole.par == 4
        assert hole.tee_location.lat == pytest.approx(_TEE_LAT)
        assert hole.tee_location.lng == pytest.approx(_TEE_LNG)
        assert hole.green_center.lat == pytest.approx(_GREEN_LAT)
        assert hole.green_center.lng == pytest.approx(_GREEN_LNG)
        assert hole.green_boundary is not None
        assert len(hole.green_boundary) == 4
        # tee->green is due north ~302 yards (0.0025 deg lat * 121,000
        # yards/deg); computed from the hole way's own geometry, independent
        # of the matched tee/green features.
        assert hole.yardage == pytest.approx(302, abs=2)

    def test_falls_back_to_hole_endpoint_when_no_tee_or_green_feature_nearby(self) -> None:
        geometry_body = {"elements": [_hole_element()]}  # no tee/green features at all
        course_body = {"elements": [{"type": "way", "id": 999, "tags": {"name": "Bare Course"}}]}
        with patch(
            "httpx.AsyncClient.post",
            side_effect=[_response(200, geometry_body), _response(200, course_body)],
        ):
            detail = asyncio.run(fetch_course_geometry("way", 999))

        hole = detail.holes[0]
        assert hole.tee_location.lat == pytest.approx(_TEE_LAT)
        assert hole.green_center.lat == pytest.approx(_GREEN_LAT)
        assert hole.green_boundary is None  # a bare fallback point isn't a polygon

    def test_ignores_a_green_feature_far_from_the_hole(self) -> None:
        far_green = _green_way_element()
        for pt in far_green["geometry"]:
            pt["lat"] += 1.0  # ~121,000 yards away — nowhere near the match radius
        geometry_body = {"elements": [_hole_element(), far_green]}
        course_body = {"elements": [{"type": "way", "id": 999, "tags": {"name": "X"}}]}
        with patch(
            "httpx.AsyncClient.post",
            side_effect=[_response(200, geometry_body), _response(200, course_body)],
        ):
            detail = asyncio.run(fetch_course_geometry("way", 999))

        hole = detail.holes[0]
        # falls back to the hole way's own endpoint, not the far-away green
        assert hole.green_center.lat == pytest.approx(_GREEN_LAT)
        assert hole.green_boundary is None

    def test_hole_without_ref_tag_has_no_number(self) -> None:
        geometry_body = {"elements": [_hole_element(number=None)]}
        course_body = {"elements": [{"type": "way", "id": 999, "tags": {"name": "X"}}]}
        with patch(
            "httpx.AsyncClient.post",
            side_effect=[_response(200, geometry_body), _response(200, course_body)],
        ):
            detail = asyncio.run(fetch_course_geometry("way", 999))

        assert detail.holes[0].number is None

    def test_holes_without_ref_sort_after_numbered_holes(self) -> None:
        numbered = _hole_element(number="2")
        numbered["id"] = 1
        unnumbered = _hole_element(number=None)
        unnumbered["id"] = 2
        geometry_body = {"elements": [unnumbered, numbered]}
        course_body = {"elements": [{"type": "way", "id": 999, "tags": {"name": "X"}}]}
        with patch(
            "httpx.AsyncClient.post",
            side_effect=[_response(200, geometry_body), _response(200, course_body)],
        ):
            detail = asyncio.run(fetch_course_geometry("way", 999))

        assert [h.number for h in detail.holes] == [2, None]
