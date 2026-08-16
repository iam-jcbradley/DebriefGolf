import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.session import engine
from app.main import app
from app.models import User

client = TestClient(app)


def _seed_user(name: str) -> int:
    with Session(engine) as session:
        user = User(email=f"test-users-{uuid.uuid4()}@example.com", name=name)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


class TestCreateUser:
    def test_creates_a_user(self) -> None:
        email = f"test-create-{uuid.uuid4()}@example.com"
        response = client.post("/api/users", json={"name": "Jane Doe", "email": email})
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Jane Doe"
        assert body["email"] == email
        assert body["id"] is not None

    def test_rejects_blank_name(self) -> None:
        response = client.post(
            "/api/users", json={"name": "   ", "email": f"test-{uuid.uuid4()}@example.com"}
        )
        assert response.status_code == 422

    def test_rejects_invalid_email(self) -> None:
        response = client.post("/api/users", json={"name": "Jane Doe", "email": "not-an-email"})
        assert response.status_code == 422

    def test_409s_on_duplicate_email(self) -> None:
        email = f"test-dup-{uuid.uuid4()}@example.com"
        client.post("/api/users", json={"name": "First", "email": email})

        response = client.post("/api/users", json={"name": "Second", "email": email})

        assert response.status_code == 409


class TestSearchUsers:
    def test_finds_a_user_by_partial_name_case_insensitive(self) -> None:
        unique = str(uuid.uuid4())[:8]
        _seed_user(f"Zaphod {unique} Beeblebrox")

        response = client.get(f"/api/users?q={unique.upper()}")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == f"Zaphod {unique} Beeblebrox"
        assert set(body[0].keys()) == {"id", "name"}  # no email/handicap leaked

    def test_empty_list_below_minimum_query_length(self) -> None:
        response = client.get("/api/users?q=a")
        assert response.status_code == 200
        assert response.json() == []

    def test_empty_list_for_no_query(self) -> None:
        response = client.get("/api/users")
        assert response.status_code == 200
        assert response.json() == []

    def test_no_match_returns_empty_list(self) -> None:
        response = client.get("/api/users?q=zzzznonexistentplayerzzzz")
        assert response.status_code == 200
        assert response.json() == []


class TestGetUser:
    def test_returns_the_user(self) -> None:
        user_id = _seed_user("Get Test User")
        response = client.get(f"/api/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test User"

    def test_404s_for_unknown_user(self) -> None:
        response = client.get("/api/users/999999")
        assert response.status_code == 404
