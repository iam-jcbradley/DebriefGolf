import uuid

from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlmodel import Session, select

from app.db.session import engine
from app.main import app
from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, User

client = TestClient(app)


def _seed_user_and_course() -> tuple[int, int]:
    with Session(engine) as session:
        user = User(email=f"test-rounds-{uuid.uuid4()}@example.com", name="Test User")
        course = Course(name="Test Course")
        session.add(user)
        session.add(course)
        session.commit()
        session.refresh(user)
        session.refresh(course)
        return user.id, course.id


def _seed_one_round() -> int:
    user_id, course_id = _seed_user_and_course()
    with Session(engine) as session:
        round_ = Round(
            user_id=user_id, course_id=course_id, total_score=90, status=RoundStatus.verified
        )
        session.add(round_)
        session.commit()
        session.refresh(round_)
        return round_.id


def test_list_rounds_includes_seeded_round() -> None:
    round_id = _seed_one_round()

    response = client.get("/api/rounds")

    assert response.status_code == 200
    assert any(r["id"] == round_id for r in response.json())


def test_round_shots_404_for_unknown_round() -> None:
    response = client.get("/api/rounds/999999/shots")
    assert response.status_code == 404


def test_round_shots_serializes_a_shot_with_a_gps_location() -> None:
    # Regression test: an earlier version of this endpoint returned raw
    # `Shot` ORM objects, and geoalchemy2 hands back a `WKBElement` for
    # `location` — which isn't JSON-serializable — so any shot with GPS
    # data crashed the response with a 500.
    round_id, course_id, _ = _seed_round_with_two_holes()
    with Session(engine) as session:
        hole = session.exec(select(Hole).where(Hole.course_id == course_id)).first()
        session.add(
            Shot(
                round_id=round_id, hole_id=hole.id, shot_number=1, club="Driver",
                start_lie=Lie.tee, end_lie=Lie.fairway,
                start_distance_yards=400, end_distance_yards=150,
                location=WKTElement("POINT(-78.9 33.7)", srid=4326),
            )
        )
        session.commit()

    response = client.get(f"/api/rounds/{round_id}/shots")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["location"] == {"lat": 33.7, "lng": -78.9}


class TestCreateRound:
    def test_creates_a_round_against_an_existing_course(self) -> None:
        user_id, course_id = _seed_user_and_course()

        response = client.post(
            "/api/rounds", json={"user_id": user_id, "course_id": course_id}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["user_id"] == user_id
        assert body["course_id"] == course_id
        assert body["status"] == "needs_audit"  # default

    def test_accepts_explicit_played_at_score_and_status(self) -> None:
        user_id, course_id = _seed_user_and_course()

        response = client.post(
            "/api/rounds",
            json={
                "user_id": user_id,
                "course_id": course_id,
                "played_at": "2026-01-15T10:00:00Z",
                "total_score": 82,
                "status": "verified",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["total_score"] == 82
        assert body["status"] == "verified"

    def test_404_for_unknown_user(self) -> None:
        _, course_id = _seed_user_and_course()
        response = client.post(
            "/api/rounds", json={"user_id": 999999, "course_id": course_id}
        )
        assert response.status_code == 404

    def test_404_for_unknown_course(self) -> None:
        user_id, _ = _seed_user_and_course()
        response = client.post(
            "/api/rounds", json={"user_id": user_id, "course_id": 999999}
        )
        assert response.status_code == 404


def _seed_round_with_two_holes() -> tuple[int, int, int]:
    """Returns (round_id, course_id, user_id) for a round with holes 1 and 2."""
    user_id, course_id = _seed_user_and_course()
    with Session(engine) as session:
        session.add_all(
            [
                Hole(course_id=course_id, number=1, par=4, yardage=400),
                Hole(course_id=course_id, number=2, par=3, yardage=175),
            ]
        )
        session.commit()

        round_ = Round(user_id=user_id, course_id=course_id, status=RoundStatus.needs_audit)
        session.add(round_)
        session.commit()
        session.refresh(round_)
        return round_.id, course_id, user_id


class TestCreateShotsBulk:
    def test_creates_shots_resolving_hole_number_to_hole_id(self) -> None:
        round_id, _, _ = _seed_round_with_two_holes()

        response = client.post(
            f"/api/rounds/{round_id}/shots/bulk",
            json={
                "shots": [
                    {
                        "hole_number": 1,
                        "shot_number": 1,
                        "club": "Driver",
                        "start_lie": "tee",
                        "end_lie": "fairway",
                        "start_distance_yards": 400,
                        "end_distance_yards": 150,
                        "location": {"lat": 33.701, "lng": -78.900},
                    },
                    {
                        "hole_number": 2,
                        "shot_number": 1,
                        "club": "7-Iron",
                        "start_lie": "tee",
                        "end_lie": "green",
                        "start_distance_yards": 175,
                        "end_distance_yards": 6,
                    },
                ]
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert len(body) == 2
        assert body[0]["club"] == "Driver"

        shots = client.get(f"/api/rounds/{round_id}/shots").json()
        assert len(shots) == 2

    def test_404_for_unknown_round(self) -> None:
        response = client.post("/api/rounds/999999/shots/bulk", json={"shots": []})
        assert response.status_code == 404

    def test_409_when_round_has_no_course(self) -> None:
        with Session(engine) as session:
            user = User(email=f"test-nocourse-{uuid.uuid4()}@example.com", name="Test User")
            session.add(user)
            session.commit()
            session.refresh(user)
            round_ = Round(user_id=user.id, status=RoundStatus.needs_audit)
            session.add(round_)
            session.commit()
            session.refresh(round_)
            round_id = round_.id

        response = client.post(f"/api/rounds/{round_id}/shots/bulk", json={"shots": []})
        assert response.status_code == 409

    def test_422_for_unknown_hole_number(self) -> None:
        round_id, _, _ = _seed_round_with_two_holes()

        response = client.post(
            f"/api/rounds/{round_id}/shots/bulk",
            json={
                "shots": [
                    {
                        "hole_number": 99,
                        "shot_number": 1,
                        "start_lie": "tee",
                        "end_lie": "fairway",
                        "start_distance_yards": 400,
                        "end_distance_yards": 150,
                    }
                ]
            },
        )

        assert response.status_code == 422
