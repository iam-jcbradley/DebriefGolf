"""Bounded reads for uploaded files.

Both upload endpoints used to do `contents = await file.read()` — the whole
request body into memory, with no size limit and nothing in front of the app
enforcing a cap. One large file was enough to take the API container with it.

Two layers, because one isn't enough:

1. `RequestSizeLimitMiddleware` (wired up in `app/main.py`) rejects a request
   whose `Content-Length` exceeds the limit *before* routing, so an
   oversized upload is refused before FastAPI parses the multipart body.
   This matters because by the time a handler runs, `UploadFile` has already
   been parsed and spooled — a check inside the handler is too late to avoid
   that work.
2. `read_upload` caps the streaming read inside the handler. This is the
   backstop for a request that declares no `Content-Length` at all (chunked
   transfer encoding), which the middleware can't judge.

Neither replaces a limit in whatever proxy sits in front of this in a real
deployment; they mean the app is not relying on one being there.
"""

import json

from fastapi import HTTPException, Request, UploadFile, status

# A .FIT file for a round of golf is tens to a few hundred kilobytes; an
# R10/R50 session export is a CSV of a few hundred rows. 10 MiB is far above
# anything legitimate and far below anything that threatens the process.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_CHUNK_BYTES = 64 * 1024


def too_large() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail=(
            f"File is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB limit. "
            "Golf .FIT files and launch-monitor exports are far smaller than this — "
            "check you're uploading the right file."
        ),
    )


async def read_upload(
    file: UploadFile, request: Request, max_bytes: int = MAX_UPLOAD_BYTES
) -> bytes:
    """The file's contents, or 413 if it exceeds `max_bytes`.

    Reads in chunks and stops at the limit rather than buffering the whole
    body first — refusing a 2 GiB upload by allocating 2 GiB would rather
    miss the point.
    """
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > max_bytes:
        raise too_large()

    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_CHUNK_BYTES):
        total += len(chunk)
        if total > max_bytes:
            raise too_large()
        chunks.append(chunk)

    return b"".join(chunks)


class RequestSizeLimitMiddleware:
    """Refuses an oversized request before it reaches routing or body parsing.

    Plain ASGI rather than a `BaseHTTPMiddleware` subclass: this has to run
    before the request body is consumed, and it answers without ever calling
    the app.
    """

    def __init__(self, app, max_bytes: int = MAX_UPLOAD_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers") or [])
            declared = headers.get(b"content-length")
            if declared and declared.isdigit() and int(declared) > self.max_bytes:
                exc = too_large()
                body = json.dumps({"detail": exc.detail}).encode()
                await send({
                    "type": "http.response.start",
                    "status": exc.status_code,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return

        await self.app(scope, receive, send)
