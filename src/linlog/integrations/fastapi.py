"""
FastAPI / Starlette integration for linlog.

Implemented as a pure ASGI middleware (not Starlette's BaseHTTPMiddleware)
because BaseHTTPMiddleware runs `dispatch` in a separate task, which breaks
ContextVar propagation — the exact mechanism linlog relies on.

Usage:

    from fastapi import FastAPI
    from linlog.integrations.fastapi import RequestIDMiddleware

    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    # Or with options:
    app.add_middleware(
        RequestIDMiddleware,
        header_name="X-Request-ID",
        response_header_name="X-Request-ID",  # None to disable
    )
"""

from typing import Callable, Optional

from ..context import clear_request_id, set_request_id
from ..utils import generate_request_id
from ._core import DEFAULT_HEADER_NAME, resolve_request_id


class RequestIDMiddleware:
    """
    Pure ASGI middleware that manages the linlog request-ID ContextVar.

    Because we implement ASGI directly (not BaseHTTPMiddleware), the
    ContextVar set here is visible to all downstream endpoint code and
    background tasks launched via ``asyncio.create_task`` within the request.
    """

    def __init__(
        self,
        app,
        header_name: str = DEFAULT_HEADER_NAME,
        response_header_name: Optional[str] = DEFAULT_HEADER_NAME,
        generator: Callable[[], str] = generate_request_id,
    ):
        self.app = app
        # Incoming ASGI headers are lowercase bytes per the spec.
        self._incoming_header = header_name.lower().encode("latin-1")
        self._response_header = response_header_name
        self._generator = generator

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        incoming = self._extract_header(scope)
        rid = resolve_request_id(incoming, self._generator)
        set_request_id(rid)

        send_wrapper = send
        if self._response_header and scope["type"] == "http":
            # ASGI spec: response header names MUST be lowercase bytes.
            response_header_bytes = self._response_header.lower().encode("latin-1")
            rid_bytes = rid.encode("latin-1")

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((response_header_bytes, rid_bytes))
                    message = {**message, "headers": headers}
                await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Harmless in ASGI (each request has its own Context copy),
            # but keeps parity with the Django middleware and avoids
            # surprises if the app shares state across requests.
            clear_request_id()

    def _extract_header(self, scope) -> Optional[str]:
        for key, value in scope.get("headers", ()):
            if key == self._incoming_header:
                try:
                    return value.decode("latin-1")
                except UnicodeDecodeError:
                    return None
        return None
