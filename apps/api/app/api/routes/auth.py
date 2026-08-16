"""Registration, login, logout, and "who am I" (Phase 10).

Replaces `app/api/routes/users.py`, which existed to back a name-based
player picker: it let anyone search other people's names and then act as
them. With real sessions there's nothing to pick — you are whoever you
logged in as — so the search and fetch-by-id endpoints are gone rather than
merely protected. Removing a user-enumeration surface beats guarding one.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    clear_session_cookie,
    set_session_cookie,
)
from app.api.routes.rounds import refresh_user_strokes_gained
from app.core.security import WeakPasswordError, hash_password, verify_password
from app.models import User

router = APIRouter()


class UserOut(BaseModel):
    """Deliberately explicit rather than returning the `User` row: that row
    carries `password_hash`, and an endpoint returning the model directly is
    one schema change away from leaking it."""

    id: int
    email: str
    name: str
    handicap_index: float
    created_at: datetime

    @classmethod
    def of(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            handicap_index=user.handicap_index,
            created_at=user.created_at,
        )


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


def _normalized(payload_email: str) -> str:
    return payload_email.strip().lower()


@router.post("/auth/register", status_code=201)
def register(payload: RegisterIn, session: SessionDep, response: Response) -> UserOut:
    name = payload.name.strip()
    email = _normalized(payload.email)
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if "@" not in email:
        raise HTTPException(status_code=422, detail="A valid email is required")

    try:
        password_hash = hash_password(payload.password)
    except WeakPasswordError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = session.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(name=name, email=email, password_hash=password_hash)
    session.add(user)
    session.commit()
    session.refresh(user)

    set_session_cookie(response, user.id)
    return UserOut.of(user)


@router.post("/auth/login")
def login(payload: LoginIn, session: SessionDep, response: Response) -> UserOut:
    user = session.exec(select(User).where(User.email == _normalized(payload.email))).first()

    # One message and one code for "no such account" and "wrong password":
    # distinguishing them turns this endpoint into a way to test whether an
    # email has an account here. `verify_password` handles `user is None`'s
    # partner case (a pre-Phase-10 account with no password set).
    if user is None or not verify_password(user.password_hash, payload.password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    set_session_cookie(response, user.id)
    return UserOut.of(user)


@router.post("/auth/logout")
def logout(response: Response) -> dict[str, bool]:
    """Clears the cookie. Sessions are stateless, so a token already copied
    out of the browser stays valid until it expires — see the trade-off note
    in app/core/security.py."""
    clear_session_cookie(response)
    return {"logged_out": True}


@router.get("/auth/me")
def read_current_user(user: CurrentUser) -> UserOut:
    return UserOut.of(user)


class ProfileUpdateIn(BaseModel):
    name: str | None = None
    handicap_index: float | None = None


@router.patch("/auth/me")
def update_current_user(
    payload: ProfileUpdateIn, user: CurrentUser, session: SessionDep
) -> UserOut:
    """Handicap index feeds the Strokes Gained benchmark bucket
    (`app/services/strokes_gained.py`), and until now there was no way to
    set it outside the seed script."""
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name is required")
        user.name = name
    handicap_changed = (
        payload.handicap_index is not None and payload.handicap_index != user.handicap_index
    )
    if payload.handicap_index is not None:
        user.handicap_index = payload.handicap_index

    session.add(user)
    session.commit()
    session.refresh(user)

    if handicap_changed:
        # Stored `Shot.strokes_gained` is benchmarked against the handicap
        # bucket, so it now describes a handicap this player no longer has.
        refresh_user_strokes_gained(session, user)

    return UserOut.of(user)
