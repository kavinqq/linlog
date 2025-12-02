"""
Context Management

Thread-safe and async-safe request context using contextvars.
Typically used with web framework middleware to track request IDs.
"""

import contextvars
from typing import Optional


_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'request_id',
    default=None
)


def set_request_id(request_id: str) -> None:
    """Set the current request's UUID"""
    _request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get the current request's UUID (or None if not set)"""
    return _request_id_var.get()


def clear_request_id() -> None:
    """Clear the current request's UUID"""
    _request_id_var.set(None)
