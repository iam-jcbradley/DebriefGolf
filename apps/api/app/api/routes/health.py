from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel import Session

from app.db.session import get_session

router = APIRouter()


@router.get("/health")
def health(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}
