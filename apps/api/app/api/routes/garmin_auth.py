from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.db.session import get_session
from app.models import GarminConnection, User
from app.services.garmin_oauth import (
    GarminOAuthError,
    build_authorize_request,
    decode_state,
    exchange_code_for_token,
)

router = APIRouter()


@router.get("/auth/garmin/authorize")
def start_garmin_authorize(
    user_id: int, session: Annotated[Session, Depends(get_session)]
) -> dict:
    """Returns the Garmin authorize URL for the frontend to redirect the
    browser to. Kept as a JSON response (not a server-side redirect) so a
    single-page app can drive the navigation itself."""
    if session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        request = build_authorize_request(user_id)
    except GarminOAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"authorize_url": request.url}


@router.get("/auth/garmin/callback")
async def garmin_callback(
    code: str, state: str, session: Annotated[Session, Depends(get_session)]
) -> RedirectResponse:
    """Garmin redirects the browser here after the user approves (or
    denies) access. Always ends in a redirect back to the frontend — there's
    no JSON response to show since this is a full-page browser navigation,
    not an API call the frontend makes directly.
    """
    try:
        payload = decode_state(state)
        token = await exchange_code_for_token(code, payload.code_verifier)
    except GarminOAuthError as exc:
        query = urlencode({"error": str(exc)})
        return RedirectResponse(f"{settings.frontend_url}/settings/garmin?{query}")

    existing = session.exec(
        select(GarminConnection).where(GarminConnection.user_id == payload.user_id)
    ).first()
    expires_at = datetime.now(UTC) + timedelta(seconds=token.expires_in)

    if existing:
        existing.access_token = token.access_token
        existing.refresh_token = token.refresh_token
        existing.token_type = token.token_type
        existing.scope = token.scope
        existing.expires_at = expires_at
        session.add(existing)
    else:
        session.add(
            GarminConnection(
                user_id=payload.user_id,
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                token_type=token.token_type,
                scope=token.scope,
                expires_at=expires_at,
            )
        )
    session.commit()

    return RedirectResponse(f"{settings.frontend_url}/settings/garmin?connected=1")


@router.get("/auth/garmin/{user_id}/status")
def garmin_status(user_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    connection = session.exec(
        select(GarminConnection).where(GarminConnection.user_id == user_id)
    ).first()
    return {"connected": connection is not None}


@router.delete("/auth/garmin/{user_id}")
def disconnect_garmin(user_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Removes the stored tokens (PRD data-privacy: "tokens... revoked on
    disconnect"). Doesn't call Garmin's own token-revocation endpoint — that
    needs the same real-credentials caveat as the rest of this module."""
    connection = session.exec(
        select(GarminConnection).where(GarminConnection.user_id == user_id)
    ).first()
    if connection:
        session.delete(connection)
        session.commit()
    return {"connected": False}
