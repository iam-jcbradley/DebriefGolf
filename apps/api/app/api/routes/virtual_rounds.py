"""Virtual/Sim Round Hub (PRD §6.2, §10 Phase 6): a dedicated log for
simulator rounds (Home Tee Hero, E6, GSPro), deliberately kept out of
`Round`/`RoundStatus` so nothing here ever feeds a real-world handicap
calculation — see `app.models.virtual_round.VirtualRound`.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.orm_typing import col, persisted
from app.models import SimPlatform, VirtualRound

router = APIRouter()


class VirtualRoundCreateIn(BaseModel):
    platform: SimPlatform
    course_name: str
    played_at: datetime | None = None
    holes_played: int = 18
    total_score: int | None = None
    notes: str | None = None


@router.post("/virtual-rounds", status_code=201)
def create_virtual_round(
    payload: VirtualRoundCreateIn, user: CurrentUser, session: SessionDep
) -> VirtualRound:
    virtual_round = VirtualRound(
        user_id=persisted(user.id),
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
def list_virtual_rounds(user: CurrentUser, session: SessionDep) -> list[VirtualRound]:
    return list(
        session.exec(
            select(VirtualRound)
            .where(VirtualRound.user_id == user.id)
            .order_by(col(VirtualRound.played_at).desc())
        ).all()
    )


@router.get("/virtual-rounds/{virtual_round_id}")
def get_virtual_round(
    virtual_round_id: int, user: CurrentUser, session: SessionDep
) -> VirtualRound:
    virtual_round = session.get(VirtualRound, virtual_round_id)
    # 404 rather than 403 for someone else's row: a 403 would confirm that a
    # virtual round with this id exists. The same rule applies everywhere a
    # route takes an id (see rounds.py's `_owned_round`).
    if virtual_round is None or virtual_round.user_id != user.id:
        raise HTTPException(status_code=404, detail="Virtual round not found")
    return virtual_round
