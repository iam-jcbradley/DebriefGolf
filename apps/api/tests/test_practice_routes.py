from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

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

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _seed_practice_session(session: Session, user_id: int, shots: list[dict]) -> int:
    practice_session = PracticeSession(user_id=user_id, source="R10")
    session.add(practice_session)
    session.commit()
    session.refresh(practice_session)
    for shot in shots:
        session.add(PracticeShot(session_id=practice_session.id, **shot))
    session.commit()
    return practice_session.id


def _seed_round_with_one_hole(session: Session, user_id: int, course_name: str) -> tuple[int, int]:
    """Returns (round_id, hole_id) for a one-hole course this user played."""
    course = Course(name=course_name)
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
    return round_.id, hole.id


class TestUploadPracticeSession:
    def test_upload_valid_csv_creates_session_and_shots(
        self, auth_client: TestClient, db_session: Session
    ) -> None:
        with (FIXTURES_DIR / "launch_monitor.csv").open("rb") as f:
            response = auth_client.post(
                "/api/practice/sessions/upload?source=R10",
                files={"file": ("session.csv", f, "text/csv")},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["shot_count"] == 3
        assert body["errors"] == []

        persisted = list(
            db_session.exec(
                select(PracticeShot).where(PracticeShot.session_id == body["session_id"])
            ).all()
        )
        assert len(persisted) == 3
        assert {s.club for s in persisted} == {"Driver", "7-Iron", "PW"}

    def test_upload_422s_when_nothing_parses(self, auth_client: TestClient) -> None:
        response = auth_client.post(
            "/api/practice/sessions/upload?source=R10",
            files={"file": ("session.csv", b"not,a,valid,header\n1,2,3,4\n", "text/csv")},
        )
        assert response.status_code == 422


class TestDeliveryProfileEndpoint:
    def test_returns_empty_for_user_with_no_sessions(self, auth_client: TestClient) -> None:
        response = auth_client.get("/api/practice/delivery")
        assert response.status_code == 200
        body = response.json()
        assert body["session_count"] == 0
        assert body["clubs"] == []
        assert body["sim_vs_real_gapping"] == []

    def test_aggregates_across_sessions_and_computes_gapping_delta(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        _seed_practice_session(
            db_session,
            user.id,
            [
                {"club": "Driver", "smash_factor": 1.48, "carry_yards": 260.0,
                 "spin_axis_deg": -2.0, "club_path_deg": -1.0, "face_angle_deg": 0.5},
                {"club": "Driver", "smash_factor": 1.46, "carry_yards": 250.0,
                 "spin_axis_deg": -1.0, "club_path_deg": -0.5, "face_angle_deg": 1.0},
            ],
        )

        # On-course Driver shots for the Sim vs. Real-World gapping delta.
        round_id, hole_id = _seed_round_with_one_hole(
            db_session, user.id, "Delivery Test Course"
        )
        db_session.add(
            Shot(round_id=round_id, hole_id=hole_id, shot_number=1, club="Driver",
                 start_lie=Lie.tee, end_lie=Lie.fairway,
                 start_distance_yards=400, end_distance_yards=400 - 240.0)
        )
        db_session.commit()

        response = auth_client.get("/api/practice/delivery")

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
    def test_no_weaknesses_for_user_with_no_data(self, auth_client: TestClient) -> None:
        response = auth_client.get("/api/practice/combines")
        assert response.status_code == 200
        body = response.json()
        assert body["weaknesses"] == []
        assert body["combines"] == []

    def test_flags_iron_strike_weakness_from_practice_shots(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        # 7-Iron's expected smash factor is ~1.33 (app/services/practice_combines.py);
        # 3+ shots meaningfully below that for one club is enough to flag.
        _seed_practice_session(
            db_session,
            user.id,
            [
                {"club": "7-Iron", "smash_factor": 1.15},
                {"club": "7-Iron", "smash_factor": 1.18},
                {"club": "7-Iron", "smash_factor": 1.17},
            ],
        )

        response = auth_client.get("/api/practice/combines")

        assert response.status_code == 200
        body = response.json()
        weaknesses = {w["weakness"] for w in body["weaknesses"]}
        assert "iron_strike_quality" in weaknesses
        combine_names = {c["name"] for c in body["combines"]}
        assert "Low-Point Compression" in combine_names

    def test_flags_approach_weakness_from_on_course_shots(
        self, auth_client: TestClient, db_session: Session, user: User
    ) -> None:
        round_id, hole_id = _seed_round_with_one_hole(
            db_session, user.id, "Combines Test Course"
        )
        for i in range(5):
            db_session.add(
                Shot(round_id=round_id, hole_id=hole_id, shot_number=i + 1, club="9-Iron",
                     start_lie=Lie.fairway, end_lie=Lie.sand,
                     start_distance_yards=110, end_distance_yards=15,
                     strokes_gained=-0.6)
            )
        db_session.commit()

        response = auth_client.get("/api/practice/combines")

        assert response.status_code == 200
        weaknesses = {w["weakness"] for w in response.json()["weaknesses"]}
        assert "approach_100_125" in weaknesses
