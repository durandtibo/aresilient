r"""Shared retry decision logic for sync and async operations.

This module contains the core retry decision logic that is shared between
synchronous and asynchronous retry executors. These functions encapsulate
the logic for determining whether to retry based on HTTP responses and
exceptions.
"""

from __future__ import annotations

__all__ = [
    "should_retry_exception",
    "should_retry_response",
]

import logging
from typing import TYPE_CHECKING

from aresilient.exceptions import HttpRequestError

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

logger: logging.Logger = logging.getLogger(__name__)


def should_retry_response(
    response: httpx.Response,
    url: str,
    method: str,
    status_forcelist: tuple[int, ...],
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None,
) -> tuple[bool, str]:
    """Determine if response should trigger retry.

    This is a stateless function that encapsulates the core retry decision
    logic for HTTP responses. It evaluates the response against configured
    status codes and custom predicates.

    Args:
        response: The HTTP response to evaluate.
        url: The URL being requested.
        method: The HTTP method being used.
        status_forcelist: Tuple of retryable HTTP status codes.
        retry_if: Optional custom retry predicate.

    Returns:
        Tuple of (should_retry, reason).

    Raises:
        HttpRequestError: For non-retryable error responses.
    """
    # Success case (status < 400)
    if response.status_code < 400:
        if retry_if is not None and retry_if(response, None):
            return (True, "retry_if predicate")
        return (False, "success")

    # Error case (status >= 400)
    if retry_if is not None:
        should_retry = retry_if(response, None)
        if not should_retry:
            # retry_if returned False for an error response
            logger.debug(
                f"{method} request to {url} failed with status {response.status_code} "
                f"(retry_if returned False)"
            )
            raise HttpRequestError(
                method=method,
                url=url,
                message=f"{method} request to {url} failed with status {response.status_code}",
                status_code=response.status_code,
                response=response,
            )
        return (should_retry, "retry_if predicate")

    # Check status_forcelist
    is_retryable = response.status_code in status_forcelist
    if not is_retryable:
        # Non-retryable status code
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
    return (is_retryable, f"status {response.status_code}")


def should_retry_exception(
    exception: Exception,
    attempt: int,
    max_retries: int,
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None,
) -> tuple[bool, str]:
    """Determine if exception should trigger retry.

    This is a stateless function that encapsulates the core retry decision
    logic for exceptions. It evaluates the exception against custom predicates
    and retry limits.

    Args:
        exception: The exception to evaluate.
        attempt: Current attempt number (0-indexed).
        max_retries: Maximum number of retries.
        retry_if: Optional custom retry predicate.

    Returns:
        Tuple of (should_retry, reason).
    """
    if retry_if is not None:
        should_retry = retry_if(None, exception)
        if not should_retry or attempt >= max_retries:
            return (False, "retry_if returned False or max retries")
        return (True, "retry_if predicate")

    # Default: retry timeout and request errors
    if attempt >= max_retries:
        return (False, "max retries exhausted")
    return (True, f"{type(exception).__name__}")
