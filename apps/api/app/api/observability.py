"""Request-id correlation and the catch-all exception handler (Phase 12).

Two independent uses of the same id, on purpose:
- `request_id_var` (a contextvar) is what every ordinary log line picks up
  automatically for the duration of a request, via `RequestIdFilter`.
- `request.state.request_id` is what `unhandled_exception_handler` reads.
  It can't rely on the contextvar: `RequestIdMiddleware` resets it in a
  `finally` as soon as the exception finishes propagating out of
  `call_next`, which happens *before* Starlette's `ServerErrorMiddleware`
  invokes this handler — so by then the contextvar is already back to
  `None`. `request.state` isn't touched by that reset, so it's the one
  that's still there.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import request_id_var

logger = logging.getLogger("app.request")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """One id per request, echoed back as `X-Request-Id`. Always
    server-generated — trusting an incoming `X-Request-Id` header would let
    an unauthenticated caller plant an arbitrary value in this app's own
    logs."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %d in %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Request-Id"] = request_id
        return response


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Everything that reaches here is a bug, not an expected error —
    `HTTPException`s (404s, 401s, 422s) are handled by Starlette's own
    `ExceptionMiddleware` before they ever get this far. Logs the full
    traceback server-side and returns a body with no traceback in it.

    Sets its own `X-Request-Id` header rather than leaving it to
    `RequestIdMiddleware`: Starlette's `ServerErrorMiddleware` sends this
    response straight over the raw ASGI `send` channel once it's built, so
    it never flows back down through `RequestIdMiddleware.dispatch` the way
    an ordinary response does — that middleware's own header-setting line
    simply never runs on this path.
    """
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
        headers={"X-Request-Id": request_id} if request_id else None,
    )
