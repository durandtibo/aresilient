r"""Helper functions for handling retry_if predicate logic.

This module provides utility functions to consolidate duplicate retry_if
handling code in request retry functions. The helpers evaluate custom retry
predicates and manage exception/error handling when retries should not
continue.
"""

from __future__ import annotations

__all__ = [
    "handle_exception_with_retry_if",
    "handle_response_with_retry_if",
]

import logging
import time
from typing import TYPE_CHECKING, NoReturn

from aresilient.exceptions import HttpRequestError

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from aresilient.callbacks import FailureInfo

logger: logging.Logger = logging.getLogger(__name__)


def handle_response_with_retry_if(
    response: httpx.Response,
    *,
    retry_if: Callable[[httpx.Response | None, Exception | None], bool],
    url: str,
    method: str,
) -> bool:
    """Handle HTTP response with retry_if predicate.

    This function evaluates the retry_if predicate for a successful response
    (status < 400) or error response (status >= 400) and determines whether
    to retry or raise an error.

    Args:
        response: The HTTP response object.
        retry_if: Custom predicate function to determine whether to retry.
            Called with (response, None).
        url: The URL that was requested.
        method: The HTTP method (e.g., "GET", "POST").

    Returns:
        True if the response should trigger a retry (either because retry_if
        returned True for a success, or returned True for an error).
        False if this is a true success (status < 400 and retry_if returned
        False or None).

    Raises:
        HttpRequestError: If status >= 400 and retry_if returns False,
            indicating a non-retryable error.

    Note:
        This function is designed to consolidate retry_if handling for
        HTTP responses in the main retry functions.
    """
    should_retry = retry_if(response, None)

    # Success case: HTTP status code 2xx or 3xx
    if response.status_code < 400:
        # If retry_if says retry even on success, return True to continue retry loop
        # Otherwise return False to indicate true success
        return should_retry

    # Error case: status >= 400
    if not should_retry:
        logger.debug(
            f"{method} request to {url} failed with status {response.status_code}, "
            f"retry_if predicate returned False"
        )
        raise HttpRequestError(
            method=method,
            url=url,
            message=(
                f"{method} request to {url} failed with status {response.status_code}"
            ),
            status_code=response.status_code,
            response=response,
        )

    # retry_if returned True for error response - will retry
    return True


def handle_exception_with_retry_if(
    exc: Exception,
    *,
    retry_if: Callable[[httpx.Response | None, Exception | None], bool],
    url: str,
    method: str,
    attempt: int,
    max_retries: int,
    on_failure: Callable[[FailureInfo], None] | None,
    start_time: float,
) -> bool:
    """Handle exception with retry_if predicate and callbacks.

    This function evaluates the retry_if predicate for an exception and
    handles the case where retries should not continue. It creates an
    appropriate error, invokes the on_failure callback if provided, and
    raises the error.

    Args:
        exc: The exception that was raised (TimeoutException or RequestError).
        retry_if: Custom predicate function to determine whether to retry.
            Called with (None, exception).
        url: The URL that was requested.
        method: The HTTP method (e.g., "GET", "POST").
        attempt: The current attempt number (0-indexed).
        max_retries: Maximum number of retry attempts.
        on_failure: Optional callback to invoke when all retries are exhausted.
        start_time: The timestamp when the request started.

    Returns:
        True if the predicate indicates retry should continue and attempts
        remain. Does not return if retry should not continue (raises instead).

    Raises:
        HttpRequestError: If retry_if returns False or max retries reached.
            The original exception is chained as the cause.

    Note:
        This function is designed to consolidate duplicate retry_if handling
        code for TimeoutException and RequestError in the main retry functions.
    """
    should_retry = retry_if(None, exc)

    # If retry_if says no or we're out of attempts, handle final error
    if not should_retry or attempt == max_retries:
        # Create appropriate error based on exception type
        import httpx

        if isinstance(exc, httpx.TimeoutException):
            logger.debug(
                f"{method} request to {url} timed out, "
                f"retry_if predicate returned {should_retry}"
            )
            error = HttpRequestError(
                method=method,
                url=url,
                message=f"{method} request to {url} timed out ({attempt + 1} attempts)",
                cause=exc,
            )
        else:
            # RequestError or subclass
            error_type = type(exc).__name__
            logger.debug(
                f"{method} request to {url} encountered {error_type}, "
                f"retry_if predicate returned {should_retry}"
            )
            error = HttpRequestError(
                method=method,
                url=url,
                message=(
                    f"{method} request to {url} failed after {attempt + 1} attempts: {exc}"
                ),
                cause=exc,
            )

        # Invoke on_failure callback if provided
        if on_failure is not None:
            from aresilient.callbacks import FailureInfo

            failure_info = FailureInfo(
                url=url,
                method=method,
                attempt=attempt + 1,
                max_retries=max_retries,
                error=error,
                status_code=None,
                total_time=time.time() - start_time,
            )
            on_failure(failure_info)

        raise error from exc

    # Predicate says retry and we have attempts remaining
    return True
