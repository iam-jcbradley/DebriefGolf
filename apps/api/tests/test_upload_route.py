from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Round, RoundStatus, User


def _seed_user(session: Session) -> int:
    user = User(email="upload@example.com", name="Test User")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user.id


class _FakeMessage:
    def __init__(self, values: dict):
        self._values = values

    def get_value(self, name: str):
        return self._values.get(name)


def _fake_fit_file(record_values: list[dict]) -> MagicMock:
    fake = MagicMock()

    def get_messages(name: str):
        if name == "session":
            start_time = datetime(2026, 8, 20, tzinfo=UTC)
            return [_FakeMessage({"sport": "golf", "start_time": start_time})]
        if name == "record":
            return [_FakeMessage(v) for v in record_values]
        raise AssertionError(f"unexpected message type: {name}")

    fake.get_messages.side_effect = get_messages
    return fake


def test_upload_valid_fit_creates_round_needing_audit(
    client: TestClient, db_session: Session
) -> None:
    user_id = _seed_user(db_session)
    fake_fit = _fake_fit_file(
        [
            {"position_lat": 401_000_000, "position_long": -871_000_000},
            {"position_lat": 401_000_500, "position_long": -871_000_400},
        ]
    )

    with patch("app.services.parsers.fit_parser.FitFile", return_value=fake_fit):
        response = client.post(
            f"/api/rounds/upload?user_id={user_id}",
            files={"file": ("round.fit", b"irrelevant-mocked-bytes", "application/octet-stream")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == RoundStatus.needs_audit.value
    assert body["sport"] == "golf"
    assert body["point_count"] == 2

    round_ = db_session.get(Round, body["round_id"])
    assert round_ is not None
    assert round_.user_id == user_id
    assert round_.course_id is None


def test_upload_corrupted_fit_still_creates_round_flagged_casual_practice(
    client: TestClient, db_session: Session
) -> None:
    user_id = _seed_user(db_session)

    response = client.post(
        f"/api/rounds/upload?user_id={user_id}",
        files={"file": ("garbage.fit", b"not-a-real-fit-file", "application/octet-stream")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == RoundStatus.casual_practice.value
    assert body["point_count"] == 0


def test_upload_unknown_user_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/rounds/upload?user_id=999999",
        files={"file": ("round.fit", b"whatever", "application/octet-stream")},
    )
    assert response.status_code == 404


def test_analytics_for_shot_less_round_reports_needs_shots(
    client: TestClient, db_session: Session
) -> None:
    user_id = _seed_user(db_session)
    response = client.post(
        f"/api/rounds/upload?user_id={user_id}",
        files={"file": ("garbage.fit", b"not-a-real-fit-file", "application/octet-stream")},
    )
    round_id = response.json()["round_id"]

    analytics = client.get(f"/api/rounds/{round_id}/analytics")

    assert analytics.status_code == 200
    assert analytics.json() == {
        "round_id": round_id,
        "status": RoundStatus.casual_practice.value,
        "needs_shots": True,
    }
