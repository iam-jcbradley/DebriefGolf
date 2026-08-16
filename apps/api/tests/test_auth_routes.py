"""Registration, login, logout and session-cookie behaviour (Phase 10)."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.core.security import MIN_PASSWORD_LENGTH
from app.models import User
from tests.conftest import TEST_PASSWORD

GOOD_PASSWORD = "a-perfectly-fine-password"


class TestRegister:
    def test_creates_an_account_and_logs_it_in(
        self, client: TestClient, db_session: Session
    ) -> None:
        response = client.post(
            "/api/auth/register",
            json={"name": "Jane Doe", "email": "jane@example.com", "password": GOOD_PASSWORD},
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Jane Doe"
        assert settings.session_cookie_name in response.cookies
        # Registration logs you straight in — no second round trip.
        assert client.get("/api/auth/me").json()["email"] == "jane@example.com"

    def test_never_returns_the_password_hash(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/register",
            json={"name": "Jane", "email": "hash@example.com", "password": GOOD_PASSWORD},
        )

        assert "password" not in response.text
        assert set(response.json()) == {"id", "email", "name", "handicap_index", "created_at"}

    def test_stores_a_hash_not_the_password(
        self, client: TestClient, db_session: Session
    ) -> None:
        created = client.post(
            "/api/auth/register",
            json={"name": "Jane", "email": "stored@example.com", "password": GOOD_PASSWORD},
        ).json()

        stored = db_session.get(User, created["id"]).password_hash
        assert stored is not None
        assert GOOD_PASSWORD not in stored
        assert stored.startswith("$argon2")

    def test_normalizes_the_email(self, client: TestClient) -> None:
        client.post(
            "/api/auth/register",
            json={"name": "Jane", "email": "  MixedCase@Example.COM ", "password": GOOD_PASSWORD},
        )
        assert client.get("/api/auth/me").json()["email"] == "mixedcase@example.com"

    def test_409s_on_duplicate_email(self, client: TestClient) -> None:
        payload = {"name": "First", "email": "dupe@example.com", "password": GOOD_PASSWORD}
        client.post("/api/auth/register", json=payload)

        response = client.post("/api/auth/register", json={**payload, "name": "Second"})

        assert response.status_code == 409

    def test_409s_on_duplicate_email_differing_only_in_case(self, client: TestClient) -> None:
        client.post(
            "/api/auth/register",
            json={"name": "First", "email": "case@example.com", "password": GOOD_PASSWORD},
        )

        response = client.post(
            "/api/auth/register",
            json={"name": "Second", "email": "CASE@example.com", "password": GOOD_PASSWORD},
        )

        assert response.status_code == 409

    def test_rejects_a_short_password(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/register",
            json={"name": "Jane", "email": "short@example.com", "password": "x" * (
                MIN_PASSWORD_LENGTH - 1
            )},
        )
        assert response.status_code == 422

    def test_rejects_a_blank_name(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/register",
            json={"name": "   ", "email": "blank@example.com", "password": GOOD_PASSWORD},
        )
        assert response.status_code == 422

    def test_rejects_an_invalid_email(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/register",
            json={"name": "Jane", "email": "not-an-email", "password": GOOD_PASSWORD},
        )
        assert response.status_code == 422


class TestLogin:
    def test_sets_a_session_cookie(self, client: TestClient, user: User) -> None:
        response = client.post(
            "/api/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
        )

        assert response.status_code == 200
        assert response.json()["id"] == user.id
        assert settings.session_cookie_name in response.cookies

    def test_session_cookie_is_http_only(self, client: TestClient, user: User) -> None:
        """Script mustn't be able to read the token, or an XSS bug becomes a
        session theft."""
        response = client.post(
            "/api/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
        )

        set_cookie = response.headers["set-cookie"].lower()
        assert "httponly" in set_cookie
        assert "samesite=lax" in set_cookie

    def test_401s_on_wrong_password(self, client: TestClient, user: User) -> None:
        response = client.post(
            "/api/auth/login", json={"email": user.email, "password": "not-the-password"}
        )
        assert response.status_code == 401

    def test_401s_for_an_unknown_email(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": TEST_PASSWORD}
        )
        assert response.status_code == 401

    def test_same_response_for_unknown_email_and_wrong_password(
        self, client: TestClient, user: User
    ) -> None:
        """Distinguishing the two turns login into an oracle for whether an
        email has an account here."""
        unknown = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": TEST_PASSWORD}
        )
        wrong = client.post("/api/auth/login", json={"email": user.email, "password": "nope"})

        assert unknown.status_code == wrong.status_code
        assert unknown.json() == wrong.json()

    def test_401s_for_an_account_with_no_password(
        self, client: TestClient, make_user
    ) -> None:
        """Accounts created before Phase 10 have `password_hash IS NULL` —
        that must read as "can't log in", never as "no password needed"."""
        legacy = make_user(email="legacy@example.com")
        legacy.password_hash = None

        response = client.post(
            "/api/auth/login", json={"email": legacy.email, "password": ""}
        )
        assert response.status_code == 401


class TestLogoutAndMe:
    def test_me_401s_without_a_session(self, client: TestClient) -> None:
        assert client.get("/api/auth/me").status_code == 401

    def test_me_401s_with_a_forged_cookie(self, client: TestClient, user: User) -> None:
        client.cookies.set(settings.session_cookie_name, "not.a.real.token")
        assert client.get("/api/auth/me").status_code == 401

    def test_me_returns_the_logged_in_user(self, auth_client: TestClient, user: User) -> None:
        response = auth_client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["id"] == user.id

    def test_logout_clears_the_session(self, auth_client: TestClient) -> None:
        assert auth_client.get("/api/auth/me").status_code == 200

        auth_client.post("/api/auth/logout")

        assert auth_client.get("/api/auth/me").status_code == 401

    def test_patch_me_updates_name_and_handicap(self, auth_client: TestClient) -> None:
        response = auth_client.patch(
            "/api/auth/me", json={"name": "New Name", "handicap_index": 8.4}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "New Name"
        assert response.json()["handicap_index"] == 8.4
        assert auth_client.get("/api/auth/me").json()["name"] == "New Name"
