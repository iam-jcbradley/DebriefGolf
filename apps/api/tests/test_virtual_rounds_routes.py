from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import SimPlatform, User, VirtualRound


class TestCreateVirtualRound:
    def test_creates_a_virtual_round(self, auth_client: TestClient, user: User) -> None:
        response = auth_client.post(
            "/api/virtual-rounds",
            json={
                "platform": "gspro",
                "course_name": "Pebble Beach (Sim)",
                "holes_played": 18,
                "total_score": 82,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["user_id"] == user.id
        assert body["platform"] == "gspro"
        assert body["total_score"] == 82

    def test_rejects_unknown_platform(self, auth_client: TestClient) -> None:
        response = auth_client.post(
            "/api/virtual-rounds",
            json={"platform": "not_a_real_sim", "course_name": "Anywhere"},
        )
        assert response.status_code == 422


class TestListAndGetVirtualRounds:
    def test_list_returns_only_the_callers_rounds(
        self, auth_client: TestClient, db_session: Session, user: User, other_user: User
    ) -> None:
        auth_client.post(
            "/api/virtual-rounds",
            json={"platform": "home_tee_hero", "course_name": "Course A"},
        )
        db_session.add(
            VirtualRound(
                user_id=other_user.id,
                platform=SimPlatform.home_tee_hero,
                course_name="Course B",
            )
        )
        db_session.commit()

        response = auth_client.get("/api/virtual-rounds")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["user_id"] == user.id
        assert body[0]["course_name"] == "Course A"

    def test_get_by_id(self, auth_client: TestClient) -> None:
        created = auth_client.post(
            "/api/virtual-rounds",
            json={"platform": "e6", "course_name": "TPC Sawgrass"},
        ).json()

        response = auth_client.get(f"/api/virtual-rounds/{created['id']}")

        assert response.status_code == 200
        assert response.json()["course_name"] == "TPC Sawgrass"

    def test_get_404s_for_unknown_id(self, auth_client: TestClient) -> None:
        response = auth_client.get("/api/virtual-rounds/999999")
        assert response.status_code == 404

    def test_get_404s_for_another_users_round(
        self, auth_client: TestClient, db_session: Session, other_user: User
    ) -> None:
        theirs = VirtualRound(
            user_id=other_user.id, platform=SimPlatform.e6, course_name="Not Yours"
        )
        db_session.add(theirs)
        db_session.commit()
        db_session.refresh(theirs)

        # 404, not 403: a 403 would confirm the row exists.
        response = auth_client.get(f"/api/virtual-rounds/{theirs.id}")
        assert response.status_code == 404
