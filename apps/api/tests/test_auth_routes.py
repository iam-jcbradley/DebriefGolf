"""Registration, login, logout, session-cookie behaviour (Phase 10), and
password reset (Phase 15)."""

import re
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.core.security import (
    MIN_PASSWORD_LENGTH,
    RESET_TOKEN_TTL_SECONDS,
    create_reset_token,
)
from app.core.signing import encode
from app.models import User
from tests.conftest import TEST_PASSWORD

GOOD_PASSWORD = "a-perfectly-fine-password"
ANOTHER_GOOD_PASSWORD = "also-a-perfectly-fine-password"


def _reset_token_from_sent_email(mock_send_email) -> str:
    """`forgot_password` never puts the token in its HTTP response — only
    the emailed link carries it, same as a real inbox — so tests recover it
    by reading the mocked `send_email` call the way a person would read
    their email."""
    body = mock_send_email.call_args.kwargs["body"]
    match = re.search(r"/reset-password/(\S+)", body)
    assert match, f"No reset link found in email body: {body!r}"
    return match.group(1)


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


class TestForgotPassword:
    @patch("app.api.routes.auth.send_email")
    def test_emails_a_reset_link_for_a_real_account(
        self, mock_send_email, client: TestClient, user: User
    ) -> None:
        response = client.post("/api/auth/forgot-password", json={"email": user.email})

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        mock_send_email.assert_called_once()
        assert mock_send_email.call_args.kwargs["to"] == user.email
        assert "reset-password" in mock_send_email.call_args.kwargs["body"]

    @patch("app.api.routes.auth.send_email")
    def test_same_response_for_an_unknown_email(self, mock_send_email, client: TestClient) -> None:
        """Same shape as login's identical wrong-password/no-account
        response — an endpoint that behaved differently here would let
        someone test which emails have accounts."""
        real = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})

        assert real.status_code == 200
        assert real.json() == {"ok": True}
        mock_send_email.assert_not_called()

    @patch("app.api.routes.auth.send_email")
    def test_normalizes_the_email(self, mock_send_email, client: TestClient, user: User) -> None:
        response = client.post(
            "/api/auth/forgot-password", json={"email": f"  {user.email.upper()}  "}
        )

        assert response.status_code == 200
        mock_send_email.assert_called_once()

    @patch("app.api.routes.auth.send_email")
    def test_reaches_a_pre_phase_10_account_with_no_password(
        self, mock_send_email, client: TestClient, db_session: Session, make_user
    ) -> None:
        """The gap this whole phase exists to close: `password_hash IS
        NULL` accounts couldn't log in and had no way to get one set."""
        legacy = make_user(email="legacy@example.com")
        legacy.password_hash = None

        response = client.post("/api/auth/forgot-password", json={"email": legacy.email})

        assert response.status_code == 200
        mock_send_email.assert_called_once()


class TestResetPassword:
    @patch("app.api.routes.auth.send_email")
    def test_full_round_trip_against_a_real_database(
        self, mock_send_email, client: TestClient, db_session: Session, user: User
    ) -> None:
        """Request -> token -> new password -> login with it; the old
        password stops working. Phase 15's stated acceptance criterion."""
        client.post("/api/auth/forgot-password", json={"email": user.email})
        token = _reset_token_from_sent_email(mock_send_email)

        reset_response = client.post(
            "/api/auth/reset-password", json={"token": token, "password": GOOD_PASSWORD}
        )
        assert reset_response.status_code == 200
        assert reset_response.json()["id"] == user.id
        # Reset signs you in immediately.
        assert settings.session_cookie_name in reset_response.cookies

        old_password_login = client.post(
            "/api/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
        )
        assert old_password_login.status_code == 401

        new_password_login = client.post(
            "/api/auth/login", json={"email": user.email, "password": GOOD_PASSWORD}
        )
        assert new_password_login.status_code == 200
        assert new_password_login.json()["id"] == user.id

    @patch("app.api.routes.auth.send_email")
    def test_a_pre_phase_10_account_can_recover(
        self, mock_send_email, client: TestClient, db_session: Session, make_user
    ) -> None:
        """The specific scenario Phase 15 was scoped around: an account
        with no password at all gets one, end to end, through this route —
        not asserted against the token/security internals directly, but
        against the same HTTP path a real recovering user takes."""
        legacy = make_user(email="legacy@example.com")
        legacy.password_hash = None

        client.post("/api/auth/forgot-password", json={"email": legacy.email})
        token = _reset_token_from_sent_email(mock_send_email)

        reset_response = client.post(
            "/api/auth/reset-password", json={"token": token, "password": GOOD_PASSWORD}
        )
        assert reset_response.status_code == 200

        login_response = client.post(
            "/api/auth/login", json={"email": legacy.email, "password": GOOD_PASSWORD}
        )
        assert login_response.status_code == 200

    @patch("app.api.routes.auth.send_email")
    def test_a_token_cannot_be_redeemed_twice(
        self, mock_send_email, client: TestClient, user: User
    ) -> None:
        client.post("/api/auth/forgot-password", json={"email": user.email})
        token = _reset_token_from_sent_email(mock_send_email)

        first = client.post(
            "/api/auth/reset-password", json={"token": token, "password": GOOD_PASSWORD}
        )
        assert first.status_code == 200

        replay = client.post(
            "/api/auth/reset-password", json={"token": token, "password": ANOTHER_GOOD_PASSWORD}
        )
        assert replay.status_code == 422

    def test_rejects_an_expired_token(self, client: TestClient, user: User) -> None:
        # `create_reset_token` always mints a fresh TTL — build an
        # already-expired one directly with the same signing primitive
        # (`encode`) rather than sleeping past a real hour in a test.
        expired_token = encode(
            {"user_id": user.id, "pwv": "irrelevant"}, ttl_seconds=-RESET_TOKEN_TTL_SECONDS
        )

        response = client.post(
            "/api/auth/reset-password", json={"token": expired_token, "password": GOOD_PASSWORD}
        )
        assert response.status_code == 422

    def test_rejects_a_malformed_token(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/reset-password",
            json={"token": "not-a-real-token", "password": GOOD_PASSWORD},
        )
        assert response.status_code == 422

    def test_rejects_a_token_for_a_deleted_account(
        self, client: TestClient, db_session: Session, make_user
    ) -> None:
        ghost = make_user(email="ghost@example.com")
        token = create_reset_token(ghost.id, ghost.password_hash)
        db_session.delete(ghost)
        db_session.commit()

        response = client.post(
            "/api/auth/reset-password", json={"token": token, "password": GOOD_PASSWORD}
        )
        assert response.status_code == 422

    def test_rejects_a_weak_new_password(self, client: TestClient, user: User) -> None:
        token = create_reset_token(user.id, user.password_hash)

        response = client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "short"},
        )
        assert response.status_code == 422
        # A weak password must not consume the token — the account should
        # still be recoverable with a real one on a second try.
        retry = client.post(
            "/api/auth/reset-password", json={"token": token, "password": GOOD_PASSWORD}
        )
        assert retry.status_code == 200

    def test_never_returns_the_password_hash(self, client: TestClient, user: User) -> None:
        token = create_reset_token(user.id, user.password_hash)

        response = client.post(
            "/api/auth/reset-password", json={"token": token, "password": GOOD_PASSWORD}
        )

        assert "password" not in response.text
        assert set(response.json()) == {"id", "email", "name", "handicap_index", "created_at"}
