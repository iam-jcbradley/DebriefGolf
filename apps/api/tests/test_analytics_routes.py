from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Course, Hole, Lie, Round, RoundStatus, Shot, User


def _seed_round_with_shots(session: Session, user: User) -> int:
    """One par-4 hole, played tee -> fairway -> green -> holed (a clean par),
    for a 10-handicap user. Returns the round id."""
    user.handicap_index = 10.0
    session.add(user)

    course = Course(name="Analytics Test Course")
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

    session.add_all(
        [
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
    )
    session.commit()

    return round_.id


def test_analytics_endpoint_returns_expected_shape(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    round_id = _seed_round_with_shots(db_session, user)

    response = auth_client.get(f"/api/rounds/{round_id}/analytics")

    assert response.status_code == 200
    body = response.json()
    assert body["round_id"] == round_id
    # The handicap bucket comes from the session user's own handicap index.
    assert body["handicap_bucket"] == 10
    assert "strokes_gained" in body
    assert set(body["strokes_gained"]["by_category"]) == {"OTT", "APP", "ARG", "PUTT"}
    assert body["tiger_five"]["clean_card_index"] == 100.0  # single par hole, no violations
    assert len(body["shots"]) == 3
    assert body["shots"][0]["category"] == "OTT"
    assert body["shots"][1]["category"] == "APP"
    assert body["shots"][2]["category"] == "PUTT"


def test_analytics_endpoint_does_not_write(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    """This endpoint used to recompute Strokes Gained and write it back to
    every shot in the round on every call — a non-idempotent GET on the
    dashboard's hot path. Stored SG is now written when shots are recorded
    (see `POST /rounds/{id}/shots/bulk`), and reads leave it alone."""
    round_id = _seed_round_with_shots(db_session, user)
    sentinel = -12.5
    for shot in db_session.exec(select(Shot).where(Shot.round_id == round_id)).all():
        shot.strokes_gained = sentinel
        db_session.add(shot)
    db_session.commit()

    response = auth_client.get(f"/api/rounds/{round_id}/analytics")
    assert response.status_code == 200
    # The response still reports freshly-computed SG...
    assert response.json()["shots"][0]["strokes_gained"] != sentinel

    db_session.expire_all()
    stored = db_session.exec(select(Shot).where(Shot.round_id == round_id)).all()
    # ...but nothing was written.
    assert [s.strokes_gained for s in stored] == [sentinel] * len(stored)


def test_analytics_endpoint_404_for_unknown_round(auth_client: TestClient) -> None:
    response = auth_client.get("/api/rounds/999999/analytics")
    assert response.status_code == 404


def test_analytics_endpoint_409_when_course_reassigned_after_shots_recorded(
    auth_client: TestClient, db_session: Session, user: User
) -> None:
    """A shot's `hole_id` still points at the round's *original* course once
    the round is reassigned to a different one — `Hole` rows are shared
    reference geometry, not deleted or rewritten on reassignment. Regression
    test for the KeyError this used to raise (a bare 500) instead of the
    409 a stale-but-still-valid foreign key actually calls for."""
    round_id = _seed_round_with_shots(db_session, user)

    other_course = Course(name="A Different Course")
    db_session.add(other_course)
    db_session.commit()
    db_session.refresh(other_course)
    db_session.add(Hole(course_id=other_course.id, number=1, par=4, yardage=380))
    db_session.commit()

    round_ = db_session.get(Round, round_id)
    round_.course_id = other_course.id
    db_session.add(round_)
    db_session.commit()

    response = auth_client.get(f"/api/rounds/{round_id}/analytics")

    assert response.status_code == 409
