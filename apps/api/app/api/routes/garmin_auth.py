from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.orm_typing import persisted
from app.models import GarminConnection
from app.services.garmin_oauth import (
    GarminOAuthError,
    build_authorize_request,
    decode_state,
    exchange_code_for_token,
)

router = APIRouter()


@router.get("/auth/garmin/authorize")
def start_garmin_authorize(user: CurrentUser) -> dict:
    """Returns the Garmin authorize URL for the frontend to redirect the
    browser to. Kept as a JSON response (not a server-side redirect) so a
    single-page app can drive the navigation itself."""
    try:
        request = build_authorize_request(persisted(user.id))
    except GarminOAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"authorize_url": request.url}


@router.get("/auth/garmin/callback")
async def garmin_callback(code: str, state: str, session: SessionDep) -> RedirectResponse:
    """Garmin redirects the browser here after the user approves (or
    denies) access. Always ends in a redirect back to the frontend — there's
    no JSON response to show since this is a full-page browser navigation,
    not an API call the frontend makes directly.

    Deliberately not behind `CurrentUser`: the caller here is Garmin's
    redirect, and the `state` token is what authorizes it. That token is
    HMAC-signed by this app with the user id inside it (see
    `app/services/garmin_oauth.py`), so it can't be pointed at another
    account without forging a signature — which is the same guarantee the
    session cookie itself rests on.
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
        existing.set_tokens(token.access_token, token.refresh_token)
        existing.token_type = token.token_type
        existing.scope = token.scope
        existing.expires_at = expires_at
        session.add(existing)
    else:
        connection = GarminConnection(
            user_id=payload.user_id,
            token_type=token.token_type,
            scope=token.scope,
            expires_at=expires_at,
        )
        connection.set_tokens(token.access_token, token.refresh_token)
        session.add(connection)
    session.commit()

    return RedirectResponse(f"{settings.frontend_url}/settings/garmin?connected=1")


@router.get("/auth/garmin/status")
def garmin_status(user: CurrentUser, session: SessionDep) -> dict:
    connection = session.exec(
        select(GarminConnection).where(GarminConnection.user_id == user.id)
    ).first()
    return {"connected": connection is not None}


@router.delete("/auth/garmin")
def disconnect_garmin(user: CurrentUser, session: SessionDep) -> dict:
    """Removes the stored tokens (PRD data-privacy: "tokens... revoked on
    disconnect"). Doesn't call Garmin's own token-revocation endpoint — that
    needs the same real-credentials caveat as the rest of this module."""
    connection = session.exec(
        select(GarminConnection).where(GarminConnection.user_id == user.id)
    ).first()
    if connection:
        session.delete(connection)
        session.commit()
    return {"connected": False}
