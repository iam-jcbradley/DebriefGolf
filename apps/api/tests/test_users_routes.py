from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import User


def _seed_user(session: Session, name: str, email: str = "seeded@example.com") -> int:
    user = User(email=email, name=name)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user.id


class TestCreateUser:
    def test_creates_a_user(self, client: TestClient) -> None:
        response = client.post(
            "/api/users", json={"name": "Jane Doe", "email": "jane@example.com"}
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Jane Doe"
        assert body["email"] == "jane@example.com"
        assert body["id"] is not None

    def test_rejects_blank_name(self, client: TestClient) -> None:
        response = client.post(
            "/api/users", json={"name": "   ", "email": "blank-name@example.com"}
        )
        assert response.status_code == 422

    def test_rejects_invalid_email(self, client: TestClient) -> None:
        response = client.post("/api/users", json={"name": "Jane Doe", "email": "not-an-email"})
        assert response.status_code == 422

    def test_409s_on_duplicate_email(self, client: TestClient) -> None:
        client.post("/api/users", json={"name": "First", "email": "duplicate@example.com"})

        response = client.post(
            "/api/users", json={"name": "Second", "email": "duplicate@example.com"}
        )

        assert response.status_code == 409


class TestSearchUsers:
    def test_finds_a_user_by_partial_name_case_insensitive(
        self, client: TestClient, db_session: Session
    ) -> None:
        _seed_user(db_session, "Zaphod Beeblebrox")

        response = client.get("/api/users?q=BEEBLE")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "Zaphod Beeblebrox"
        assert set(body[0].keys()) == {"id", "name"}  # no email/handicap leaked

    def test_empty_list_below_minimum_query_length(self, client: TestClient) -> None:
        response = client.get("/api/users?q=a")
        assert response.status_code == 200
        assert response.json() == []

    def test_empty_list_for_no_query(self, client: TestClient) -> None:
        response = client.get("/api/users")
        assert response.status_code == 200
        assert response.json() == []

    def test_no_match_returns_empty_list(self, client: TestClient) -> None:
        response = client.get("/api/users?q=zzzznonexistentplayerzzzz")
        assert response.status_code == 200
        assert response.json() == []


class TestGetUser:
    def test_returns_the_user(self, client: TestClient, db_session: Session) -> None:
        user_id = _seed_user(db_session, "Get Test User")
        response = client.get(f"/api/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test User"

    def test_404s_for_unknown_user(self, client: TestClient) -> None:
        response = client.get("/api/users/999999")
        assert response.status_code == 404
