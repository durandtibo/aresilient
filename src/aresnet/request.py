r"""Contain utility functions for synchronous HTTP requests with
automatic retry logic."""

from __future__ import annotations

__all__ = ["request_with_automatic_retry"]

import logging
import random
import time
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    RETRY_STATUS_CODES,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

import httpx

from aresnet.exceptions import HttpRequestError

logger: logging.Logger = logging.getLogger(__name__)


def _parse_retry_after(retry_after_header: str | None) -> float | None:
    """Parse the Retry-After header value.

    The Retry-After header can be either:
    1. A number of seconds (integer)
    2. An HTTP-date (RFC 5322 format)

    Args:
        retry_after_header: The value of the Retry-After header.

    Returns:
        The number of seconds to wait, or None if the header is invalid.

    Example:
        ```pycon
        >>> _parse_retry_after("120")
        120.0
        >>> _parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT")  # doctest: +SKIP
        ...

        ```
    """
    if retry_after_header is None:
        return None

    # Try parsing as an integer (seconds)
    try:
        return float(retry_after_header)
    except ValueError:
        pass

    # Try parsing as HTTP-date
    try:
        retry_date: datetime = parsedate_to_datetime(retry_after_header)
        now = parsedate_to_datetime(time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()))
        delta_seconds = (retry_date - now).total_seconds()
        # Ensure we don't return negative values
        return max(0.0, delta_seconds)
    except (ValueError, TypeError, OverflowError):
        logger.debug(f"Failed to parse Retry-After header: {retry_after_header}")
        return None


def request_with_automatic_retry(
    url: str,
    method: str,
    request_func: Callable[..., httpx.Response],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
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
    - Jitter: Up to 10% randomization added to prevent thundering herd
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
            where attempt is 0-indexed (0, 1, 2, ...). Jitter of up to 10% is
            added to this base value to prevent synchronized retries across
            multiple clients.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
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

            # Retryable HTTP status - log and continue to retry
            logger.debug(
                f"{method} request to {url} failed with status {response.status_code} "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )

        except httpx.TimeoutException as exc:
            # Request timed out - retry if attempts remain
            logger.debug(
                f"{method} request to {url} timed out on attempt {attempt + 1}/{max_retries + 1}"
            )
            if attempt == max_retries:
                raise HttpRequestError(
                    method=method,
                    url=url,
                    message=f"{method} request to {url} timed out ({max_retries + 1} attempts)",
                    cause=exc,
                ) from exc

        except httpx.RequestError as exc:
            # Network error (connection failed, DNS failure, etc.) - retry if attempts remain
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

        # Exponential backoff with jitter before next retry (skip on last attempt since we're about to fail)
        if attempt < max_retries:
            # Check for Retry-After header in the response (if available)
            retry_after_sleep: float | None = None
            if response is not None and hasattr(response, "headers"):
                retry_after_header = response.headers.get("Retry-After")
                retry_after_sleep = _parse_retry_after(retry_after_header)

            # Use Retry-After if available, otherwise use exponential backoff
            if retry_after_sleep is not None:
                sleep_time = retry_after_sleep
                logger.debug(f"Using Retry-After header value: {sleep_time:.2f}s")
            else:
                sleep_time = backoff_factor * (2**attempt)

            # Add jitter to prevent thundering herd problem
            # Jitter is up to 10% of the sleep time
            jitter = random.uniform(0, 0.1) * sleep_time
            total_sleep_time = sleep_time + jitter
            logger.debug(f"Waiting {total_sleep_time:.2f}s before retry (base={sleep_time:.2f}s, jitter={jitter:.2f}s)")
            time.sleep(total_sleep_time)

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
