r"""Exception handling utilities for HTTP request retries.

This module provides functions for handling various types of exceptions
that can occur during HTTP requests, including timeouts, connection errors,
and other request failures.
"""

from __future__ import annotations

__all__ = [
    "handle_exception_with_callback",
    "handle_request_error",
    "handle_timeout_exception",
    "raise_final_error",
]

import logging
import time
from typing import TYPE_CHECKING, NoReturn

from aresilient.callbacks import FailureInfo
from aresilient.exceptions import HttpRequestError

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

logger: logging.Logger = logging.getLogger(__name__)


def handle_timeout_exception(
    exc: Exception,
    url: str,
    method: str,
    attempt: int,
    max_retries: int,
) -> None:
    """Handle timeout exceptions during HTTP requests.

    This function processes timeout exceptions that occur during HTTP requests.
    It logs the timeout event and raises an HttpRequestError if all retry
    attempts have been exhausted. If there are remaining retries, the function
    returns silently to allow the retry loop to continue.

    Args:
        exc: The timeout exception that was raised (typically httpx.TimeoutException).
        url: The URL that was requested, used in error messages.
        method: The HTTP method name (e.g., "GET", "POST"), used in error messages.
        attempt: The current attempt number (0-indexed). For example, attempt=0
            is the initial request, attempt=1 is the first retry, etc.
        max_retries: Maximum number of retry attempts configured. The total number
            of attempts is max_retries + 1 (including the initial attempt).

    Raises:
        HttpRequestError: If attempt == max_retries, indicating that all retry
            attempts have been exhausted. The original exception is chained as
            the cause.

    Note:
        This is an internal utility function. If there are remaining retries
        (attempt < max_retries), the function returns without raising, allowing
        the retry loop to continue.
    """
    logger.debug(f"{method} request to {url} timed out on attempt {attempt + 1}/{max_retries + 1}")
    if attempt == max_retries:
        raise HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} timed out ({max_retries + 1} attempts)",
            cause=exc,
        ) from exc


def handle_request_error(
    exc: Exception,
    url: str,
    method: str,
    attempt: int,
    max_retries: int,
) -> None:
    """Handle network and connection errors during HTTP requests.

    This function processes various request errors that can occur during HTTP
    requests, such as connection errors, network errors, or other httpx.RequestError
    exceptions. It logs the error with detailed information including the error type
    and raises an HttpRequestError if all retry attempts have been exhausted.

    Args:
        exc: The request error that was raised (typically httpx.RequestError or
            a subclass like httpx.ConnectError, httpx.PoolTimeout, etc.).
        url: The URL that was requested, used in error messages.
        method: The HTTP method name (e.g., "GET", "POST"), used in error messages.
        attempt: The current attempt number (0-indexed). For example, attempt=0
            is the initial request, attempt=1 is the first retry, etc.
        max_retries: Maximum number of retry attempts configured. The total number
            of attempts is max_retries + 1 (including the initial attempt).

    Raises:
        HttpRequestError: If attempt == max_retries, indicating that all retry
            attempts have been exhausted. The original exception is chained as
            the cause.

    Note:
        This is an internal utility function. If there are remaining retries
        (attempt < max_retries), the function returns without raising, allowing
        the retry loop to continue.
    """
    error_type = type(exc).__name__
    logger.debug(
        f"{method} request to {url} encountered {error_type} on attempt "
        f"{attempt + 1}/{max_retries + 1}: {exc}"
    )
    if attempt == max_retries:
        raise HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} failed after {max_retries + 1} attempts: {exc}",
            cause=exc,
        ) from exc


def handle_exception_with_callback(
    exc: Exception,
    *,
    url: str,
    method: str,
    attempt: int,
    max_retries: int,
    handler_func: Callable[[Exception, str, str, int, int], None],
    on_failure: Callable[[FailureInfo], None] | None,
    start_time: float,
) -> None:
    """Handle exception and invoke on_failure callback if final attempt.

    Args:
        exc: The exception to handle.
        url: The URL that was requested.
        method: The HTTP method (e.g., "GET", "POST").
        attempt: The current attempt number (0-indexed).
        max_retries: Maximum number of retry attempts.
        handler_func: Function to handle the exception (raises if final attempt).
        on_failure: Optional callback to invoke when all retries are exhausted.
        start_time: The timestamp when the request started.

    Raises:
        HttpRequestError: If this is the final attempt.
    """
    try:
        handler_func(exc, url, method, attempt, max_retries)
    except HttpRequestError as err:
        # This is the final attempt - call on_failure callback
        if on_failure is not None:
            failure_info = FailureInfo(
                url=url,
                method=method,
                attempt=attempt + 1,
                max_retries=max_retries,
                error=err,
                status_code=None,
                total_time=time.time() - start_time,
            )
            on_failure(failure_info)
        raise


def raise_final_error(
    *,
    url: str,
    method: str,
    max_retries: int,
    response: httpx.Response | None,
    on_failure: Callable[[FailureInfo], None] | None,
    start_time: float,
) -> NoReturn:
    """Create and raise final error after all retries exhausted.

    Args:
        url: The URL that was requested.
        method: The HTTP method (e.g., "GET", "POST").
        max_retries: Maximum number of retry attempts.
        response: The final HTTP response object (if available).
        on_failure: Optional callback to invoke when all retries are exhausted.
        start_time: The timestamp when the request started.

    Raises:
        HttpRequestError: Always raises with details about the failure.
    """
    total_time = time.time() - start_time

    if response is None:  # pragma: no cover
        # This should never happen in practice, but we check for type safety
        msg = f"{method} request to {url} failed after {max_retries + 1} attempts"
        error = HttpRequestError(
            method=method,
            url=url,
            message=msg,
        )

        # Call on_failure callback
        if on_failure is not None:
            failure_info = FailureInfo(
                url=url,
                method=method,
                attempt=max_retries + 1,
                max_retries=max_retries,
                error=error,
                status_code=None,
                total_time=total_time,
            )
            on_failure(failure_info)

        raise error

    error = HttpRequestError(
        method=method,
        url=url,
        message=(
            f"{method} request to {url} failed with status "
            f"{response.status_code} after {max_retries + 1} attempts"
        ),
        status_code=response.status_code,
        response=response,
    )

    # Call on_failure callback
    if on_failure is not None:
        failure_info = FailureInfo(
            url=url,
            method=method,
            attempt=max_retries + 1,
            max_retries=max_retries,
            error=error,
            status_code=response.status_code,
            total_time=total_time,
        )
        on_failure(failure_info)

    raise error
