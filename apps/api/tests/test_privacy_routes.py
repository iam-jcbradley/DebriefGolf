import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.session import engine
from app.main import app
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

client = TestClient(app)


def _seed_full_user() -> tuple[int, int]:
    """A user with a round+shot, a practice session+shot, a virtual round,
    and a Garmin connection — one of everything this endpoint touches."""
    with Session(engine) as session:
        user = User(email=f"test-privacy-{uuid.uuid4()}@example.com", name="Test User")
        course = Course(name="Privacy Test Course")
        session.add(user)
        session.add(course)
        session.commit()
        session.refresh(user)
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
        session.add(
            GarminConnection(
                user_id=user.id, access_token="secret-access", refresh_token="secret-refresh",
                expires_at=datetime.now(UTC),
            )
        )
        session.commit()

        return user.id, round_.id


class TestExportUserData:
    def test_404s_for_unknown_user(self) -> None:
        response = client.get("/api/users/999999/export")
        assert response.status_code == 404

    def test_exports_everything_the_user_owns(self) -> None:
        user_id, round_id = _seed_full_user()

        response = client.get(f"/api/users/{user_id}/export")

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["id"] == user_id
        assert body["garmin_connected"] is True
        assert len(body["rounds"]) == 1
        assert body["rounds"][0]["id"] == round_id
        assert len(body["rounds"][0]["shots"]) == 1
        assert body["rounds"][0]["shots"][0]["club"] == "Driver"
        assert len(body["practice_sessions"]) == 1
        assert len(body["practice_sessions"][0]["shots"]) == 1
        assert len(body["virtual_rounds"]) == 1
        assert body["virtual_rounds"][0]["course_name"] == "Sim Course"

    def test_never_includes_raw_oauth_tokens(self) -> None:
        user_id, _ = _seed_full_user()

        response = client.get(f"/api/users/{user_id}/export")

        assert "secret-access" not in response.text
        assert "secret-refresh" not in response.text

    def test_empty_for_a_user_with_no_data(self) -> None:
        with Session(engine) as session:
            user = User(email=f"test-privacy-empty-{uuid.uuid4()}@example.com", name="Empty User")
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        response = client.get(f"/api/users/{user_id}/export")

        assert response.status_code == 200
        body = response.json()
        assert body["rounds"] == []
        assert body["practice_sessions"] == []
        assert body["virtual_rounds"] == []
        assert body["garmin_connected"] is False


class TestDeleteUserData:
    def test_404s_for_unknown_user(self) -> None:
        response = client.delete("/api/users/999999")
        assert response.status_code == 404

    def test_deletes_the_user_and_everything_they_own(self) -> None:
        user_id, round_id = _seed_full_user()

        response = client.delete(f"/api/users/{user_id}")

        assert response.status_code == 200
        assert response.json() == {"deleted": True, "user_id": user_id}

        with Session(engine) as session:
            assert session.get(User, user_id) is None
            assert session.get(Round, round_id) is None
            assert list(session.exec(select(Shot).where(Shot.round_id == round_id)).all()) == []
            remaining_sessions = session.exec(
                select(PracticeSession).where(PracticeSession.user_id == user_id)
            ).all()
            assert list(remaining_sessions) == []
            remaining_virtual_rounds = session.exec(
                select(VirtualRound).where(VirtualRound.user_id == user_id)
            ).all()
            assert list(remaining_virtual_rounds) == []
            remaining_connection = session.exec(
                select(GarminConnection).where(GarminConnection.user_id == user_id)
            ).first()
            assert remaining_connection is None

    def test_does_not_touch_shared_course_and_hole_data(self) -> None:
        user_id, round_id = _seed_full_user()
        with Session(engine) as session:
            round_row = session.get(Round, round_id)
            course_id = round_row.course_id

        client.delete(f"/api/users/{user_id}")

        with Session(engine) as session:
            assert session.get(Course, course_id) is not None
            assert list(session.exec(select(Hole).where(Hole.course_id == course_id)).all()) != []

    def test_get_after_delete_404s(self) -> None:
        user_id, _ = _seed_full_user()
        client.delete(f"/api/users/{user_id}")

        response = client.get(f"/api/users/{user_id}/export")

        assert response.status_code == 404
