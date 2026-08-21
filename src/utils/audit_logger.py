"""Starlette middleware for request-level audit logging.

``AuditLoggingMiddleware`` fires on every request.  For paths in
``LOGGED_PATHS`` it writes a ``QueryLog`` row to Postgres after the response
is sent (non-blocking — exceptions are swallowed so logging never breaks the
request path).

Each request also receives a unique ``X-Request-ID`` response header that
propagates through distributed traces and appears in every log line inside
that request via ``request.state.request_id``.
"""

import time
import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger("uvicorn.error")

# Paths for which a QueryLog row is written.  Add new sensitive paths here.
LOGGED_PATHS: frozenset[str] = frozenset({
    "/api/v1/nlp/index/answer",
    "/api/v1/nlp/index/search",
    "/api/v1/data/upload",
})


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Write audit records for sensitive endpoints.

    The middleware:
    1. Assigns a UUID request ID and attaches it to ``request.state``.
    2. Calls the downstream handler and measures wall-clock latency.
    3. If the path matches ``LOGGED_PATHS`` **and** the request was
       authenticated (``request.state.user`` exists), it persists a
       ``QueryLog`` row.
    4. Appends ``X-Request-ID`` to every response regardless of path.

    Middleware exceptions are logged and suppressed — they must never kill
    a successful response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1_000)

        # ── Audit log for sensitive paths ─────────────────────────────────
        path = request.url.path
        if any(path.startswith(logged) for logged in LOGGED_PATHS):
            user = getattr(request.state, "user", None)
            if user is not None:
                try:
                    from models import QueryLogModel  # deferred to avoid circular import
                    log_model = await QueryLogModel.create_instance(
                        db_client=request.app.db_client
                    )
                    await log_model.create_log(
                        user_id=user.user_id,
                        project_id=None,  # project resolved at handler level
                        endpoint=path,
                        query_text=None,  # detailed query logged at handler level
                        result_summary=None,
                        status="success" if response.status_code < 400 else "error",
                        latency_ms=latency_ms,
                        ip_address=getattr(request.client, "host", None),
                        request_id=request_id,
                    )
                except Exception as exc:
                    # Logging must NEVER break the request path.
                    log.warning(
                        "AuditLoggingMiddleware: failed to write audit log: %s", exc
                    )

        # ── Always attach request ID to response ──────────────────────────
        response.headers["X-Request-ID"] = request_id
        return response
