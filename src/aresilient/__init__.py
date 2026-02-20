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
    - Context manager API for managing request sessions

Example:
    ```pycon
    >>> from aresilient import get
    >>> from aresilient.backoff import LinearBackoff
    >>> # Use default exponential backoff
    >>> response = get("https://api.example.com/data")  # doctest: +SKIP
    >>> # Use linear backoff strategy
    >>> response = get(
    ...     "https://api.example.com/data", backoff_strategy=LinearBackoff(base_delay=1.0)
    ... )  # doctest: +SKIP
    >>> # Use context manager for multiple requests
    >>> from aresilient import ResilientClient
    >>> from aresilient.core.config import ClientConfig
    >>> with ResilientClient(
    ...     config=ClientConfig(max_retries=5), timeout=30
    ... ) as client:  # doctest: +SKIP
    ...     response1 = client.get("https://api.example.com/data1")
    ...     response2 = client.post("https://api.example.com/data2", json={"key": "value"})
    ...

    ```
"""

from __future__ import annotations

__all__ = [
    "AsyncResilientClient",
    "HttpRequestError",
    "ResilientClient",
    "__version__",
    "delete",
    "delete_async",
    "get",
    "get_async",
    "head",
    "head_async",
    "options",
    "options_async",
    "patch",
    "patch_async",
    "post",
    "post_async",
    "put",
    "put_async",
    "request",
    "request_async",
]

from importlib.metadata import PackageNotFoundError, version

from aresilient.client import ResilientClient
from aresilient.client_async import AsyncResilientClient
from aresilient.delete import delete
from aresilient.delete_async import delete_async
from aresilient.exceptions import HttpRequestError
from aresilient.get import get
from aresilient.get_async import get_async
from aresilient.head import head
from aresilient.head_async import head_async
from aresilient.options import options
from aresilient.options_async import options_async
from aresilient.patch import patch
from aresilient.patch_async import patch_async
from aresilient.post import post
from aresilient.post_async import post_async
from aresilient.put import put
from aresilient.put_async import put_async
from aresilient.request import request
from aresilient.request_async import request_async

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    # Package is not installed, fallback if needed
    __version__ = "0.0.0"
