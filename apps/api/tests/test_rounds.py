from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlmodel import Session, select

from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, User


def _seed_user_and_course(session: Session) -> tuple[int, int]:
    user = User(email="rounds@example.com", name="Test User")
    course = Course(name="Test Course")
    session.add(user)
    session.add(course)
    session.commit()
    session.refresh(user)
    session.refresh(course)
    return user.id, course.id


def _seed_one_round(session: Session) -> int:
    user_id, course_id = _seed_user_and_course(session)
    round_ = Round(
        user_id=user_id, course_id=course_id, total_score=90, status=RoundStatus.verified
    )
    session.add(round_)
    session.commit()
    session.refresh(round_)
    return round_.id


def _seed_round_with_two_holes(session: Session) -> tuple[int, int, int]:
    """Returns (round_id, course_id, user_id) for a round with holes 1 and 2."""
    user_id, course_id = _seed_user_and_course(session)
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


def test_list_rounds_includes_seeded_round(client: TestClient, db_session: Session) -> None:
    round_id = _seed_one_round(db_session)

    response = client.get("/api/rounds")

    assert response.status_code == 200
    # Exactly one: this test's transaction is the only thing in scope.
    assert [r["id"] for r in response.json()] == [round_id]


def test_list_rounds_filters_by_user_id(client: TestClient, db_session: Session) -> None:
    user_a, course_id = _seed_user_and_course(db_session)
    user_b = User(email="other-player@example.com", name="Other User")
    db_session.add(user_b)
    db_session.commit()
    db_session.refresh(user_b)

    round_a = Round(user_id=user_a, course_id=course_id, status=RoundStatus.verified)
    round_b = Round(user_id=user_b.id, course_id=course_id, status=RoundStatus.verified)
    db_session.add(round_a)
    db_session.add(round_b)
    db_session.commit()
    db_session.refresh(round_a)
    db_session.refresh(round_b)

    response = client.get(f"/api/rounds?user_id={user_a}")

    assert response.status_code == 200
    round_ids = {r["id"] for r in response.json()}
    assert round_a.id in round_ids
    assert round_b.id not in round_ids


def test_round_shots_404_for_unknown_round(client: TestClient) -> None:
    response = client.get("/api/rounds/999999/shots")
    assert response.status_code == 404


def test_round_shots_serializes_a_shot_with_a_gps_location(
    client: TestClient, db_session: Session
) -> None:
    # Regression test: an earlier version of this endpoint returned raw
    # `Shot` ORM objects, and geoalchemy2 hands back a `WKBElement` for
    # `location` — which isn't JSON-serializable — so any shot with GPS
    # data crashed the response with a 500.
    round_id, course_id, _ = _seed_round_with_two_holes(db_session)
    hole = db_session.exec(select(Hole).where(Hole.course_id == course_id)).first()
    db_session.add(
        Shot(
            round_id=round_id, hole_id=hole.id, shot_number=1, club="Driver",
            start_lie=Lie.tee, end_lie=Lie.fairway,
            start_distance_yards=400, end_distance_yards=150,
            location=WKTElement("POINT(-78.9 33.7)", srid=4326),
        )
    )
    db_session.commit()

    response = client.get(f"/api/rounds/{round_id}/shots")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["location"] == {"lat": 33.7, "lng": -78.9}


class TestCreateRound:
    def test_creates_a_round_against_an_existing_course(
        self, client: TestClient, db_session: Session
    ) -> None:
        user_id, course_id = _seed_user_and_course(db_session)

        response = client.post(
            "/api/rounds", json={"user_id": user_id, "course_id": course_id}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["user_id"] == user_id
        assert body["course_id"] == course_id
        assert body["status"] == "needs_audit"  # default

    def test_accepts_explicit_played_at_score_and_status(
        self, client: TestClient, db_session: Session
    ) -> None:
        user_id, course_id = _seed_user_and_course(db_session)

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

    def test_404_for_unknown_user(self, client: TestClient, db_session: Session) -> None:
        _, course_id = _seed_user_and_course(db_session)
        response = client.post(
            "/api/rounds", json={"user_id": 999999, "course_id": course_id}
        )
        assert response.status_code == 404

    def test_404_for_unknown_course(self, client: TestClient, db_session: Session) -> None:
        user_id, _ = _seed_user_and_course(db_session)
        response = client.post(
            "/api/rounds", json={"user_id": user_id, "course_id": 999999}
        )
        assert response.status_code == 404


class TestCreateShotsBulk:
    def test_creates_shots_resolving_hole_number_to_hole_id(
        self, client: TestClient, db_session: Session
    ) -> None:
        round_id, _, _ = _seed_round_with_two_holes(db_session)

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

    def test_404_for_unknown_round(self, client: TestClient) -> None:
        response = client.post("/api/rounds/999999/shots/bulk", json={"shots": []})
        assert response.status_code == 404

    def test_409_when_round_has_no_course(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = User(email="rounds-nocourse@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        round_ = Round(user_id=user.id, status=RoundStatus.needs_audit)
        db_session.add(round_)
        db_session.commit()
        db_session.refresh(round_)

        response = client.post(f"/api/rounds/{round_.id}/shots/bulk", json={"shots": []})
        assert response.status_code == 409

    def test_422_for_unknown_hole_number(
        self, client: TestClient, db_session: Session
    ) -> None:
        round_id, _, _ = _seed_round_with_two_holes(db_session)

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
