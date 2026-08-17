from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlmodel import Session, select

from app.models import Course, Hole, Lie, Round, RoundHolePin, RoundStatus, Shot, User


def _seed_course(session: Session) -> int:
    course = Course(name="Test Course")
    session.add(course)
    session.commit()
    session.refresh(course)
    return course.id


def _seed_one_round(session: Session, user: User) -> int:
    round_ = Round(
        user_id=user.id,
        course_id=_seed_course(session),
        total_score=90,
        status=RoundStatus.verified,
    )
    session.add(round_)
    session.commit()
    session.refresh(round_)
    return round_.id


def _seed_round_with_two_holes(session: Session, user: User) -> tuple[int, int]:
    """Returns (round_id, course_id) for a round with holes 1 and 2."""
    course_id = _seed_course(session)
    session.add_all(
        [
            Hole(course_id=course_id, number=1, par=4, yardage=400),
            Hole(course_id=course_id, number=2, par=3, yardage=175),
        ]
    )
    session.commit()

    round_ = Round(user_id=user.id, course_id=course_id, status=RoundStatus.needs_audit)
    session.add(round_)
    session.commit()
    session.refresh(round_)
    return round_.id, course_id


def test_list_rounds_returns_only_the_callers_rounds(
    auth_client: TestClient, db_session: Session, user: User, other_user: User
) -> None:
    mine = _seed_one_round(db_session, user)
    theirs = _seed_one_round(db_session, other_user)

    response = auth_client.get("/api/rounds")

    assert response.status_code == 200
    assert [r["id"] for r in response.json()] == [mine]
    assert theirs not in [r["id"] for r in response.json()]


def test_round_shots_404_for_unknown_round(auth_client: TestClient) -> None:
    response = auth_client.get("/api/rounds/999999/shots")
    assert response.status_code == 404


def test_round_shots_serializes_a_shot_with_a_gps_location(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    # Regression test: an earlier version of this endpoint returned raw
    # `Shot` ORM objects, and geoalchemy2 hands back a `WKBElement` for
    # `location` — which isn't JSON-serializable — so any shot with GPS
    # data crashed the response with a 500.
    round_id, course_id = _seed_round_with_two_holes(db_session, user)
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

    response = auth_client.get(f"/api/rounds/{round_id}/shots")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["location"] == {"lat": 33.7, "lng": -78.9}


class TestCreateRound:
    def test_creates_a_round_owned_by_the_caller(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        course_id = _seed_course(db_session)

        response = auth_client.post("/api/rounds", json={"course_id": course_id})

        assert response.status_code == 201
        body = response.json()
        # The round's owner comes from the session, not from the request —
        # there is no `user_id` field to send any more.
        assert body["user_id"] == user.id
        assert body["course_id"] == course_id
        assert body["status"] == "needs_audit"  # default

    def test_accepts_explicit_played_at_score_and_status(
        self, auth_client: TestClient, db_session: Session
    ) -> None:
        course_id = _seed_course(db_session)

        response = auth_client.post(
            "/api/rounds",
            json={
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

    def test_404_for_unknown_course(self, auth_client: TestClient) -> None:
        response = auth_client.post("/api/rounds", json={"course_id": 999999})
        assert response.status_code == 404


class TestCreateShotsBulk:
    def test_creates_shots_resolving_hole_number_to_hole_id(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        round_id, _ = _seed_round_with_two_holes(db_session, user)

        response = auth_client.post(
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

        shots = auth_client.get(f"/api/rounds/{round_id}/shots").json()
        assert len(shots) == 2

    def test_resubmitting_the_same_shot_does_not_duplicate_it(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        """Regression test: this used to be purely additive, so a retried
        submit (e.g. a dropped connection after the write actually
        succeeded) silently duplicated a hole's shots."""
        round_id, _ = _seed_round_with_two_holes(db_session, user)
        shot_payload = {
            "shots": [
                {
                    "hole_number": 1,
                    "shot_number": 1,
                    "club": "Driver",
                    "start_lie": "tee",
                    "end_lie": "fairway",
                    "start_distance_yards": 400,
                    "end_distance_yards": 150,
                }
            ]
        }

        first = auth_client.post(f"/api/rounds/{round_id}/shots/bulk", json=shot_payload)
        second = auth_client.post(f"/api/rounds/{round_id}/shots/bulk", json=shot_payload)

        assert first.status_code == 201
        assert second.status_code == 201
        # Same shot id back both times — the second call didn't create a
        # new row, it found the one from the first call.
        assert first.json()[0]["id"] == second.json()[0]["id"]

        shots = auth_client.get(f"/api/rounds/{round_id}/shots").json()
        assert len(shots) == 1

    def test_duplicate_shot_within_one_payload_does_not_duplicate_it(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        """Same guard, but both copies arrive in a single request rather
        than two separate ones."""
        round_id, _ = _seed_round_with_two_holes(db_session, user)
        one_shot = {
            "hole_number": 1,
            "shot_number": 1,
            "club": "Driver",
            "start_lie": "tee",
            "end_lie": "fairway",
            "start_distance_yards": 400,
            "end_distance_yards": 150,
        }

        response = auth_client.post(
            f"/api/rounds/{round_id}/shots/bulk", json={"shots": [one_shot, one_shot]}
        )

        assert response.status_code == 201
        body = response.json()
        assert len(body) == 2
        assert body[0]["id"] == body[1]["id"]

        shots = auth_client.get(f"/api/rounds/{round_id}/shots").json()
        assert len(shots) == 1

    def test_a_second_hole_can_still_be_added_after_the_first(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        """Not everything through this endpoint is a retry — the manual
        entry flow calls it once per hole as the round is played, and those
        calls must keep accumulating shots normally."""
        round_id, _ = _seed_round_with_two_holes(db_session, user)
        auth_client.post(
            f"/api/rounds/{round_id}/shots/bulk",
            json={
                "shots": [
                    {
                        "hole_number": 1,
                        "shot_number": 1,
                        "start_lie": "tee",
                        "end_lie": "fairway",
                        "start_distance_yards": 400,
                        "end_distance_yards": 150,
                    }
                ]
            },
        )

        response = auth_client.post(
            f"/api/rounds/{round_id}/shots/bulk",
            json={
                "shots": [
                    {
                        "hole_number": 2,
                        "shot_number": 1,
                        "start_lie": "tee",
                        "end_lie": "green",
                        "start_distance_yards": 175,
                        "end_distance_yards": 6,
                    }
                ]
            },
        )

        assert response.status_code == 201
        shots = auth_client.get(f"/api/rounds/{round_id}/shots").json()
        assert len(shots) == 2

    def test_persists_strokes_gained_when_shots_are_recorded(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        """Stored SG is written here rather than on every analytics read.
        `GET /practice/combines`, the export and the hole replay all read the
        column, so it has to be populated at write time."""
        round_id, _ = _seed_round_with_two_holes(db_session, user)

        auth_client.post(
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
                    }
                ]
            },
        )

        db_session.expire_all()
        stored = db_session.exec(select(Shot).where(Shot.round_id == round_id)).all()
        assert stored
        assert all(s.strokes_gained is not None for s in stored)

    def test_404_for_unknown_round(self, auth_client: TestClient) -> None:
        response = auth_client.post("/api/rounds/999999/shots/bulk", json={"shots": []})
        assert response.status_code == 404

    def test_409_when_round_has_no_course(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        round_ = Round(user_id=user.id, status=RoundStatus.needs_audit)
        db_session.add(round_)
        db_session.commit()
        db_session.refresh(round_)

        response = auth_client.post(f"/api/rounds/{round_.id}/shots/bulk", json={"shots": []})
        assert response.status_code == 409

    def test_422_for_unknown_hole_number(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        round_id, _ = _seed_round_with_two_holes(db_session, user)

        response = auth_client.post(
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


class TestCreatePinsBulk:
    def test_creates_a_pin_resolving_hole_number_to_hole_id(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        round_id, _ = _seed_round_with_two_holes(db_session, user)

        response = auth_client.post(
            f"/api/rounds/{round_id}/pins/bulk",
            json={"pins": [{"hole_number": 1, "location": {"lat": 33.701, "lng": -78.900}}]},
        )

        assert response.status_code == 201
        body = response.json()
        assert len(body) == 1
        assert body[0]["hole_number"] == 1
        assert body[0]["location"] == {"lat": 33.701, "lng": -78.900}

        db_session.expire_all()
        pins = db_session.exec(select(RoundHolePin).where(RoundHolePin.round_id == round_id)).all()
        assert len(pins) == 1

    def test_resubmitting_a_hole_replaces_its_pin_rather_than_duplicating(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        round_id, _ = _seed_round_with_two_holes(db_session, user)

        first = auth_client.post(
            f"/api/rounds/{round_id}/pins/bulk",
            json={"pins": [{"hole_number": 1, "location": {"lat": 33.701, "lng": -78.900}}]},
        )
        second = auth_client.post(
            f"/api/rounds/{round_id}/pins/bulk",
            # A correction, not a duplicate — same hole, different point.
            json={"pins": [{"hole_number": 1, "location": {"lat": 33.702, "lng": -78.901}}]},
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()[0]["id"] == second.json()[0]["id"]

        db_session.expire_all()
        pins = db_session.exec(select(RoundHolePin).where(RoundHolePin.round_id == round_id)).all()
        assert len(pins) == 1
        assert second.json()[0]["location"] == {"lat": 33.702, "lng": -78.901}

    def test_404_for_unknown_round(self, auth_client: TestClient) -> None:
        response = auth_client.post("/api/rounds/999999/pins/bulk", json={"pins": []})
        assert response.status_code == 404

    def test_409_when_round_has_no_course(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        round_ = Round(user_id=user.id, status=RoundStatus.needs_audit)
        db_session.add(round_)
        db_session.commit()
        db_session.refresh(round_)

        response = auth_client.post(f"/api/rounds/{round_.id}/pins/bulk", json={"pins": []})
        assert response.status_code == 409

    def test_422_for_unknown_hole_number(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        round_id, _ = _seed_round_with_two_holes(db_session, user)

        response = auth_client.post(
            f"/api/rounds/{round_id}/pins/bulk",
            json={"pins": [{"hole_number": 99, "location": {"lat": 33.701, "lng": -78.900}}]},
        )

        assert response.status_code == 422
