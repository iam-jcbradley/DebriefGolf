from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlmodel import Session

from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, User


def _point(lat: float, lng: float) -> WKTElement:
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def _green_boundary(lat: float, lng: float) -> WKTElement:
    # a small square around (lat, lng), just needs to be a valid polygon
    d = 0.0001
    pts = [
        f"{lng - d} {lat - d}", f"{lng + d} {lat - d}",
        f"{lng + d} {lat + d}", f"{lng - d} {lat + d}",
        f"{lng - d} {lat - d}",
    ]
    return WKTElement(f"POLYGON(({', '.join(pts)}))", srid=4326)


def _seed_round_with_hole_geometry(session: Session, user: User) -> tuple[int, int]:
    """One hole with real tee/green/shot geometry. Returns (round_id, hole_number)."""
    course = Course(name="Replay Test Course")
    session.add(course)
    session.commit()
    session.refresh(course)

    tee_lat, tee_lng = 33.7000, -78.9000
    green_lat, green_lng = 33.7025, -78.9000  # due north, ~277 yards away

    hole = Hole(
        course_id=course.id, number=1, par=4, yardage=400,
        tee_location=_point(tee_lat, tee_lng),
        green_center=_point(green_lat, green_lng),
        green_boundary=_green_boundary(green_lat, green_lng),
    )
    session.add(hole)
    session.commit()
    session.refresh(hole)

    round_ = Round(
        user_id=user.id, course_id=course.id, total_score=4, status=RoundStatus.verified
    )
    session.add(round_)
    session.commit()
    session.refresh(round_)

    session.add_all(
        [
            Shot(
                round_id=round_.id, hole_id=hole.id, shot_number=1, club="Driver",
                start_lie=Lie.tee, end_lie=Lie.fairway,
                start_distance_yards=400, end_distance_yards=150,
                location=_point(33.7013, -78.9001),
            ),
            Shot(
                round_id=round_.id, hole_id=hole.id, shot_number=2, club="7-Iron",
                start_lie=Lie.fairway, end_lie=Lie.rough,
                start_distance_yards=150, end_distance_yards=8,
                tag="Missed Green", location=_point(33.7022, -78.9002),
            ),
            Shot(
                round_id=round_.id, hole_id=hole.id, shot_number=3, club="SW",
                start_lie=Lie.rough, end_lie=Lie.green,
                start_distance_yards=8, end_distance_yards=3,
                location=_point(green_lat, green_lng),
            ),
            Shot(
                round_id=round_.id, hole_id=hole.id, shot_number=4, club="Putter",
                start_lie=Lie.green, end_lie=Lie.hole,
                start_distance_yards=3, end_distance_yards=0,
            ),
        ]
    )
    session.commit()

    return round_.id, hole.number


def test_list_round_holes_reports_par_yardage_and_shot_count(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    round_id, hole_number = _seed_round_with_hole_geometry(db_session, user)

    response = auth_client.get(f"/api/rounds/{round_id}/holes")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0] == {"hole_number": hole_number, "par": 4, "yardage": 400, "shot_count": 4}


def test_list_round_holes_empty_for_course_less_round(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    round_ = Round(user_id=user.id, status=RoundStatus.needs_audit)
    db_session.add(round_)
    db_session.commit()
    db_session.refresh(round_)
    round_id = round_.id

    response = auth_client.get(f"/api/rounds/{round_id}/holes")
    assert response.status_code == 200
    assert response.json() == []


def test_list_round_holes_404_for_unknown_round(auth_client: TestClient) -> None:
    response = auth_client.get("/api/rounds/999999/holes")
    assert response.status_code == 404


def test_hole_replay_includes_geometry_and_shots(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    round_id, hole_number = _seed_round_with_hole_geometry(db_session, user)

    response = auth_client.get(f"/api/rounds/{round_id}/holes/{hole_number}/replay")

    assert response.status_code == 200
    body = response.json()
    assert body["hole_number"] == hole_number
    assert body["par"] == 4
    assert body["tee"] == {"lat": 33.7000, "lng": -78.9000}
    assert body["green_center"] == {"lat": 33.7025, "lng": -78.9000}
    assert len(body["green_boundary"]) == 5  # closed ring: 4 corners + repeat of first
    assert len(body["shots"]) == 4
    assert body["shots"][0]["club"] == "Driver"
    assert body["shots"][0]["location"] == {"lat": 33.7013, "lng": -78.9001}
    # the putt has no recorded location
    assert body["shots"][3]["location"] is None


def test_hole_replay_reports_short_sided_count(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    round_id, hole_number = _seed_round_with_hole_geometry(db_session, user)

    response = auth_client.get(f"/api/rounds/{round_id}/holes/{hole_number}/replay")

    body = response.json()
    # the 7-Iron shot missed the green into rough at 20y — inside the
    # short-sided proximity threshold (see app/services/approach.py)
    missed_green_shot = next(s for s in body["shots"] if s["tag"] == "Missed Green")
    assert missed_green_shot["approach_leave"] == "short_sided"
    assert body["short_sided_count"] == 1


def test_hole_replay_404_for_unknown_hole_number(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    round_id, _ = _seed_round_with_hole_geometry(db_session, user)
    response = auth_client.get(f"/api/rounds/{round_id}/holes/99/replay")
    assert response.status_code == 404


def test_hole_replay_409_for_course_less_round(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    round_ = Round(user_id=user.id, status=RoundStatus.needs_audit)
    db_session.add(round_)
    db_session.commit()
    db_session.refresh(round_)
    round_id = round_.id

    response = auth_client.get(f"/api/rounds/{round_id}/holes/1/replay")
    assert response.status_code == 409


def test_hole_replay_404_for_unknown_round(auth_client: TestClient) -> None:
    response = auth_client.get("/api/rounds/999999/holes/1/replay")
    assert response.status_code == 404
