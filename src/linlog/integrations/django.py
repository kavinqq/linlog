"""
Django integration for linlog.

Usage (settings.py):

    MIDDLEWARE = [
        "linlog.integrations.django.RequestIDMiddleware",
        ...
    ]

    # Optional — override defaults:
    LINLOG_REQUEST_ID_HEADER = "X-Request-ID"   # incoming header
    LINLOG_REQUEST_ID_RESPONSE_HEADER = "X-Request-ID"  # set to None to disable
"""

from typing import Callable, Optional

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from ..context import clear_request_id, set_request_id
from ..utils import generate_request_id
from ._core import DEFAULT_HEADER_NAME, resolve_request_id


def _django_meta_key(header_name: str) -> str:
    """Convert 'X-Request-ID' -> 'HTTP_X_REQUEST_ID' (Django META convention)."""
    return "HTTP_" + header_name.upper().replace("-", "_")


class RequestIDMiddleware(MiddlewareMixin):
    """
    Reads the request-ID from an incoming header (or generates one), stores
    it in the linlog ContextVar for the duration of the request, and writes
    it back on the response for downstream correlation.
    """

    # Subclasses can override these without touching Django settings.
    header_name: str = DEFAULT_HEADER_NAME
    response_header_name: Optional[str] = DEFAULT_HEADER_NAME
    generator: Callable[[], str] = staticmethod(generate_request_id)

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self._incoming_meta_key = _django_meta_key(
            getattr(settings, "LINLOG_REQUEST_ID_HEADER", self.header_name)
        )
        self._response_header = getattr(
            settings,
            "LINLOG_REQUEST_ID_RESPONSE_HEADER",
            self.response_header_name,
        )

    def process_request(self, request):
        incoming = request.META.get(self._incoming_meta_key)
        rid = resolve_request_id(incoming, self.generator)
        set_request_id(rid)
        request.request_id = rid

    def process_response(self, request, response):
        rid = getattr(request, "request_id", None)
        if rid and self._response_header:
            response[self._response_header] = rid
        # Clear so worker threads reused across requests don't leak IDs.
        clear_request_id()
        return response
