"""Request-scoped dependencies.

`CurrentUser` is the one that matters. Before Phase 10 every endpoint took
`user_id` as a query or path parameter and trusted it, which made
`GET /api/users/{id}/export` and `DELETE /api/users/{id}` reachable for any
account by anyone. Identity now comes from the signed session cookie and
nowhere else — a route that needs to know who is calling asks for
`CurrentUser`, and there is deliberately no way to name a different user in
a request.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.core.config import settings
from app.core.security import create_session_token, read_session_token
from app.db.session import get_session
from app.models import User

SessionDep = Annotated[Session, Depends(get_session)]

# Kept identical between setting and clearing: a browser only replaces a
# cookie when name/path/samesite/secure all match, so a logout whose
# attributes drift from login's silently leaves the session cookie in place.
_COOKIE_ATTRS = {"httponly": True, "samesite": "lax", "path": "/"}


def set_session_cookie(response: Response, user_id: int) -> None:
    """HttpOnly so script can't read the token (an XSS bug can't walk off
    with a session), SameSite=Lax to block cross-site request forgery while
    still allowing the web app's own credentialed fetches — localhost:3000 →
    localhost:8000 is same-site, since ports don't affect a cookie's notion
    of "site"."""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(user_id),
        max_age=settings.session_ttl_seconds,
        secure=settings.session_cookie_secure,
        **_COOKIE_ATTRS,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        secure=settings.session_cookie_secure,
        **_COOKIE_ATTRS,
    )


def _unauthenticated() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def get_current_user(request: Request, session: SessionDep) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise _unauthenticated()

    user_id = read_session_token(token)
    if user_id is None:
        raise _unauthenticated()

    user = session.get(User, user_id)
    if user is None:
        # A validly-signed session for an account that no longer exists —
        # the holder deleted it via `DELETE /api/me`. Sessions are stateless
        # (see app/core/security.py), so the token outlives the row and this
        # is the only place that mismatch can be caught.
        raise _unauthenticated()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
