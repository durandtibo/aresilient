r"""Utility functions for HTTP request handling and retry logic.

This module provides helper functions for managing HTTP request retries,
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

import logging
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, NoReturn

from aresilient.exceptions import HttpRequestError

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo

logger: logging.Logger = logging.getLogger(__name__)


def validate_retry_params(
    max_retries: int,
    backoff_factor: float,
    jitter_factor: float = 0.0,
    timeout: float | httpx.Timeout | None = None,
) -> None:
    """Validate retry parameters.

    Args:
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0. A value of 0 means no retries (only the initial attempt).
        backoff_factor: Factor for exponential backoff between retries.
            Must be >= 0.
        jitter_factor: Factor for adding random jitter to backoff delays.
            Must be >= 0. Recommended value is 0.1 for 10% jitter.
        timeout: Maximum seconds to wait for the server response.
            Must be > 0 if provided as a numeric value.

    Raises:
        ValueError: If max_retries, backoff_factor, or jitter_factor are negative,
            or if timeout is non-positive.

    Example:
        ```pycon
        >>> from aresilient.utils import validate_retry_params
        >>> validate_retry_params(max_retries=3, backoff_factor=0.5)
        >>> validate_retry_params(max_retries=3, backoff_factor=0.5, jitter_factor=0.1)
        >>> validate_retry_params(max_retries=3, backoff_factor=0.5, timeout=10.0)
        >>> validate_retry_params(max_retries=-1, backoff_factor=0.5)  # doctest: +SKIP

        ```
    """
    if max_retries < 0:
        msg = f"max_retries must be >= 0, got {max_retries}"
        raise ValueError(msg)
    if backoff_factor < 0:
        msg = f"backoff_factor must be >= 0, got {backoff_factor}"
        raise ValueError(msg)
    if jitter_factor < 0:
        msg = f"jitter_factor must be >= 0, got {jitter_factor}"
        raise ValueError(msg)
    if timeout is not None and isinstance(timeout, (int, float)) and timeout <= 0:
        msg = f"timeout must be > 0, got {timeout}"
        raise ValueError(msg)


def parse_retry_after(retry_after_header: str | None) -> float | None:
    """Parse the Retry-After header value from an HTTP response.

    The Retry-After header can be specified in two formats according to RFC 7231:
    1. An integer representing the number of seconds to wait (e.g., "120")
    2. An HTTP-date in RFC 5322 format (e.g., "Wed, 21 Oct 2015 07:28:00 GMT")

    This function attempts to parse both formats and returns the number of seconds
    to wait. If parsing fails or the header is absent, it returns None to allow
    the caller to use the default exponential backoff strategy.

    Args:
        retry_after_header: The value of the Retry-After header as a string,
            or None if the header is not present in the response.

    Returns:
        The number of seconds to wait before retrying, or None if:
        - The header is not present (retry_after_header is None)
        - The header value cannot be parsed as either an integer or HTTP-date
        For HTTP-date format, negative values (dates in the past) are clamped to 0.0.

    Example:
        ```pycon
        >>> from aresilient.utils import parse_retry_after
        >>> # Parse integer seconds
        >>> parse_retry_after("120")
        120.0
        >>> parse_retry_after("0")
        0.0
        >>> # No header present
        >>> parse_retry_after(None)
        >>> # Invalid format
        >>> parse_retry_after("invalid")

        ```
    """
    if retry_after_header is None:
        return None

    # Try parsing as an integer (seconds)
    try:
        return float(retry_after_header)
    except ValueError:
        pass

    # Try parsing as HTTP-date (RFC 5322 format)
    try:
        retry_date: datetime = parsedate_to_datetime(retry_after_header)
        now = datetime.now(timezone.utc)
        delta_seconds = (retry_date - now).total_seconds()
        # Ensure we don't return negative values
        return max(0.0, delta_seconds)
    except (ValueError, TypeError, OverflowError):
        logger.debug(f"Failed to parse Retry-After header: {retry_after_header!r}")
        return None


def calculate_sleep_time(
    attempt: int,
    backoff_factor: float,
    jitter_factor: float,
    response: httpx.Response | None,
) -> float:
    """Calculate sleep time for retry with exponential backoff and
    jitter.

    This function implements an exponential backoff strategy with optional
    jitter for retrying failed HTTP requests. It also supports the Retry-After
    header when present in the server response, which takes precedence over
    the exponential backoff calculation.

    The sleep time is calculated as follows:
    1. Determine base sleep time:
       - If Retry-After header is present: use that value
       - Otherwise: backoff_factor * (2 ** attempt)
    2. Apply jitter (if jitter_factor > 0):
       - jitter = random.uniform(0, jitter_factor) * base_sleep_time
       - total_sleep_time = base_sleep_time + jitter

    Args:
        attempt: The current attempt number (0-indexed). For example,
            attempt=0 is the first retry, attempt=1 is the second retry, etc.
        backoff_factor: Factor for exponential backoff between retries.
            The base wait time is calculated as: backoff_factor * (2 ** attempt).
        jitter_factor: Factor for adding random jitter to backoff delays.
            The jitter is calculated as: random.uniform(0, jitter_factor) * base_sleep_time,
            and this jitter is ADDED to the base sleep time. Set to 0 to disable jitter.
            Recommended value is 0.1 to add up to 10% additional random delay.
        response: The HTTP response object (if available). Used to extract
            the Retry-After header if present.

    Returns:
        The calculated sleep time in seconds, including any jitter applied.

    Example:
        ```pycon
        >>> from aresilient.utils import calculate_sleep_time
        >>> # First retry with backoff_factor=0.3, no jitter
        >>> calculate_sleep_time(0, 0.3, 0.0, None)
        0.3
        >>> # Second retry
        >>> calculate_sleep_time(1, 0.3, 0.0, None)
        0.6
        >>> # Third retry
        >>> calculate_sleep_time(2, 0.3, 0.0, None)
        1.2

        ```
    """
    # Check for Retry-After header in the response (if available)
    retry_after_sleep: float | None = None
    if response is not None and hasattr(response, "headers"):
        retry_after_header = response.headers.get("Retry-After")
        retry_after_sleep = parse_retry_after(retry_after_header)

    # Use Retry-After if available, otherwise use exponential backoff
    if retry_after_sleep is not None:
        sleep_time = retry_after_sleep
        logger.debug(f"Using Retry-After header value: {sleep_time:.2f}s")
    else:
        sleep_time = backoff_factor * (2**attempt)

    # Add jitter if jitter_factor is configured
    if jitter_factor > 0:
        jitter = random.uniform(0, jitter_factor) * sleep_time  # noqa: S311
        total_sleep_time = sleep_time + jitter
        logger.debug(
            f"Waiting {total_sleep_time:.2f}s before retry (base={sleep_time:.2f}s, jitter={jitter:.2f}s)"
        )
    else:
        total_sleep_time = sleep_time
        logger.debug(f"Waiting {total_sleep_time:.2f}s before retry")

    return total_sleep_time


def handle_response(
    response: httpx.Response,
    url: str,
    method: str,
    status_forcelist: tuple[int, ...],
) -> None:
    """Handle HTTP response and raise error for non-retryable status
    codes.

    This function checks the HTTP response status code and raises an error if
    the status code is not in the retryable status list. This allows the retry
    logic to distinguish between transient errors (e.g., 503 Service Unavailable)
    that should be retried and permanent errors (e.g., 404 Not Found) that should
    fail immediately.

    Args:
        response: The HTTP response object to validate.
        url: The URL that was requested, used in error messages.
        method: The HTTP method name (e.g., "GET", "POST"), used in error messages.
        status_forcelist: Tuple of HTTP status codes that are considered
            retryable (e.g., (429, 500, 502, 503, 504)). If the response status
            code is not in this tuple, an error is raised.

    Raises:
        HttpRequestError: If the response status code is not in status_forcelist,
            indicating a non-retryable error (e.g., 404, 401, 403).

    Example:
        ```pycon
        >>> import httpx
        >>> from aresilient.utils import handle_response
        >>> # This would pass for a retryable status code
        >>> # handle_response(response, "https://api.example.com", "GET", (429, 503))

        ```
    """
    # Non-retryable HTTP error (e.g., 404, 401, 403)
    if response.status_code not in status_forcelist:
        logger.debug(
            f"{method} request to {url} failed with non-retryable status {response.status_code}"
        )
        raise HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} failed with status {response.status_code}",
            status_code=response.status_code,
            response=response,
        )


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

    Example:
        ```pycon
        >>> from aresilient.utils import handle_timeout_exception
        >>> # This would raise an error on the last attempt
        >>> # handle_timeout_exception(exc, "https://api.example.com", "GET", 3, 3)

        ```
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

    Example:
        ```pycon
        >>> from aresilient.utils import handle_request_error
        >>> # This would raise an error on the last attempt
        >>> # handle_request_error(exc, "https://api.example.com", "GET", 3, 3)

        ```
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
        attempt: The current attempt number (0-indexed).
        max_retries: Maximum number of retry attempts.
    """
    if on_request is not None:
        request_info: RequestInfo = {
            "url": url,
            "method": method,
            "attempt": attempt + 1,
            "max_retries": max_retries,
        }
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
        attempt: The attempt number that succeeded (0-indexed).
        max_retries: Maximum number of retry attempts.
        response: The successful HTTP response object.
        start_time: The timestamp when the request started.
    """
    if on_success is not None:
        response_info: ResponseInfo = {
            "url": url,
            "method": method,
            "attempt": attempt + 1,
            "max_retries": max_retries,
            "response": response,
            "total_time": time.time() - start_time,
        }
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
        attempt: The current attempt number (0-indexed).
        max_retries: Maximum number of retry attempts.
        sleep_time: The sleep time in seconds before this retry.
        last_error: The exception that triggered the retry (if any).
        last_status_code: The HTTP status code that triggered the retry (if any).
    """
    if on_retry is not None:
        retry_info: RetryInfo = {
            "url": url,
            "method": method,
            "attempt": attempt + 2,  # Next attempt number
            "max_retries": max_retries,
            "wait_time": sleep_time,
            "error": last_error,
            "status_code": last_status_code,
        }
        on_retry(retry_info)


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
            failure_info: FailureInfo = {
                "url": url,
                "method": method,
                "attempt": attempt + 1,
                "max_retries": max_retries,
                "error": err,
                "status_code": None,
                "total_time": time.time() - start_time,
            }
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
            failure_info: FailureInfo = {
                "url": url,
                "method": method,
                "attempt": max_retries + 1,
                "max_retries": max_retries,
                "error": error,
                "status_code": None,
                "total_time": total_time,
            }
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
        failure_info: FailureInfo = {
            "url": url,
            "method": method,
            "attempt": max_retries + 1,
            "max_retries": max_retries,
            "error": error,
            "status_code": response.status_code,
            "total_time": total_time,
        }
        on_failure(failure_info)

    raise error
