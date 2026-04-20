"""
Framework-agnostic helpers for request-ID middleware.

Both the Django and FastAPI integrations share the same decision logic:
honour an incoming request-ID header if present, otherwise generate one.
Keeping this in a tiny core module means both middlewares stay a thin
adapter over framework-specific request/response APIs.
"""

from typing import Callable, Optional

from ..utils import generate_request_id

DEFAULT_HEADER_NAME = "X-Request-ID"


def resolve_request_id(
    incoming: Optional[str],
    generator: Callable[[], str] = generate_request_id,
) -> str:
    """Pick the incoming request ID if non-empty, else generate a fresh one."""
    if incoming:
        return incoming
    return generator()
