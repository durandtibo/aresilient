r"""Contain utility functions for asynchronous HTTP requests with
automatic retry logic."""

from __future__ import annotations

__all__ = ["request_with_automatic_retry_async"]

import asyncio
import logging
import random
from typing import TYPE_CHECKING, Any

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    RETRY_STATUS_CODES,
)
from aresnet.utils import parse_retry_after

if TYPE_CHECKING:
    from collections.abc import Callable, Awaitable

import httpx

from aresnet.exceptions import HttpRequestError

logger: logging.Logger = logging.getLogger(__name__)


def _should_retry_status(status_code: int, status_forcelist: tuple[int, ...]) -> bool:
    """Check if a status code should trigger a retry.

    Args:
        status_code: The HTTP status code to check.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.

    Returns:
        True if the status code is in the retry list, False otherwise.
    """
    return status_code in status_forcelist


def _calculate_sleep_time(
    attempt: int,
    backoff_factor: float,
    jitter_factor: float,
    response: httpx.Response | None,
) -> float:
    """Calculate sleep time for retry with exponential backoff and jitter.

    Args:
        attempt: The current attempt number (0-indexed).
        backoff_factor: Factor for exponential backoff between retries.
        jitter_factor: Factor for adding random jitter to backoff delays.
        response: The HTTP response object (if available).

    Returns:
        The calculated sleep time in seconds.
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


def _handle_response(
    response: httpx.Response,
    url: str,
    method: str,
    status_forcelist: tuple[int, ...],
) -> None:
    """Handle HTTP response based on status code.

    Args:
        response: The HTTP response object.
        url: The URL that was requested.
        method: The HTTP method name.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.

    Raises:
        HttpRequestError: If the status code is not retryable (not in status_forcelist).
    """
    # Non-retryable HTTP error (e.g., 404, 401, 403)
    if not _should_retry_status(response.status_code, status_forcelist):
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


def _handle_timeout_exception(
    exc: httpx.TimeoutException,
    url: str,
    method: str,
    attempt: int,
    max_retries: int,
) -> None:
    """Handle timeout exceptions during request.

    Args:
        exc: The timeout exception that was raised.
        url: The URL that was requested.
        method: The HTTP method name.
        attempt: The current attempt number (0-indexed).
        max_retries: Maximum number of retry attempts.

    Raises:
        HttpRequestError: If max retries have been exhausted.
    """
    logger.debug(f"{method} request to {url} timed out on attempt {attempt + 1}/{max_retries + 1}")
    if attempt == max_retries:
        raise HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} timed out ({max_retries + 1} attempts)",
            cause=exc,
        ) from exc


def _handle_request_error(
    exc: httpx.RequestError,
    url: str,
    method: str,
    attempt: int,
    max_retries: int,
) -> None:
    """Handle request errors during request.

    Args:
        exc: The request error that was raised.
        url: The URL that was requested.
        method: The HTTP method name.
        attempt: The current attempt number (0-indexed).
        max_retries: Maximum number of retry attempts.

    Raises:
        HttpRequestError: If max retries have been exhausted.
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


async def request_with_automatic_retry_async(
    url: str,
    method: str,
    request_func: Callable[..., Awaitable[httpx.Response]],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    jitter_factor: float = 0.0,
    **kwargs: Any,
) -> httpx.Response:
    """Perform an async HTTP request with automatic retry logic.

    This function implements a retry mechanism with exponential backoff for
    handling transient HTTP errors. It attempts the request up to max_retries + 1
    times, waiting progressively longer between each retry.

    The retry logic handles three types of failures:
    1. Retryable HTTP status codes (e.g., 429, 500, 502, 503, 504)
    2. Timeout exceptions (httpx.TimeoutException)
    3. General network errors (httpx.RequestError)

    Backoff Strategy:
    - Exponential backoff: backoff_factor * (2 ** attempt)
    - Jitter: Optional randomization added to prevent thundering herd
    - Retry-After header: If present in the response (429/503), the server's
      suggested wait time is used instead of exponential backoff

    Args:
        url: The URL to send the request to.
        method: The HTTP method name (e.g., "GET", "POST") for logging.
        request_func: The async function to call to make the request (e.g.,
            client.get, client.post).
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** attempt) seconds,
            where attempt is 0-indexed (0, 1, 2, ...).
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        jitter_factor: Factor for adding random jitter to backoff delays. The jitter
            is calculated as: random.uniform(0, jitter_factor) * base_sleep_time.
            Set to 0 to disable jitter (default). Recommended value is 0.1 for 10%
            jitter to prevent thundering herd issues.
        **kwargs: Additional keyword arguments passed to the request function.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.

    Example:
        ```pycon
        >>> import asyncio
        >>> import httpx
        >>> from aresnet import request_with_automatic_retry_async
        >>> async def example():
        ...     async with httpx.AsyncClient() as client:
        ...         response = await request_with_automatic_retry_async(
        ...             url="https://api.example.com/data",
        ...             method="GET",
        ...             request_func=client.get,
        ...             max_retries=5,
        ...             backoff_factor=1.0,
        ...             jitter_factor=0.1,  # Add 10% jitter
        ...         )
        ...         return response.status_code
        ...
        >>> asyncio.run(example())  # doctest: +SKIP

        ```
    """
    response: httpx.Response | None = None

    # Retry loop: attempt 0 is initial try, 1..max_retries are retries
    for attempt in range(max_retries + 1):
        try:
            response = await request_func(url=url, **kwargs)

            # Success case: HTTP status code 2xx or 3xx
            if response.status_code < 400:
                if attempt > 0:
                    logger.debug(f"{method} request to {url} succeeded on attempt {attempt + 1}")
                return response

            # Client/Server error: check if it's retryable
            _handle_response(response, url, method, status_forcelist)

            # Retryable HTTP status - log and continue to retry
            logger.debug(
                f"{method} request to {url} failed with status {response.status_code} "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )

        except httpx.TimeoutException as exc:
            _handle_timeout_exception(exc, url, method, attempt, max_retries)

        except httpx.RequestError as exc:
            _handle_request_error(exc, url, method, attempt, max_retries)

        # Exponential backoff with jitter before next retry (skip on last attempt since we're about to fail)
        if attempt < max_retries:
            sleep_time = _calculate_sleep_time(attempt, backoff_factor, jitter_factor, response)
            await asyncio.sleep(sleep_time)

    # All retries exhausted with retryable status code - raise final error
    # Note: response cannot be None here because if all attempts raised exceptions,
    # they would have been caught by the exception handlers above and raised before
    # reaching this point.
    if response is None:  # pragma: no cover
        # This should never happen in practice, but we check for type safety
        msg = f"{method} request to {url} failed after {max_retries + 1} attempts"
        raise HttpRequestError(
            method=method,
            url=url,
            message=msg,
        )
    raise HttpRequestError(
        method=method,
        url=url,
        message=(
            f"{method} request to {url} failed with status "
            f"{response.status_code} after {max_retries + 1} attempts"
        ),
        status_code=response.status_code,
        response=response,
    )
