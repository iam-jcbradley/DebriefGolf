import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.session import engine
from app.main import app
from app.models import Course, Round, RoundStatus, User

client = TestClient(app)


def _seed_one_round() -> int:
    with Session(engine) as session:
        user = User(email=f"test-rounds-{uuid.uuid4()}@example.com", name="Test User")
        course = Course(name="Test Course")
        session.add(user)
        session.add(course)
        session.commit()
        session.refresh(user)
        session.refresh(course)

        round_ = Round(user_id=user.id, course_id=course.id, total_score=90,
                        status=RoundStatus.verified)
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
