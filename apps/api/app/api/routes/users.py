"""User identity endpoints — there's no real auth in this app yet (PRD's
"no login yet" placeholder, threaded through every other route), so these
exist to back a name-based player picker the frontend persists locally
(`src/lib/current-user.tsx`) rather than making someone retype a numeric
user ID on every page.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.db.session import get_session
from app.models import User

router = APIRouter()

MIN_SEARCH_QUERY_LENGTH = 2
SEARCH_RESULT_LIMIT = 20


class UserCreateIn(BaseModel):
    name: str
    email: str


@router.post("/users", status_code=201)
def create_user(payload: UserCreateIn, session: Annotated[Session, Depends(get_session)]) -> User:
    name = payload.name.strip()
    email = payload.email.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if "@" not in email:
        raise HTTPException(status_code=422, detail="A valid email is required")

    existing = session.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A player with this email already exists")

    user = User(name=name, email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


class UserSummary(BaseModel):
    id: int
    name: str


@router.get("/users")
def search_users(
    session: Annotated[Session, Depends(get_session)], q: str = ""
) -> list[UserSummary]:
    """Name search backing the frontend's player picker. Requires at least
    `MIN_SEARCH_QUERY_LENGTH` characters — an empty/1-char query would
    otherwise dump every user in the database into a search-as-you-type
    box. Returns only `{id, name}`, not the full `User` (email, handicap),
    since search results may surface *other* people's accounts to whoever
    is picking a player on a shared device.
    """
    query = q.strip()
    if len(query) < MIN_SEARCH_QUERY_LENGTH:
        return []
    rows = session.exec(
        select(User.id, User.name)
        .where(func.lower(User.name).contains(query.lower()))
        .order_by(User.name)
        .limit(SEARCH_RESULT_LIMIT)
    ).all()
    return [UserSummary(id=r.id, name=r.name) for r in rows]


@router.get("/users/{user_id}")
def get_user(user_id: int, session: Annotated[Session, Depends(get_session)]) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
