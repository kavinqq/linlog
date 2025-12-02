"""
Log Formatters

Custom logging formatters for consistent log output.
"""

import logging
import json
from datetime import datetime


class StandardFormatter(logging.Formatter):
    """
    Standard log formatter

    Output: [2025-12-02 11:02:04][uuid][INFO][module.name:98]：message
    If no UUID is set, outputs: [2025-12-02 11:02:04][INFO][module.name:98]：message
    """

    def __init__(self, datefmt='%Y-%m-%d %H:%M:%S', show_uuid=True):
        """
        Args:
            datefmt: Date format string
            show_uuid: Whether to include UUID in output (default: True)
        """
        super().__init__(datefmt=datefmt)
        self.show_uuid = show_uuid

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime(self.datefmt)
        level = record.levelname
        location = f"{record.name}:{record.lineno}"
        message = record.getMessage()

        # Build format with optional UUID
        if self.show_uuid and hasattr(record, 'request_id') and record.request_id != 'N/A':
            formatted = f"[{timestamp}][{record.request_id}][{level}][{location}]：{message}"
        else:
            formatted = f"[{timestamp}][{level}][{location}]：{message}"

        if record.exc_info:
            formatted += '\n' + self.formatException(record.exc_info)

        return formatted


class JSONFormatter(logging.Formatter):
    """JSON format log formatter for machine parsing"""

    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        return json.dumps(log_data, ensure_ascii=False)
