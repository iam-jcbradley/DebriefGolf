from unittest.mock import patch

from fastapi.testclient import TestClient

from app.services.geometry import LatLng
from app.services.osm_courses import (
    OsmCourseDetail,
    OsmCourseSummary,
    OsmHoleCandidate,
    OsmLookupError,
)


def _payload(**overrides) -> dict:
    payload = {
        "name": "Test Creek Golf Club",
        "city": "Testville",
        "state": "SC",
        "holes": [
            {
                "number": 1,
                "par": 4,
                "yardage": 400,
                "tee_location": {"lat": 33.7000, "lng": -78.9000},
                "green_center": {"lat": 33.7025, "lng": -78.9000},
                "green_boundary": [
                    {"lat": 33.70255, "lng": -78.90005},
                    {"lat": 33.70255, "lng": -78.89995},
                    {"lat": 33.70245, "lng": -78.89995},
                    {"lat": 33.70245, "lng": -78.90005},
                ],
            },
            {"number": 2, "par": 3, "yardage": 175},  # no geometry — allowed
        ],
    }
    payload.update(overrides)
    return payload


def test_create_course_persists_holes_and_geometry(client: TestClient) -> None:
    response = client.post("/api/courses", json=_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert len(body["holes"]) == 2

    hole_1 = next(h for h in body["holes"] if h["hole_number"] == 1)
    assert hole_1["par"] == 4
    assert hole_1["tee"] == {"lat": 33.7000, "lng": -78.9000}
    assert hole_1["green_center"] == {"lat": 33.7025, "lng": -78.9000}
    assert len(hole_1["green_boundary"]) == 5  # closed ring: 4 points + repeat of first

    hole_2 = next(h for h in body["holes"] if h["hole_number"] == 2)
    assert hole_2["tee"] is None
    assert hole_2["green_center"] is None
    assert hole_2["green_boundary"] is None


def test_create_course_rejects_duplicate_hole_numbers(client: TestClient) -> None:
    payload = _payload(
        holes=[
            {"number": 1, "par": 4, "yardage": 400},
            {"number": 1, "par": 3, "yardage": 150},
        ]
    )

    response = client.post("/api/courses", json=payload)

    assert response.status_code == 422


def test_create_course_idempotent_on_osm_relation_id(client: TestClient) -> None:
    payload = _payload(osm_relation_id=12345678)

    first = client.post("/api/courses", json=payload)
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = client.post("/api/courses", json=payload)
    assert second.status_code == 200
    assert second.json()["id"] == first_id


def test_get_course_returns_holes(client: TestClient) -> None:
    created = client.post("/api/courses", json=_payload()).json()

    response = client.get(f"/api/courses/{created['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == created["name"]
    assert len(response.json()["holes"]) == 2


def test_get_course_404_for_unknown_course(client: TestClient) -> None:
    response = client.get("/api/courses/999999")
    assert response.status_code == 404


def test_search_osm_returns_summaries(client: TestClient) -> None:
    fake_results = [
        OsmCourseSummary(
            osm_type="way", osm_id=123, name="Pinehurst Creek", city="PI", state="SC",
            center=LatLng(33.7, -78.9),
        )
    ]
    with patch("app.api.routes.courses.search_courses", return_value=fake_results):
        response = client.get("/api/courses/search-osm", params={"q": "Pinehurst"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "osm_type": "way", "osm_id": 123, "name": "Pinehurst Creek",
            "city": "PI", "state": "SC", "center": {"lat": 33.7, "lng": -78.9},
        }
    ]


def test_search_osm_503_on_lookup_error(client: TestClient) -> None:
    with patch("app.api.routes.courses.search_courses", side_effect=OsmLookupError("blocked")):
        response = client.get("/api/courses/search-osm", params={"q": "Pinehurst"})
    assert response.status_code == 503


def test_search_osm_geometry_returns_draft_holes(client: TestClient) -> None:
    fake_detail = OsmCourseDetail(
        osm_id=999,
        name="Test Creek GC",
        city="Testville",
        state="SC",
        holes=[
            OsmHoleCandidate(
                number=1, par=4, yardage=302,
                tee_location=LatLng(33.7000, -78.9000),
                green_center=LatLng(33.7025, -78.9000),
                green_boundary=[LatLng(33.70255, -78.90005), LatLng(33.70245, -78.89995)],
            ),
            OsmHoleCandidate(
                number=None, par=None, yardage=None,
                tee_location=None, green_center=None, green_boundary=None,
            ),
        ],
    )
    with patch("app.api.routes.courses.fetch_course_geometry", return_value=fake_detail):
        response = client.get("/api/courses/search-osm/way/999")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Test Creek GC"
    assert body["osm_relation_id"] == 999
    assert len(body["holes"]) == 2
    assert body["holes"][0]["tee_location"] == {"lat": 33.7000, "lng": -78.9000}
    assert body["holes"][0]["green_boundary"] == [
        {"lat": 33.70255, "lng": -78.90005}, {"lat": 33.70245, "lng": -78.89995}
    ]
    assert body["holes"][1]["tee_location"] is None


def test_search_osm_geometry_rejects_bad_osm_type(client: TestClient) -> None:
    response = client.get("/api/courses/search-osm/bogus/999")
    assert response.status_code == 422


def test_search_osm_geometry_503_on_lookup_error(client: TestClient) -> None:
    with patch(
        "app.api.routes.courses.fetch_course_geometry", side_effect=OsmLookupError("blocked")
    ):
        response = client.get("/api/courses/search-osm/way/999")
    assert response.status_code == 503


def test_list_courses_includes_created_course(client: TestClient) -> None:
    created = client.post("/api/courses", json=_payload()).json()

    response = client.get("/api/courses")

    assert response.status_code == 200
    assert any(c["id"] == created["id"] for c in response.json())
