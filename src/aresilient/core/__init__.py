r"""Core shared logic for sync and async HTTP operations.

This module contains shared functionality used by both synchronous and
asynchronous HTTP request implementations, including validation, retry
logic, and HTTP method handling.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "RETRY_STATUS_CODES",
    "ClientConfig",
    "execute_http_method",
    "execute_http_method_async",
    "should_retry_exception",
    "should_retry_response",
    "validate_retry_params",
    "validate_timeout",
]


from aresilient.core.config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
    ClientConfig,
)
from aresilient.core.http_logic import (
    execute_http_method,
    execute_http_method_async,
)
from aresilient.core.retry_logic import (
    should_retry_exception,
    should_retry_response,
)
from aresilient.core.validation import validate_retry_params, validate_timeout
