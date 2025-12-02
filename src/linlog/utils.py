"""
Request ID generation utilities

Provides cryptographically secure random ID generation for request tracking.
"""

import secrets
from typing import Callable, Optional

DEFAULT_ALPHABET = '123456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'

# Custom generator storage
_custom_generator: Optional[Callable[[], str]] = None


def generate_request_id(length: int = 7, alphabet: str = DEFAULT_ALPHABET) -> str:
    """
    Generate a random request ID using cryptographically secure randomness.
    
    Args:
        length: ID length (default: 7, provides ~41 bits of entropy with base62)
        alphabet: Characters to use (default: base62 - 0-9, a-z, A-Z)
    
    Returns:
        Random string like "a7Bx2Kf"
    
    Example:
        >>> from linlog import generate_request_id, set_request_id
        >>> request_id = generate_request_id()
        >>> set_request_id(request_id)
    """
    if _custom_generator is not None:
        return _custom_generator()
    return ''.join(secrets.choice(alphabet) for _ in range(length))
