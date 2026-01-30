r"""Contain utility functions for synchronous HTTP requests with
automatic retry logic."""

from __future__ import annotations

__all__ = ["request_with_automatic_retry"]

import logging
import time
from typing import TYPE_CHECKING, Any

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    RETRY_STATUS_CODES,
)
from aresnet.utils import (
    calculate_sleep_time,
    handle_request_error,
    handle_response,
    handle_timeout_exception,
)

if TYPE_CHECKING:
    from collections.abc import Callable

import httpx

from aresnet.exceptions import HttpRequestError

logger: logging.Logger = logging.getLogger(__name__)


def request_with_automatic_retry(
    url: str,
    method: str,
    request_func: Callable[..., httpx.Response],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    jitter_factor: float = 0.0,
    **kwargs: Any,
) -> httpx.Response:
    """Perform an HTTP request with automatic retry logic.

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
        request_func: The function to call to make the request (e.g.,
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
        >>> import httpx
        >>> from aresnet import request_with_automatic_retry
        >>> with httpx.Client() as client:
        ...     response = request_with_automatic_retry(
        ...         url="https://api.example.com/data",
        ...         method="GET",
        ...         request_func=client.get,
        ...         max_retries=5,
        ...         backoff_factor=1.0,
        ...         jitter_factor=0.1,  # Add 10% jitter
        ...     )  # doctest: +SKIP
        ...

        ```
    """
    response: httpx.Response | None = None

    # Retry loop: attempt 0 is initial try, 1..max_retries are retries
    for attempt in range(max_retries + 1):
        try:
            response = request_func(url=url, **kwargs)

            # Success case: HTTP status code 2xx or 3xx
            if response.status_code < 400:
                if attempt > 0:
                    logger.debug(f"{method} request to {url} succeeded on attempt {attempt + 1}")
                return response

            # Client/Server error: check if it's retryable
            handle_response(response, url, method, status_forcelist)

            # Retryable HTTP status - log and continue to retry
            logger.debug(
                f"{method} request to {url} failed with status {response.status_code} "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )

        except httpx.TimeoutException as exc:
            handle_timeout_exception(exc, url, method, attempt, max_retries)

        except httpx.RequestError as exc:
            handle_request_error(exc, url, method, attempt, max_retries)

        # Exponential backoff with jitter before next retry (skip on last attempt since we're about to fail)
        if attempt < max_retries:
            sleep_time = calculate_sleep_time(attempt, backoff_factor, jitter_factor, response)
            time.sleep(sleep_time)

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
