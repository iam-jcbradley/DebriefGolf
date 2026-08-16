from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.db.session import get_session

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: this process is up. No dependency on anything else being
    healthy — a Postgres blip must never make a perfectly fine API process
    read as dead. See `/ready` for the endpoint that actually checks the
    database (Phase 12; this one used to do both, conflated)."""
    return {"status": "ok"}


@router.get("/ready")
def ready(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
    """Readiness: can this instance actually serve a request right now.
    A real orchestrator's health probe should point here, not at
    `/health` — that one can't tell "the app is fine" from "the app is
    fine but its database isn't"."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unreachable") from exc
    return {"status": "ok", "db": "connected"}
