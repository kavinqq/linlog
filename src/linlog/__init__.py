"""
linlog - Simple Python logging utilities

Features:
- StandardFormatter: [time][level][name:line]：message
- DailyRotatingHandler: Daily log rotation with custom naming
- UUIDFilter: Request ID tracking for log correlation
"""

__version__ = "0.1.0"
__author__ = "Kuan Lin"

from .formatters import StandardFormatter, JSONFormatter
from .handlers import DailyRotatingHandler
from .filters import UUIDFilter
from .context import set_request_id, get_request_id, clear_request_id
from .utils import generate_request_id

__all__ = [
    # Formatters
    'StandardFormatter',
    'JSONFormatter',
    # Handlers
    'DailyRotatingHandler',
    # Filters
    'UUIDFilter',
    # Context management
    'set_request_id',
    'get_request_id',
    'clear_request_id',
    # Request ID generation
    'generate_request_id',
]
