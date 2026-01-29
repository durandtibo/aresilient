r"""Contain utility functions for asynchronous HTTP requests with
automatic retry logic."""

from __future__ import annotations

__all__ = ["request_with_automatic_retry_async"]

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    RETRY_STATUS_CODES,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Awaitable

import httpx

from aresnet.exception import HttpRequestError

logger: logging.Logger = logging.getLogger(__name__)


async def request_with_automatic_retry_async(
    url: str,
    method: str,
    request_func: Callable[..., Awaitable[httpx.Response]],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
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

    Exponential backoff wait time: backoff_factor * (2 ** attempt)
    where attempt is 0-indexed (0, 1, 2, ...).

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
        **kwargs: Additional keyword arguments passed to the request function.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
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
            # Non-retryable HTTP error (e.g., 404, 401, 403)
            if response.status_code not in status_forcelist:
                logger.debug(
                    f"{method} request to {url} failed with non-retryable status {response.status_code}"
                )
                # Let httpx raise the appropriate HTTPStatusError
                response.raise_for_status()

            # Retryable HTTP status - log and continue to retry
            logger.debug(
                f"{method} request to {url} failed with status {response.status_code} "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )

        except httpx.TimeoutException as exc:
            # Request timed out - retry if attempts remain
            if attempt == max_retries:
                raise HttpRequestError(
                    method=method,
                    url=url,
                    message=f"{method} request to {url} timed out ({max_retries + 1} attempts)",
                    cause=exc,
                ) from exc

        except httpx.RequestError as exc:
            # Network error (connection failed, DNS failure, etc.) - retry if attempts remain
            if attempt == max_retries:
                raise HttpRequestError(
                    method=method,
                    url=url,
                    message=f"{method} request to {url} failed after {max_retries + 1} attempts: {exc}",
                    cause=exc,
                ) from exc

        # Exponential backoff before next retry (skip on last attempt since we're about to fail)
        if attempt < max_retries:
            sleep_time = backoff_factor * (2**attempt)
            logger.debug(f"Waiting {sleep_time:.2f}s before retry")
            await asyncio.sleep(sleep_time)

    # All retries exhausted with retryable status code - raise final error
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
