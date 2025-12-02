"""
Log Filters

UUID tracking filter for request tracing.
"""

import logging
from .context import get_request_id


class UUIDFilter(logging.Filter):
    """
    Add request UUID to log records

    Reads UUID from context and adds it to each log record as record.request_id
    """

    def filter(self, record):
        request_id = get_request_id()
        record.request_id = request_id if request_id else 'N/A'
        return True
