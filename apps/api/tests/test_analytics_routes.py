import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.session import engine
from app.main import app
from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, User

client = TestClient(app)


def _seed_round_with_shots() -> tuple[int, int]:
    """One par-4 hole, played tee -> fairway -> green -> holed (a clean par),
    for a 10-handicap user. Returns (round_id, hole_id)."""
    with Session(engine) as session:
        user = User(
            email=f"test-analytics-{uuid.uuid4()}@example.com", name="Test User",
            handicap_index=10.0,
        )
        course = Course(name="Analytics Test Course")
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

        shots = [
            Shot(round_id=round_.id, hole_id=hole.id, shot_number=1, club="Driver",
                 start_lie=Lie.tee, end_lie=Lie.fairway,
                 start_distance_yards=400, end_distance_yards=150),
            Shot(round_id=round_.id, hole_id=hole.id, shot_number=2, club="7-Iron",
                 start_lie=Lie.fairway, end_lie=Lie.green,
                 start_distance_yards=150, end_distance_yards=6.0),
            Shot(round_id=round_.id, hole_id=hole.id, shot_number=3, club="Putter",
                 start_lie=Lie.green, end_lie=Lie.hole,
                 start_distance_yards=6.0, end_distance_yards=0),
        ]
        session.add_all(shots)
        session.commit()

        return round_.id, hole.id


def test_analytics_endpoint_returns_expected_shape() -> None:
    round_id, _ = _seed_round_with_shots()

    response = client.get(f"/api/rounds/{round_id}/analytics")

    assert response.status_code == 200
    body = response.json()
    assert body["round_id"] == round_id
    assert body["handicap_bucket"] == 10
    assert "strokes_gained" in body
    assert set(body["strokes_gained"]["by_category"]) == {"OTT", "APP", "ARG", "PUTT"}
    assert body["tiger_five"]["clean_card_index"] == 100.0  # single par hole, no violations
    assert len(body["shots"]) == 3
    assert body["shots"][0]["category"] == "OTT"
    assert body["shots"][1]["category"] == "APP"
    assert body["shots"][2]["category"] == "PUTT"


def test_analytics_endpoint_persists_strokes_gained_on_shots() -> None:
    round_id, _ = _seed_round_with_shots()

    client.get(f"/api/rounds/{round_id}/analytics")

    with Session(engine) as session:
        shots = session.exec(
            select(Shot).where(Shot.round_id == round_id).order_by(Shot.id)
        ).all()
        assert all(s.strokes_gained is not None for s in shots)


def test_analytics_endpoint_404_for_unknown_round() -> None:
    response = client.get("/api/rounds/999999/analytics")
    assert response.status_code == 404
