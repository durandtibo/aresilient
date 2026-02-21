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
    >>> from aresilient import get
    >>> from aresilient.callbacks import RetryInfo
    >>> from aresilient.core import ClientConfig
    >>> def log_retry(retry_info: RetryInfo):
    ...     print(f"Retry {retry_info.attempt}/{retry_info.max_retries + 1}")
    ...
    >>> response = get("https://api.example.com/data", config=ClientConfig(on_retry=log_retry))  # doctest: +SKIP

    ```
"""

from __future__ import annotations

__all__ = [
    "CallbackInfo",
    "FailureInfo",
    "RequestInfo",
    "ResponseInfo",
    "RetryInfo",
    "invoke_on_request",
    "invoke_on_retry",
    "invoke_on_success",
]

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx


@dataclass
class RequestInfo:
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


@dataclass
class RetryInfo:
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


@dataclass
class ResponseInfo:
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


@dataclass
class FailureInfo:
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


@dataclass
class CallbackInfo:
    """Unified callback information structure (for internal use).

    This is a superset of all callback info types, used internally to
    simplify callback invocation logic. Contains all possible fields that
    might be needed by any callback type.

    Attributes:
        url: The URL being requested.
        method: The HTTP method (e.g., "GET", "POST").
        attempt: The current attempt number (1-indexed).
        max_retries: Maximum number of retry attempts configured.
        wait_time: The sleep time in seconds before a retry.
        error: The exception that occurred (if any).
        status_code: The HTTP status code (if any).
        response: The HTTP response object (if any).
        total_time: Total time spent on all attempts including backoff (seconds).
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


def invoke_on_request(
    on_request: Callable[[RequestInfo], None] | None,
    *,
    url: str,
    method: str,
    attempt: int,
    max_retries: int,
) -> None:
    """Invoke on_request callback if provided.

    Args:
        on_request: Optional callback to invoke before each request attempt.
        url: The URL being requested.
        method: The HTTP method (e.g., "GET", "POST").
        attempt: The current attempt number (0-indexed internally). The callback
            receives this as a 1-indexed value (attempt + 1).
        max_retries: Maximum number of retry attempts.
    """
    if on_request is not None:
        on_request(
            RequestInfo(
                url=url,
                method=method,
                attempt=attempt + 1,
                max_retries=max_retries,
            )
        )


def invoke_on_success(
    on_success: Callable[[ResponseInfo], None] | None,
    *,
    url: str,
    method: str,
    attempt: int,
    max_retries: int,
    response: httpx.Response,
    start_time: float,
) -> None:
    """Invoke on_success callback if provided.

    Args:
        on_success: Optional callback to invoke when request succeeds.
        url: The URL that was requested.
        method: The HTTP method (e.g., "GET", "POST").
        attempt: The attempt number that succeeded (0-indexed internally). The
            callback receives this as a 1-indexed value (attempt + 1).
        max_retries: Maximum number of retry attempts.
        response: The successful HTTP response object.
        start_time: The timestamp when the request started.
    """
    if on_success is not None:
        on_success(
            ResponseInfo(
                url=url,
                method=method,
                attempt=attempt + 1,
                max_retries=max_retries,
                response=response,
                total_time=time.time() - start_time,
            )
        )


def invoke_on_retry(
    on_retry: Callable[[RetryInfo], None] | None,
    *,
    url: str,
    method: str,
    attempt: int,
    max_retries: int,
    sleep_time: float,
    last_error: Exception | None,
    last_status_code: int | None,
) -> None:
    """Invoke on_retry callback if provided.

    Args:
        on_retry: Optional callback to invoke before each retry.
        url: The URL being requested.
        method: The HTTP method (e.g., "GET", "POST").
        attempt: The current attempt number (0-indexed internally). The callback
            receives the next attempt number as a 1-indexed value. For example,
            after the first failed attempt (internally attempt=0), the callback
            receives attempt=2 (indicating the second attempt will be tried next).
        max_retries: Maximum number of retry attempts.
        sleep_time: The sleep time in seconds before this retry.
        last_error: The exception that triggered the retry (if any).
        last_status_code: The HTTP status code that triggered the retry (if any).
    """
    if on_retry is not None:
        on_retry(
            RetryInfo(
                url=url,
                method=method,
                attempt=attempt + 2,  # Next attempt number
                max_retries=max_retries,
                wait_time=sleep_time,
                error=last_error,
                status_code=last_status_code,
            )
        )
