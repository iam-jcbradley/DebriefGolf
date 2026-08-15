import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.session import engine
from app.main import app
from app.models import (
    Course,
    Hole,
    Lie,
    PracticeSession,
    PracticeShot,
    Round,
    RoundStatus,
    Shot,
    User,
)

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _seed_user() -> int:
    with Session(engine) as session:
        user = User(email=f"test-practice-{uuid.uuid4()}@example.com", name="Test User")
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def _seed_practice_session(user_id: int, shots: list[dict]) -> int:
    with Session(engine) as session:
        practice_session = PracticeSession(user_id=user_id, source="R10")
        session.add(practice_session)
        session.commit()
        session.refresh(practice_session)
        for shot in shots:
            session.add(PracticeShot(session_id=practice_session.id, **shot))
        session.commit()
        return practice_session.id


class TestUploadPracticeSession:
    def test_upload_valid_csv_creates_session_and_shots(self) -> None:
        user_id = _seed_user()
        with (FIXTURES_DIR / "launch_monitor.csv").open("rb") as f:
            response = client.post(
                f"/api/practice/sessions/upload?user_id={user_id}&source=R10",
                files={"file": ("session.csv", f, "text/csv")},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["shot_count"] == 3
        assert body["errors"] == []

        with Session(engine) as session:
            persisted = list(
                session.exec(
                    select(PracticeShot).where(PracticeShot.session_id == body["session_id"])
                ).all()
            )
        assert len(persisted) == 3
        assert {s.club for s in persisted} == {"Driver", "7-Iron", "PW"}

    def test_upload_404s_for_unknown_user(self) -> None:
        with (FIXTURES_DIR / "launch_monitor.csv").open("rb") as f:
            response = client.post(
                "/api/practice/sessions/upload?user_id=999999&source=R10",
                files={"file": ("session.csv", f, "text/csv")},
            )
        assert response.status_code == 404

    def test_upload_422s_when_nothing_parses(self) -> None:
        user_id = _seed_user()
        response = client.post(
            f"/api/practice/sessions/upload?user_id={user_id}&source=R10",
            files={"file": ("session.csv", b"not,a,valid,header\n1,2,3,4\n", "text/csv")},
        )
        assert response.status_code == 422


class TestDeliveryProfileEndpoint:
    def test_returns_empty_for_user_with_no_sessions(self) -> None:
        user_id = _seed_user()
        response = client.get(f"/api/practice/delivery/{user_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["session_count"] == 0
        assert body["clubs"] == []
        assert body["sim_vs_real_gapping"] == []

    def test_aggregates_across_sessions_and_computes_gapping_delta(self) -> None:
        user_id = _seed_user()
        _seed_practice_session(
            user_id,
            [
                {"club": "Driver", "smash_factor": 1.48, "carry_yards": 260.0,
                 "spin_axis_deg": -2.0, "club_path_deg": -1.0, "face_angle_deg": 0.5},
                {"club": "Driver", "smash_factor": 1.46, "carry_yards": 250.0,
                 "spin_axis_deg": -1.0, "club_path_deg": -0.5, "face_angle_deg": 1.0},
            ],
        )

        # On-course Driver shots for the Sim vs. Real-World gapping delta.
        with Session(engine) as session:
            course = Course(name="Delivery Test Course")
            session.add(course)
            session.commit()
            session.refresh(course)
            hole = Hole(course_id=course.id, number=1, par=4, yardage=400)
            session.add(hole)
            session.commit()
            session.refresh(hole)
            round_ = Round(user_id=user_id, course_id=course.id, status=RoundStatus.verified)
            session.add(round_)
            session.commit()
            session.refresh(round_)
            session.add(
                Shot(round_id=round_.id, hole_id=hole.id, shot_number=1, club="Driver",
                     start_lie=Lie.tee, end_lie=Lie.fairway,
                     start_distance_yards=400, end_distance_yards=400 - 240.0)
            )
            session.commit()

        response = client.get(f"/api/practice/delivery/{user_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["session_count"] == 1
        driver = next(c for c in body["clubs"] if c["club"] == "Driver")
        assert driver["shot_count"] == 2
        assert driver["avg_carry_yards"] == 255.0
        assert "Driver" in body["trend"]

        gapping = next(g for g in body["sim_vs_real_gapping"] if g["club"] == "Driver")
        assert gapping["range_carry_mean_yards"] == 255.0
        assert gapping["on_course_carry_mean_yards"] == 240.0
        assert gapping["delta_yards"] == 15.0


class TestPracticeCombinesEndpoint:
    def test_404s_for_unknown_user(self) -> None:
        response = client.get("/api/practice/combines/999999")
        assert response.status_code == 404

    def test_no_weaknesses_for_user_with_no_data(self) -> None:
        user_id = _seed_user()
        response = client.get(f"/api/practice/combines/{user_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["weaknesses"] == []
        assert body["combines"] == []

    def test_flags_iron_strike_weakness_from_practice_shots(self) -> None:
        user_id = _seed_user()
        _seed_practice_session(
            user_id,
            [
                {"club": "7-Iron", "smash_factor": 1.15},
                {"club": "7-Iron", "smash_factor": 1.18},
                {"club": "8-Iron", "smash_factor": 1.20},
            ],
        )

        response = client.get(f"/api/practice/combines/{user_id}")

        assert response.status_code == 200
        body = response.json()
        weaknesses = {w["weakness"] for w in body["weaknesses"]}
        assert "iron_strike_quality" in weaknesses
        combine_names = {c["name"] for c in body["combines"]}
        assert "Low-Point Compression" in combine_names

    def test_flags_approach_weakness_from_on_course_shots(self) -> None:
        user_id = _seed_user()
        with Session(engine) as session:
            course = Course(name="Combines Test Course")
            session.add(course)
            session.commit()
            session.refresh(course)
            hole = Hole(course_id=course.id, number=1, par=4, yardage=400)
            session.add(hole)
            session.commit()
            session.refresh(hole)
            round_ = Round(user_id=user_id, course_id=course.id, status=RoundStatus.verified)
            session.add(round_)
            session.commit()
            session.refresh(round_)
            for i in range(3):
                session.add(
                    Shot(round_id=round_.id, hole_id=hole.id, shot_number=i + 1, club="9-Iron",
                         start_lie=Lie.fairway, end_lie=Lie.sand,
                         start_distance_yards=110, end_distance_yards=15,
                         strokes_gained=-0.6)
                )
            session.commit()

        response = client.get(f"/api/practice/combines/{user_id}")

        assert response.status_code == 200
        weaknesses = {w["weakness"] for w in response.json()["weaknesses"]}
        assert "approach_100_125" in weaknesses
