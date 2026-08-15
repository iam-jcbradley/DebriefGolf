import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.session import engine
from app.main import app
from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, User

client = TestClient(app)


def _seed_user_with_club_shots(driver_carries: list[float]) -> int:
    with Session(engine) as session:
        user = User(email=f"test-bag-{uuid.uuid4()}@example.com", name="Test User")
        course = Course(name="Bag Test Course")
        session.add(user)
        session.add(course)
        session.commit()
        session.refresh(user)
        session.refresh(course)

        hole = Hole(course_id=course.id, number=1, par=4, yardage=400)
        session.add(hole)
        session.commit()
        session.refresh(hole)

        round_ = Round(user_id=user.id, course_id=course.id, total_score=4,
                        status=RoundStatus.verified)
        session.add(round_)
        session.commit()
        session.refresh(round_)

        for i, carry in enumerate(driver_carries, start=1):
            session.add(
                Shot(round_id=round_.id, hole_id=hole.id, shot_number=i, club="Driver",
                     start_lie=Lie.tee, end_lie=Lie.fairway,
                     start_distance_yards=400, end_distance_yards=400 - carry)
            )
        session.commit()

        return user.id


def test_bag_endpoint_reports_carry_stats_per_club() -> None:
    user_id = _seed_user_with_club_shots([248.0, 250.0, 252.0, 251.0, 249.0])

    response = client.get(f"/api/bag/{user_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert len(body["clubs"]) == 1
    driver = body["clubs"][0]
    assert driver["club"] == "Driver"
    assert driver["sample_count"] == 5
    assert driver["carry_mean_yards"] == 250.0


def test_bag_endpoint_excludes_outlier_from_stats() -> None:
    user_id = _seed_user_with_club_shots([248.0, 250.0, 252.0, 251.0, 249.0, 400.0])

    response = client.get(f"/api/bag/{user_id}")

    driver = response.json()["clubs"][0]
    assert driver["sample_count"] == 5
    assert driver["excluded_outliers"] == 1
    assert driver["carry_mean_yards"] == 250.0


def test_bag_endpoint_empty_for_unknown_user() -> None:
    response = client.get("/api/bag/999999")

    assert response.status_code == 200
    assert response.json() == {"user_id": 999999, "clubs": [], "gaps": []}
