r"""aresnet - Resilient HTTP request library with automatic retry logic.

This package provides resilient HTTP request functionality with automatic
retry logic and exponential backoff. Built on top of the modern httpx library,
it simplifies handling transient failures in HTTP communications, making your
applications more robust and fault-tolerant.

Key Features:
    - Automatic retry logic for transient HTTP errors (429, 500, 502, 503, 504)
    - Exponential backoff with optional jitter to prevent thundering herd problems
    - Retry-After header support (both integer seconds and HTTP-date formats)
    - Complete HTTP method support (GET, POST, PUT, DELETE, PATCH)
    - Full async support for high-performance applications
    - Configurable timeout, retry attempts, backoff factors, and jitter
    - Enhanced error handling with detailed exception information

Example:
    ```pycon
    >>> from aresnet import get_with_automatic_retry
    >>> response = get_with_automatic_retry("https://api.example.com/data")  # doctest: +SKIP

    ```
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_BACKOFF_FACTOR",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "RETRY_STATUS_CODES",
    "HttpRequestError",
    "__version__",
    "delete_with_automatic_retry",
    "delete_with_automatic_retry_async",
    "get_with_automatic_retry",
    "get_with_automatic_retry_async",
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

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresnet.delete import delete_with_automatic_retry
from aresnet.delete_async import delete_with_automatic_retry_async
from aresnet.exceptions import HttpRequestError
from aresnet.get import get_with_automatic_retry
from aresnet.get_async import get_with_automatic_retry_async
from aresnet.patch import patch_with_automatic_retry
from aresnet.patch_async import patch_with_automatic_retry_async
from aresnet.post import post_with_automatic_retry
from aresnet.post_async import post_with_automatic_retry_async
from aresnet.put import put_with_automatic_retry
from aresnet.put_async import put_with_automatic_retry_async
from aresnet.request import request_with_automatic_retry
from aresnet.request_async import request_with_automatic_retry_async

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    # Package is not installed, fallback if needed
    __version__ = "0.0.0"
