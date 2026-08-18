from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import (
    Course,
    GarminConnection,
    Hole,
    Lie,
    PracticeSession,
    PracticeShot,
    Round,
    RoundStatus,
    Shot,
    SimPlatform,
    User,
    VirtualRound,
)


def _seed_full_user(session: Session, user: User) -> tuple[int, int]:
    """Gives `user` a round+shot, a practice session+shot, a virtual round,
    and a Garmin connection — one of everything this endpoint touches."""
    course = Course(name="Privacy Test Course")
    session.add(course)
    session.commit()
    session.refresh(course)

    hole = Hole(course_id=course.id, number=1, par=4, yardage=400)
    session.add(hole)
    session.commit()
    session.refresh(hole)

    round_ = Round(
        user_id=user.id, course_id=course.id, total_score=90, status=RoundStatus.verified
    )
    session.add(round_)
    session.commit()
    session.refresh(round_)

    shot = Shot(
        round_id=round_.id, hole_id=hole.id, shot_number=1, club="Driver",
        start_lie=Lie.tee, end_lie=Lie.fairway,
        start_distance_yards=400, end_distance_yards=150,
    )
    session.add(shot)

    practice_session = PracticeSession(user_id=user.id, source="R10")
    session.add(practice_session)
    session.commit()
    session.refresh(practice_session)
    session.add(PracticeShot(session_id=practice_session.id, club="7-Iron", smash_factor=1.3))

    session.add(
        VirtualRound(
            user_id=user.id, platform=SimPlatform.gspro, course_name="Sim Course",
            total_score=85,
        )
    )
    connection = GarminConnection(user_id=user.id, expires_at=datetime.now(UTC))
    connection.set_tokens("secret-access", "secret-refresh")
    session.add(connection)
    session.commit()

    return user.id, round_.id


class TestExportUserData:
    def test_exports_everything_the_user_owns(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        _, round_id = _seed_full_user(db_session, user)

        response = auth_client.get("/api/me/export")

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["id"] == user.id
        assert body["garmin_connected"] is True
        assert len(body["rounds"]) == 1
        assert body["rounds"][0]["id"] == round_id
        assert len(body["rounds"][0]["shots"]) == 1
        assert body["rounds"][0]["shots"][0]["club"] == "Driver"
        assert len(body["practice_sessions"]) == 1
        assert len(body["practice_sessions"][0]["shots"]) == 1
        assert len(body["virtual_rounds"]) == 1
        assert body["virtual_rounds"][0]["course_name"] == "Sim Course"

    def test_never_includes_raw_oauth_tokens(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        _seed_full_user(db_session, user)

        response = auth_client.get("/api/me/export")

        assert "secret-access" not in response.text
        assert "secret-refresh" not in response.text

    def test_empty_for_a_user_with_no_data(self, auth_client: TestClient) -> None:
        response = auth_client.get("/api/me/export")

        assert response.status_code == 200
        body = response.json()
        assert body["rounds"] == []
        assert body["practice_sessions"] == []
        assert body["virtual_rounds"] == []
        assert body["garmin_connected"] is False

    def test_groups_shots_correctly_across_multiple_rounds(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        # The export is now streamed one round's shots at a time (Phase 16)
        # rather than assembled from one query grouped in Python — this
        # guards against a round mix-up in that per-round query.
        course = Course(name="Multi Round Course")
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)

        hole = Hole(course_id=course.id, number=1, par=4, yardage=400)
        db_session.add(hole)
        db_session.commit()
        db_session.refresh(hole)

        round_a = Round(
            user_id=user.id, course_id=course.id, total_score=80, status=RoundStatus.verified
        )
        round_b = Round(
            user_id=user.id, course_id=course.id, total_score=95, status=RoundStatus.verified
        )
        db_session.add(round_a)
        db_session.add(round_b)
        db_session.commit()
        db_session.refresh(round_a)
        db_session.refresh(round_b)

        db_session.add(
            Shot(
                round_id=round_a.id, hole_id=hole.id, shot_number=1, club="Driver",
                start_lie=Lie.tee, end_lie=Lie.fairway,
                start_distance_yards=400, end_distance_yards=150,
            )
        )
        db_session.add(
            Shot(
                round_id=round_b.id, hole_id=hole.id, shot_number=1, club="7-Iron",
                start_lie=Lie.tee, end_lie=Lie.fairway,
                start_distance_yards=400, end_distance_yards=250,
            )
        )
        db_session.commit()

        response = auth_client.get("/api/me/export")

        body = response.json()
        assert len(body["rounds"]) == 2
        by_id = {r["id"]: r for r in body["rounds"]}
        assert [s["club"] for s in by_id[round_a.id]["shots"]] == ["Driver"]
        assert [s["club"] for s in by_id[round_b.id]["shots"]] == ["7-Iron"]

    def test_groups_shots_correctly_across_multiple_practice_sessions(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        session_a = PracticeSession(user_id=user.id, source="R10")
        session_b = PracticeSession(user_id=user.id, source="R50")
        db_session.add(session_a)
        db_session.add(session_b)
        db_session.commit()
        db_session.refresh(session_a)
        db_session.refresh(session_b)

        db_session.add(PracticeShot(session_id=session_a.id, club="Driver", smash_factor=1.4))
        db_session.add(PracticeShot(session_id=session_b.id, club="7-Iron", smash_factor=1.3))
        db_session.commit()

        response = auth_client.get("/api/me/export")

        body = response.json()
        assert len(body["practice_sessions"]) == 2
        by_id = {s["id"]: s for s in body["practice_sessions"]}
        assert [s["club"] for s in by_id[session_a.id]["shots"]] == ["Driver"]
        assert [s["club"] for s in by_id[session_b.id]["shots"]] == ["7-Iron"]


class TestDeleteUserData:
    def test_deletes_the_user_and_everything_they_own(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        user_id, round_id = _seed_full_user(db_session, user)

        response = auth_client.delete("/api/me")

        assert response.status_code == 200
        assert response.json() == {"deleted": True, "user_id": user_id}

        assert db_session.get(User, user_id) is None
        assert db_session.get(Round, round_id) is None
        assert list(db_session.exec(select(Shot).where(Shot.round_id == round_id)).all()) == []
        remaining_sessions = db_session.exec(
            select(PracticeSession).where(PracticeSession.user_id == user_id)
        ).all()
        assert list(remaining_sessions) == []
        remaining_virtual_rounds = db_session.exec(
            select(VirtualRound).where(VirtualRound.user_id == user_id)
        ).all()
        assert list(remaining_virtual_rounds) == []
        remaining_connection = db_session.exec(
            select(GarminConnection).where(GarminConnection.user_id == user_id)
        ).first()
        assert remaining_connection is None

    def test_does_not_touch_shared_course_and_hole_data(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        user_id, round_id = _seed_full_user(db_session, user)
        course_id = db_session.get(Round, round_id).course_id

        auth_client.delete("/api/me")

        assert db_session.get(Course, course_id) is not None
        assert list(db_session.exec(select(Hole).where(Hole.course_id == course_id)).all()) != []

    def test_get_after_delete_401s(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        _seed_full_user(db_session, user)
        auth_client.delete("/api/me")

        # The session cookie is cleared by the delete, and the token would
        # name a row that no longer exists anyway.
        response = auth_client.get("/api/me/export")

        assert response.status_code == 401
