r"""Utility functions for HTTP request handling and retry logic.

This package provides helper functions for managing HTTP request retries,
including parameter validation, sleep time calculation with exponential
backoff and jitter, Retry-After header parsing, and error handling for
various HTTP failure scenarios.
"""

from __future__ import annotations

__all__ = [
    "calculate_sleep_time",
    "handle_exception_with_callback",
    "handle_request_error",
    "handle_response",
    "handle_timeout_exception",
    "invoke_on_request",
    "invoke_on_retry",
    "invoke_on_success",
    "parse_retry_after",
    "raise_final_error",
    "validate_retry_params",
]

from aresilient.utils.backoff import calculate_sleep_time
from aresilient.utils.callbacks import invoke_on_request, invoke_on_retry, invoke_on_success
from aresilient.utils.exceptions import (
    handle_exception_with_callback,
    handle_request_error,
    handle_timeout_exception,
    raise_final_error,
)
from aresilient.utils.response import handle_response
from aresilient.utils.retry_after import parse_retry_after
from aresilient.utils.validation import validate_retry_params
