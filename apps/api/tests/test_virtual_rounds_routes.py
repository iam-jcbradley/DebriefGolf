import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.session import engine
from app.main import app
from app.models import User

client = TestClient(app)


def _seed_user() -> int:
    with Session(engine) as session:
        user = User(email=f"test-virtual-{uuid.uuid4()}@example.com", name="Test User")
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


class TestCreateVirtualRound:
    def test_creates_a_virtual_round(self) -> None:
        user_id = _seed_user()
        response = client.post(
            "/api/virtual-rounds",
            json={
                "user_id": user_id,
                "platform": "gspro",
                "course_name": "Pebble Beach (Sim)",
                "holes_played": 18,
                "total_score": 82,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["user_id"] == user_id
        assert body["platform"] == "gspro"
        assert body["total_score"] == 82

    def test_404s_for_unknown_user(self) -> None:
        response = client.post(
            "/api/virtual-rounds",
            json={"user_id": 999999, "platform": "e6", "course_name": "Whistling Straits"},
        )
        assert response.status_code == 404

    def test_rejects_unknown_platform(self) -> None:
        user_id = _seed_user()
        response = client.post(
            "/api/virtual-rounds",
            json={"user_id": user_id, "platform": "not_a_real_sim", "course_name": "Anywhere"},
        )
        assert response.status_code == 422


class TestListAndGetVirtualRounds:
    def test_list_filters_by_user_id(self) -> None:
        user_a = _seed_user()
        user_b = _seed_user()
        client.post(
            "/api/virtual-rounds",
            json={"user_id": user_a, "platform": "home_tee_hero", "course_name": "Course A"},
        )
        client.post(
            "/api/virtual-rounds",
            json={"user_id": user_b, "platform": "home_tee_hero", "course_name": "Course B"},
        )

        response = client.get(f"/api/virtual-rounds?user_id={user_a}")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["user_id"] == user_a
        assert body[0]["course_name"] == "Course A"

    def test_get_by_id(self) -> None:
        user_id = _seed_user()
        created = client.post(
            "/api/virtual-rounds",
            json={"user_id": user_id, "platform": "e6", "course_name": "TPC Sawgrass"},
        ).json()

        response = client.get(f"/api/virtual-rounds/{created['id']}")

        assert response.status_code == 200
        assert response.json()["course_name"] == "TPC Sawgrass"

    def test_get_404s_for_unknown_id(self) -> None:
        response = client.get("/api/virtual-rounds/999999")
        assert response.status_code == 404
