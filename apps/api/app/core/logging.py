"""Structured (JSON) logging, correlated by a per-request id (Phase 12).

Before this, `grep -rn "import logging" apps/api/app` returned nothing — an
unhandled exception was a bare 500 with nothing on disk to explain it. This
wires stdlib `logging` (no new dependency; a JSON formatter is a dozen
lines, not worth pulling in structlog for a single-service app) to emit one
JSON object per line to stdout, tagged with whatever request id is live in
`request_id_var` for the request currently being handled — see
`app/api/observability.py` for where that gets set.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Fills in `record.request_id` from the ambient contextvar, unless the
    log call already passed one explicitly via `extra=` — the exception
    handler does that, since by the time it runs the request has already
    finished propagating out of the middleware that owns the contextvar."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


_HANDLER_MARKER = "_debriefgolf_json_handler"


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotent — safe to call more than once, since uvicorn's `--reload`
    re-imports `app.main` (and this module) on every code change, and
    duplicate handlers would otherwise mean duplicate log lines.

    Only ever removes a handler *this function* previously added, rather
    than clearing the root logger's handlers outright — the naive version
    of this silently broke pytest's own log capture, since pytest installs
    its root-level catching handler before collection imports `app.main`
    for the first time, and `handlers.clear()` doesn't distinguish "a
    duplicate of ours" from "something else entirely that happens to be on
    the root logger."
    """
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [h for h in root.handlers if not getattr(h, _HANDLER_MARKER, False)]

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    setattr(handler, _HANDLER_MARKER, True)
    root.addHandler(handler)
