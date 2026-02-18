r"""Utility functions for HTTP request handling and retry logic.

This package provides helper functions for managing HTTP request
retries, including parameter validation, Retry-After header parsing, and
error handling for various HTTP failure scenarios.
"""

from __future__ import annotations

__all__ = [
    "handle_exception_with_callback",
    "handle_exception_with_retry_if",
    "handle_request_error",
    "handle_response",
    "handle_response_with_retry_if",
    "handle_timeout_exception",
    "parse_retry_after",
    "raise_final_error",
]


from aresilient.utils.exceptions import (
    handle_exception_with_callback,
    handle_request_error,
    handle_timeout_exception,
    raise_final_error,
)
from aresilient.utils.response import handle_response
from aresilient.utils.retry_after import parse_retry_after
from aresilient.utils.retry_if_handler import (
    handle_exception_with_retry_if,
    handle_response_with_retry_if,
)
