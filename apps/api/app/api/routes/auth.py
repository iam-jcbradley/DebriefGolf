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
from app.core.config import settings
from app.core.security import (
    WeakPasswordError,
    create_reset_token,
    hash_password,
    read_reset_token,
    reset_token_matches_current_password,
    verify_password,
)
from app.models import User
from app.services.email import send_email

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


class ForgotPasswordIn(BaseModel):
    email: str


class ForgotPasswordOut(BaseModel):
    ok: bool = True


@router.post("/auth/forgot-password")
def forgot_password(payload: ForgotPasswordIn, session: SessionDep) -> ForgotPasswordOut:
    """Always answers the same way whether or not the email has an account —
    same reasoning as `login`'s identical "no such account"/"wrong password"
    response above: distinguishing the two here would turn this endpoint
    into a way to test whether an email is registered."""
    user = session.exec(select(User).where(User.email == _normalized(payload.email))).first()
    if user is not None:
        token = create_reset_token(user.id, user.password_hash)
        reset_url = f"{settings.frontend_url}/reset-password/{token}"
        send_email(
            to=user.email,
            subject="Reset your Debrief Golf password",
            body=(
                "Someone asked to reset the password on this account.\n\n"
                f"Reset it: {reset_url}\n\n"
                "This link expires in an hour. If you didn't request this, ignore this email "
                "— your password hasn't changed."
            ),
        )
    return ForgotPasswordOut()


class ResetPasswordIn(BaseModel):
    token: str
    password: str


@router.post("/auth/reset-password")
def reset_password(payload: ResetPasswordIn, session: SessionDep, response: Response) -> UserOut:
    """Consumes a token from `forgot_password`. Also how a pre-Phase-10
    account (`password_hash IS NULL`, can't log in — see `verify_password`)
    gets a password set for the first time: `_password_fingerprint(None)`
    is a real, matchable value, so nothing here special-cases it."""
    invalid_token = HTTPException(
        status_code=422, detail="This reset link is invalid or has expired"
    )

    parsed = read_reset_token(payload.token)
    if parsed is None:
        raise invalid_token

    user = session.get(User, parsed.user_id)
    if user is None or not reset_token_matches_current_password(user.password_hash, parsed):
        # The mismatch case is what makes the token single-use: redeeming it
        # once changes `password_hash`, so a replay of the same token lands
        # here instead of succeeding twice.
        raise invalid_token

    try:
        user.password_hash = hash_password(payload.password)
    except WeakPasswordError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session.add(user)
    session.commit()
    session.refresh(user)

    # Resetting a password is itself proof of owning the account — sign
    # them straight in rather than making them log in again right after.
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
