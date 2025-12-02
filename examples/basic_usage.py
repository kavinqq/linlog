"""
Basic Usage Example

Demonstrates how to use linlog's basic features
"""

import logging
import uuid
from linlog import (
    StandardFormatter,
    DailyRotatingHandler,
    UUIDFilter,
    set_request_id,
    clear_request_id
)


def setup_logging():
    """Setup logging with linlog components"""
    # Create logger
    logger = logging.getLogger('myapp')
    logger.setLevel(logging.DEBUG)

    # Create handler with daily rotation
    handler = DailyRotatingHandler(
        filename='logs/app.log',
        when='midnight',
        backupCount=30,
        encoding='utf-8'
    )
    handler.setLevel(logging.DEBUG)

    # Add UUID filter
    handler.addFilter(UUIDFilter())

    # Set formatter
    formatter = StandardFormatter()
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    # Also add console handler for demo
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(UUIDFilter())
    logger.addHandler(console_handler)

    return logger


def simulate_request(logger, request_num):
    """Simulate a request with UUID tracking"""
    # Set request ID at start of request
    request_id = str(uuid.uuid4())[:8]  # Short UUID for demo
    set_request_id(request_id)

    # All logs in this request will have the same UUID
    logger.info(f"Request {request_num} started")
    logger.debug(f"Processing request {request_num}")
    logger.info(f"Request {request_num} completed")

    # Clear request ID after request
    clear_request_id()


if __name__ == '__main__':
    print("=== linlog Basic Usage Example ===\n")

    # Setup logging
    logger = setup_logging()

    print("Log output format: [time][level][logger:line]：message")
    print("With UUID filter, request_id will be tracked\n")

    # Simulate multiple requests
    for i in range(3):
        simulate_request(logger, i + 1)
        print()

    print("Check logs/app.log for the output!")
    print("\nLog format example:")
    print("[2025-12-02 11:02:04][INFO][myapp:58]：Request 1 started")
