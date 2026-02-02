r"""aresilient - Resilient HTTP request library with automatic retry logic.

This package provides resilient HTTP request functionality with automatic
retry logic and backoff strategies. Built on top of the modern httpx library,
it simplifies handling transient failures in HTTP communications, making your
applications more robust and fault-tolerant.

Key Features:
    - Automatic retry logic for transient HTTP errors (429, 500, 502, 503, 504)
    - Multiple backoff strategies: Exponential, Linear, Fibonacci, Constant, and custom
    - Optional jitter to prevent thundering herd problems
    - Retry-After header support (both integer seconds and HTTP-date formats)
    - Complete HTTP method support (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
    - Full async support for high-performance applications
    - Configurable timeout, retry attempts, backoff factors, and jitter
    - Enhanced error handling with detailed exception information
    - Callback/Event system for observability (logging, metrics, alerting)

Example:
    ```pycon
    >>> from aresilient import get_with_automatic_retry, LinearBackoff
    >>> # Use default exponential backoff
    >>> response = get_with_automatic_retry("https://api.example.com/data")  # doctest: +SKIP
    >>> # Use linear backoff strategy
    >>> response = get_with_automatic_retry(
    ...     "https://api.example.com/data", backoff_strategy=LinearBackoff(base_delay=1.0)
    ... )  # doctest: +SKIP

    ```
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_BACKOFF_FACTOR",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "RETRY_STATUS_CODES",
    "BackoffStrategy",
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitState",
    "ConstantBackoff",
    "ExponentialBackoff",
    "FailureInfo",
    "FibonacciBackoff",
    "HttpRequestError",
    "LinearBackoff",
    "RequestInfo",
    "ResponseInfo",
    "RetryInfo",
    "__version__",
    "delete_with_automatic_retry",
    "delete_with_automatic_retry_async",
    "get_with_automatic_retry",
    "get_with_automatic_retry_async",
    "head_with_automatic_retry",
    "head_with_automatic_retry_async",
    "options_with_automatic_retry",
    "options_with_automatic_retry_async",
    "patch_with_automatic_retry",
    "patch_with_automatic_retry_async",
    "post_with_automatic_retry",
    "post_with_automatic_retry_async",
    "put_with_automatic_retry",
    "put_with_automatic_retry_async",
    "request_with_automatic_retry",
    "request_with_automatic_retry_async",
]

from importlib.metadata import PackageNotFoundError, version

from aresilient.backoff import (
    BackoffStrategy,
    ConstantBackoff,
    ExponentialBackoff,
    FibonacciBackoff,
    LinearBackoff,
)
from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo
from aresilient.circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitState
from aresilient.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresilient.delete import delete_with_automatic_retry
from aresilient.delete_async import delete_with_automatic_retry_async
from aresilient.exceptions import HttpRequestError
from aresilient.get import get_with_automatic_retry
from aresilient.get_async import get_with_automatic_retry_async
from aresilient.head import head_with_automatic_retry
from aresilient.head_async import head_with_automatic_retry_async
from aresilient.options import options_with_automatic_retry
from aresilient.options_async import options_with_automatic_retry_async
from aresilient.patch import patch_with_automatic_retry
from aresilient.patch_async import patch_with_automatic_retry_async
from aresilient.post import post_with_automatic_retry
from aresilient.post_async import post_with_automatic_retry_async
from aresilient.put import put_with_automatic_retry
from aresilient.put_async import put_with_automatic_retry_async
from aresilient.request import request_with_automatic_retry
from aresilient.request_async import request_with_automatic_retry_async

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    # Package is not installed, fallback if needed
    __version__ = "0.0.0"
