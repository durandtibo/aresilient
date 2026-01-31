r"""Callback types and data structures for observability.

This module provides callback support for the aresilient library, enabling
users to hook into the retry lifecycle for logging, metrics, alerting, and
custom retry decisions.

The callback system provides four key lifecycle hooks:
- on_request: Called before each request attempt
- on_retry: Called before each retry (after backoff delay)
- on_success: Called when a request succeeds
- on_failure: Called when all retries are exhausted

Example:
    ```pycon
    >>> from aresilient import get_with_automatic_retry
    >>> def log_retry(retry_info):
    ...     print(f"Retry {retry_info['attempt']}/{retry_info['max_retries']}")
    ...
    >>> response = get_with_automatic_retry(
    ...     "https://api.example.com/data", on_retry=log_retry
    ... )  # doctest: +SKIP

    ```
"""

from __future__ import annotations

__all__ = [
    "CallbackInfo",
    "FailureInfo",
    "RequestInfo",
    "ResponseInfo",
    "RetryInfo",
]

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    import httpx


class RequestInfo(TypedDict, total=False):
    """Information passed to on_request callback.

    Attributes:
        url: The URL being requested.
        method: The HTTP method (e.g., "GET", "POST").
        attempt: The current attempt number (1-indexed). First attempt is 1.
        max_retries: Maximum number of retry attempts configured.
    """

    url: str
    method: str
    attempt: int
    max_retries: int


class RetryInfo(TypedDict, total=False):
    """Information passed to on_retry callback.

    Attributes:
        url: The URL being requested.
        method: The HTTP method (e.g., "GET", "POST").
        attempt: The current attempt number (1-indexed). First retry is attempt 2.
        max_retries: Maximum number of retry attempts configured.
        wait_time: The sleep time in seconds before this retry.
        error: The exception that triggered the retry (if any).
        status_code: The HTTP status code that triggered the retry (if any).
    """

    url: str
    method: str
    attempt: int
    max_retries: int
    wait_time: float
    error: Exception | None
    status_code: int | None


class ResponseInfo(TypedDict, total=False):
    """Information passed to on_success callback.

    Attributes:
        url: The URL that was requested.
        method: The HTTP method (e.g., "GET", "POST").
        attempt: The attempt number that succeeded (1-indexed).
        max_retries: Maximum number of retry attempts configured.
        response: The successful HTTP response object.
        total_time: Total time spent on all attempts including backoff (seconds).
    """

    url: str
    method: str
    attempt: int
    max_retries: int
    response: httpx.Response
    total_time: float


class FailureInfo(TypedDict, total=False):
    """Information passed to on_failure callback.

    Attributes:
        url: The URL that was requested.
        method: The HTTP method (e.g., "GET", "POST").
        attempt: The final attempt number (1-indexed).
        max_retries: Maximum number of retry attempts configured.
        error: The final exception that caused the failure.
        status_code: The final HTTP status code (if any).
        total_time: Total time spent on all attempts including backoff (seconds).
    """

    url: str
    method: str
    attempt: int
    max_retries: int
    error: Exception
    status_code: int | None
    total_time: float


class CallbackInfo(TypedDict, total=False):
    """Unified callback information structure (for internal use).

    This is a superset of all callback info types, used internally to
    simplify callback invocation logic.
    """

    url: str
    method: str
    attempt: int
    max_retries: int
    wait_time: float
    error: Exception | None
    status_code: int | None
    response: httpx.Response | None
    total_time: float
