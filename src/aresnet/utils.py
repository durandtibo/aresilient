r"""Contain utility functions for HTTP requests."""

from __future__ import annotations

__all__ = [
    "calculate_sleep_time",
    "handle_request_error",
    "handle_response",
    "handle_timeout_exception",
    "parse_retry_after",
    "validate_retry_params",
]

import logging
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING

from aresnet.exceptions import HttpRequestError

if TYPE_CHECKING:
    import httpx

logger: logging.Logger = logging.getLogger(__name__)


def validate_retry_params(
    max_retries: int, backoff_factor: float, jitter_factor: float = 0.0
) -> None:
    """Validate retry parameters.

    Args:
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries.
            Must be >= 0.
        jitter_factor: Factor for adding random jitter to backoff delays.
            Must be >= 0. Recommended value is 0.1 for 10% jitter.

    Raises:
        ValueError: If max_retries, backoff_factor, or jitter_factor are negative.

    Example:
        ```pycon
        >>> from aresnet.utils import validate_retry_params
        >>> validate_retry_params(max_retries=3, backoff_factor=0.5)
        >>> validate_retry_params(max_retries=3, backoff_factor=0.5, jitter_factor=0.1)
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


def parse_retry_after(retry_after_header: str | None) -> float | None:
    """Parse the Retry-After header value from an HTTP response.

    The Retry-After header can be specified in two formats:
    1. An integer representing the number of seconds to wait
    2. An HTTP-date in RFC 5322 format

    Args:
        retry_after_header: The value of the Retry-After header, or None
            if the header is not present.

    Returns:
        The number of seconds to wait before retrying, or None if the
        header is absent or cannot be parsed.

    Example:
        ```pycon
        >>> from aresnet.utils import parse_retry_after
        >>> parse_retry_after("120")
        120.0
        >>> parse_retry_after("0")
        0.0
        >>> parse_retry_after(None)
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
    if response is not None:
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


def handle_request_error(
    exc: Exception,
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
