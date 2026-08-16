"""Access control (Phase 10).

Before this phase every endpoint took `user_id` from the request and trusted
it, so `GET /api/users/{id}/export` handed over any account's email, rounds
and GPS traces, and `DELETE /api/users/{id}` deleted any account — both
unauthenticated. These are the tests that say that can't happen again.

Two properties, tested differently:

1. *Every* endpoint requires a session. Rather than listing endpoints by
   hand — a list that goes stale the moment someone adds a route — this
   enumerates the live API surface from the OpenAPI schema and asserts each
   one 401s, with an explicit allowlist of the handful that are public by
   design. A new endpoint added without a session dependency fails this test
   until someone consciously adds it to `PUBLIC_ENDPOINTS`.
2. One user can't reach another's data, per resource.

These are also the tests Phase 9's transactional isolation exists to make
trustworthy: "user A cannot see user B's round" means nothing on a suite
where a stray row from a previous test could be supplying the answer.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models import Course, Hole, Round, RoundStatus, SimPlatform, User, VirtualRound

# Public by design:
#   health/ready — liveness/readiness probes that must answer before anyone
#                  can log in, and before there's a session to check
#   register/login — you can't hold a session before you have one
#   logout   — clearing a cookie shouldn't require the cookie to be valid
#   garmin callback — Garmin's redirect, authorized by the HMAC-signed
#                     `state` token instead (see app/api/routes/garmin_auth.py)
PUBLIC_ENDPOINTS = {
    ("GET", "/api/health"),
    ("GET", "/api/ready"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/auth/garmin/callback"),
}


def _api_endpoints() -> list[tuple[str, str]]:
    paths = app.openapi()["paths"]
    return sorted(
        (method.upper(), path)
        for path, operations in paths.items()
        if path.startswith("/api/")
        for method in operations
    )


def _concrete(path: str) -> str:
    """`/api/rounds/{round_id}/holes/{hole_number}/replay` -> `.../1/holes/1/replay`.

    The ids don't need to exist: an endpoint that checks the session first
    answers 401 without ever looking them up, which is exactly the ordering
    being asserted.
    """
    out = []
    for segment in path.split("/"):
        out.append("1" if segment.startswith("{") and segment.endswith("}") else segment)
    return "/".join(out)


ENDPOINTS = _api_endpoints()
PROTECTED = [e for e in ENDPOINTS if e not in PUBLIC_ENDPOINTS]


def test_the_endpoint_inventory_looks_sane() -> None:
    """Guards the guard: if the OpenAPI walk silently returned nothing, every
    parametrized test below would vacuously pass."""
    assert len(PROTECTED) > 15
    assert ("GET", "/api/me/export") in PROTECTED
    assert ("DELETE", "/api/me") in PROTECTED


@pytest.mark.parametrize(("method", "path"), PROTECTED, ids=[f"{m} {p}" for m, p in PROTECTED])
def test_endpoint_requires_a_session(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, _concrete(path), json={})

    assert response.status_code == 401, (
        f"{method} {path} answered {response.status_code} without a session. Every endpoint "
        "must depend on CurrentUser; if this one is genuinely public, add it to "
        "PUBLIC_ENDPOINTS with a reason."
    )


@pytest.mark.parametrize(("method", "path"), PROTECTED, ids=[f"{m} {p}" for m, p in PROTECTED])
def test_endpoint_rejects_a_forged_session_cookie(
    client: TestClient, method: str, path: str
) -> None:
    from app.core.config import settings

    client.cookies.set(settings.session_cookie_name, "eyJmYWtlIjoxfQ.bm90LWEtc2lnbmF0dXJl")

    response = client.request(method, _concrete(path), json={})

    assert response.status_code == 401


def _seed_round(session: Session, owner: User) -> int:
    course = Course(name="Someone Else's Course")
    session.add(course)
    session.commit()
    session.refresh(course)
    session.add(Hole(course_id=course.id, number=1, par=4, yardage=400))
    round_ = Round(user_id=owner.id, course_id=course.id, status=RoundStatus.verified)
    session.add(round_)
    session.commit()
    session.refresh(round_)
    return round_.id


class TestCrossUserAccess:
    """`other_user` owns the data; `auth_client` is logged in as `user`.

    Every assertion here is 404 rather than 403 on purpose: a 403 confirms
    the row exists, which lets someone map another account's data by
    walking integers even when they can't read it.
    """

    @pytest.mark.parametrize(
        "suffix",
        ["/analytics", "/shots", "/holes", "/holes/1/replay"],
    )
    def test_cannot_read_another_users_round(
        self,
        auth_client: TestClient,
        db_session: Session,
        other_user: User,
        suffix: str,
    ) -> None:
        round_id = _seed_round(db_session, other_user)

        response = auth_client.get(f"/api/rounds/{round_id}{suffix}")

        assert response.status_code == 404

    def test_cannot_add_shots_to_another_users_round(
        self, auth_client: TestClient, db_session: Session, other_user: User
    ) -> None:
        round_id = _seed_round(db_session, other_user)

        response = auth_client.post(
            f"/api/rounds/{round_id}/shots/bulk",
            json={
                "shots": [
                    {
                        "hole_number": 1,
                        "shot_number": 1,
                        "start_lie": "tee",
                        "end_lie": "fairway",
                        "start_distance_yards": 400,
                        "end_distance_yards": 150,
                    }
                ]
            },
        )

        assert response.status_code == 404

    def test_cannot_read_another_users_virtual_round(
        self, auth_client: TestClient, db_session: Session, other_user: User
    ) -> None:
        theirs = VirtualRound(
            user_id=other_user.id, platform=SimPlatform.gspro, course_name="Not Yours"
        )
        db_session.add(theirs)
        db_session.commit()
        db_session.refresh(theirs)

        assert auth_client.get(f"/api/virtual-rounds/{theirs.id}").status_code == 404

    def test_export_returns_only_the_callers_data(
        self, auth_client: TestClient, db_session: Session, user: User, other_user: User
    ) -> None:
        """The endpoint that used to hand over anyone's account by id. There
        is no longer a way to name whose export you want."""
        _seed_round(db_session, other_user)
        mine = _seed_round(db_session, user)

        body = auth_client.get("/api/me/export").json()

        assert body["user"]["id"] == user.id
        assert [r["id"] for r in body["rounds"]] == [mine]

    def test_delete_only_deletes_the_caller(
        self, auth_client: TestClient, db_session: Session, user: User, other_user: User
    ) -> None:
        """The endpoint that used to hard-delete any account by id."""
        theirs = _seed_round(db_session, other_user)

        response = auth_client.delete("/api/me")

        assert response.status_code == 200
        assert response.json()["user_id"] == user.id
        assert db_session.get(User, user.id) is None
        # Untouched.
        assert db_session.get(User, other_user.id) is not None
        assert db_session.get(Round, theirs) is not None

    def test_bag_and_practice_never_mix_users_data(
        self, auth_client: TestClient, db_session: Session, other_user: User
    ) -> None:
        _seed_round(db_session, other_user)

        assert auth_client.get("/api/bag").json()["clubs"] == []
        assert auth_client.get("/api/practice/delivery").json()["session_count"] == 0
        assert auth_client.get("/api/practice/combines").json()["weaknesses"] == []
