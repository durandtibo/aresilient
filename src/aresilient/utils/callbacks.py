r"""Callback invocation utilities for HTTP request lifecycle events.

This module provides functions for invoking user-defined callbacks at
various points in the HTTP request lifecycle, including before requests,
after success, before retries, and on failures.
"""

from __future__ import annotations

__all__ = ["invoke_on_request", "invoke_on_retry", "invoke_on_success"]

import time
from typing import TYPE_CHECKING

from aresilient.callbacks import RequestInfo, ResponseInfo, RetryInfo

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx


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
        request_info = RequestInfo(
            url=url,
            method=method,
            attempt=attempt + 1,
            max_retries=max_retries,
        )
        on_request(request_info)


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
        response_info = ResponseInfo(
            url=url,
            method=method,
            attempt=attempt + 1,
            max_retries=max_retries,
            response=response,
            total_time=time.time() - start_time,
        )
        on_success(response_info)


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
        retry_info = RetryInfo(
            url=url,
            method=method,
            attempt=attempt + 2,  # Next attempt number
            max_retries=max_retries,
            wait_time=sleep_time,
            error=last_error,
            status_code=last_status_code,
        )
        on_retry(retry_info)
