from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.models import Round, Shot

router = APIRouter()


@router.get("/rounds")
def list_rounds(session: Annotated[Session, Depends(get_session)]) -> list[Round]:
    return list(session.exec(select(Round)).all())


@router.get("/rounds/{round_id}/shots")
def list_round_shots(
    round_id: int, session: Annotated[Session, Depends(get_session)]
) -> list[Shot]:
    round_ = session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status_code=404, detail="Round not found")
    return list(
        session.exec(select(Shot).where(Shot.round_id == round_id).order_by(Shot.id)).all()
    )
