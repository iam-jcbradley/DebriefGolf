from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, User


def _seed_club_shots(session: Session, user: User, driver_carries: list[float]) -> None:
    course = Course(name="Bag Test Course")
    session.add(course)
    session.commit()
    session.refresh(course)

    hole = Hole(course_id=course.id, number=1, par=4, yardage=400)
    session.add(hole)
    session.commit()
    session.refresh(hole)

    round_ = Round(
        user_id=user.id, course_id=course.id, total_score=4, status=RoundStatus.verified
    )
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


def test_bag_endpoint_reports_carry_stats_per_club(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    _seed_club_shots(db_session, user, [248.0, 250.0, 252.0, 251.0, 249.0])

    response = auth_client.get("/api/bag")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user.id
    assert len(body["clubs"]) == 1
    driver = body["clubs"][0]
    assert driver["club"] == "Driver"
    assert driver["sample_count"] == 5
    assert driver["carry_mean_yards"] == 250.0


def test_bag_endpoint_excludes_outlier_from_stats(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    _seed_club_shots(db_session, user, [248.0, 250.0, 252.0, 251.0, 249.0, 400.0])

    response = auth_client.get("/api/bag")

    driver = response.json()["clubs"][0]
    assert driver["sample_count"] == 5
    assert driver["excluded_outliers"] == 1
    assert driver["carry_mean_yards"] == 250.0


def test_bag_endpoint_empty_for_a_user_with_no_shots(
    auth_client: TestClient, user: User
) -> None:
    response = auth_client.get("/api/bag")

    assert response.status_code == 200
    assert response.json() == {"user_id": user.id, "clubs": [], "gaps": []}


def test_bag_endpoint_ignores_another_users_shots(
    auth_client: TestClient, db_session: Session, other_user: User
) -> None:
    _seed_club_shots(db_session, other_user, [248.0, 250.0, 252.0, 251.0, 249.0])

    response = auth_client.get("/api/bag")

    assert response.json()["clubs"] == []
