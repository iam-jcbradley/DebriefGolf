"""Virtual/Sim Round Hub (PRD §6.2, §10 Phase 6): a dedicated log for
simulator rounds (Home Tee Hero, E6, GSPro), deliberately kept out of
`Round`/`RoundStatus` so nothing here ever feeds a real-world handicap
calculation — see `app.models.virtual_round.VirtualRound`.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db.session import get_session
from app.models import SimPlatform, User, VirtualRound

router = APIRouter()


class VirtualRoundCreateIn(BaseModel):
    user_id: int
    platform: SimPlatform
    course_name: str
    played_at: datetime | None = None
    holes_played: int = 18
    total_score: int | None = None
    notes: str | None = None


@router.post("/virtual-rounds", status_code=201)
def create_virtual_round(
    payload: VirtualRoundCreateIn, session: Annotated[Session, Depends(get_session)]
) -> VirtualRound:
    if session.get(User, payload.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    virtual_round = VirtualRound(
        user_id=payload.user_id,
        platform=payload.platform,
        course_name=payload.course_name,
        played_at=payload.played_at or datetime.now(UTC),
        holes_played=payload.holes_played,
        total_score=payload.total_score,
        notes=payload.notes,
    )
    session.add(virtual_round)
    session.commit()
    session.refresh(virtual_round)
    return virtual_round


@router.get("/virtual-rounds")
def list_virtual_rounds(
    session: Annotated[Session, Depends(get_session)], user_id: int | None = None
) -> list[VirtualRound]:
    query = select(VirtualRound).order_by(VirtualRound.played_at.desc())
    if user_id is not None:
        query = query.where(VirtualRound.user_id == user_id)
    return list(session.exec(query).all())


@router.get("/virtual-rounds/{virtual_round_id}")
def get_virtual_round(
    virtual_round_id: int, session: Annotated[Session, Depends(get_session)]
) -> VirtualRound:
    virtual_round = session.get(VirtualRound, virtual_round_id)
    if virtual_round is None:
        raise HTTPException(status_code=404, detail="Virtual round not found")
    return virtual_round
