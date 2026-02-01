r"""Contains utility functions for asynchronous HTTP requests with
automatic retry logic."""

from __future__ import annotations

__all__ = ["request_with_automatic_retry_async"]

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from aresilient.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    RETRY_STATUS_CODES,
)
from aresilient.utils import (
    calculate_sleep_time,
    handle_exception_with_callback,
    handle_exception_with_retry_if,
    handle_request_error,
    handle_response,
    handle_response_with_retry_if,
    handle_timeout_exception,
    invoke_on_request,
    invoke_on_retry,
    invoke_on_success,
    raise_final_error,
)

if TYPE_CHECKING:
    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo
    from collections.abc import Awaitable, Callable

import httpx

logger: logging.Logger = logging.getLogger(__name__)


async def request_with_automatic_retry_async(
    url: str,
    method: str,
    request_func: Callable[..., Awaitable[httpx.Response]],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    jitter_factor: float = 0.0,
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None = None,
    on_request: Callable[[RequestInfo], None] | None = None,
    on_retry: Callable[[RetryInfo], None] | None = None,
    on_success: Callable[[ResponseInfo], None] | None = None,
    on_failure: Callable[[FailureInfo], None] | None = None,
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
            time is calculated as: backoff_factor * (2 ** attempt) seconds,
            where attempt is 0-indexed (0, 1, 2, ...).
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        jitter_factor: Factor for adding random jitter to backoff delays. The jitter
            is calculated as: random.uniform(0, jitter_factor) * base_sleep_time,
            and this jitter is ADDED to the base sleep time. Set to 0 to disable
            jitter (default). Recommended value is 0.1 for 10% jitter to prevent
            thundering herd issues.
        retry_if: Optional custom predicate function to determine whether to retry
            based on the response or exception. Called with (response, exception)
            where at least one will be non-None. Should return True to retry, False
            to not retry. If provided, this takes precedence over status_forcelist
            for determining retry behavior.
        on_request: Optional callback called before each request attempt.
            Receives RequestInfo with url, method, attempt, max_retries.
        on_retry: Optional callback called before each retry (after backoff).
            Receives RetryInfo with url, method, attempt, max_retries, wait_time,
            error, status_code.
        on_success: Optional callback called when request succeeds.
            Receives ResponseInfo with url, method, attempt, max_retries, response,
            total_time.
        on_failure: Optional callback called when all retries are exhausted.
            Receives FailureInfo with url, method, attempt, max_retries, error,
            status_code, total_time.
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
        >>> from aresilient import request_with_automatic_retry_async
        >>> def log_retry(info):
        ...     print(f"Retry {info.attempt}/{info.max_retries + 1}")
        ...
        >>> async def example():
        ...     async with httpx.AsyncClient() as client:
        ...         response = await request_with_automatic_retry_async(
        ...             url="https://api.example.com/data",
        ...             method="GET",
        ...             request_func=client.get,
        ...             max_retries=5,
        ...             backoff_factor=1.0,
        ...             jitter_factor=0.1,  # Add 10% jitter
        ...             on_retry=log_retry,
        ...         )
        ...         return response.status_code
        ...
        >>> asyncio.run(example())  # doctest: +SKIP

        ```
    """
    response: httpx.Response | None = None
    start_time = time.time()
    last_error: Exception | None = None
    last_status_code: int | None = None

    # Retry loop: attempt 0 is initial try, 1..max_retries are retries
    for attempt in range(max_retries + 1):
        try:
            # Call on_request callback before each attempt
            invoke_on_request(
                on_request,
                url=url,
                method=method,
                attempt=attempt,
                max_retries=max_retries,
            )

            response = await request_func(url=url, **kwargs)

            # Success case: HTTP status code 2xx or 3xx
            if response.status_code < 400:
                # Check custom retry predicate even for successful responses
                should_retry_success = False
                if retry_if is not None:
                    should_retry_success = handle_response_with_retry_if(
                        response,
                        retry_if=retry_if,
                        url=url,
                        method=method,
                    )

                if not should_retry_success:
                    # True success - no retry needed
                    if attempt > 0:
                        logger.debug(
                            f"{method} request to {url} succeeded on attempt {attempt + 1}"
                        )

                    # Call on_success callback
                    invoke_on_success(
                        on_success,
                        url=url,
                        method=method,
                        attempt=attempt,
                        max_retries=max_retries,
                        response=response,
                        start_time=start_time,
                    )

                    return response

                # retry_if returned True for success - mark for retry
                logger.debug(
                    f"{method} request to {url} has status {response.status_code} but "
                    f"retry_if predicate returned True "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                last_status_code = response.status_code

            # Client/Server error: check if it's retryable
            # Use custom retry predicate if provided, otherwise use status_forcelist
            if retry_if is not None:
                handle_response_with_retry_if(
                    response,
                    retry_if=retry_if,
                    url=url,
                    method=method,
                )
                # If we get here, retry_if returned True for error response
            else:
                handle_response(response, url, method, status_forcelist)

            # Retryable HTTP status - log and continue to retry
            logger.debug(
                f"{method} request to {url} failed with status {response.status_code} "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )
            last_status_code = response.status_code

        except (httpx.TimeoutException, httpx.RequestError) as exc:
            last_error = exc
            # Check custom retry predicate if provided
            if retry_if is not None:
                handle_exception_with_retry_if(
                    exc,
                    retry_if=retry_if,
                    url=url,
                    method=method,
                    attempt=attempt,
                    max_retries=max_retries,
                    on_failure=on_failure,
                    start_time=start_time,
                )
            else:
                # Determine which handler to use based on exception type
                handler_func = (
                    handle_timeout_exception
                    if isinstance(exc, httpx.TimeoutException)
                    else handle_request_error
                )
                handle_exception_with_callback(
                    exc,
                    url=url,
                    method=method,
                    attempt=attempt,
                    max_retries=max_retries,
                    handler_func=handler_func,
                    on_failure=on_failure,
                    start_time=start_time,
                )

        # Exponential backoff with jitter before next retry
        # (skip on last attempt since we're about to fail)
        if attempt < max_retries:
            sleep_time = calculate_sleep_time(attempt, backoff_factor, jitter_factor, response)

            # Call on_retry callback before sleeping
            invoke_on_retry(
                on_retry,
                url=url,
                method=method,
                attempt=attempt,
                max_retries=max_retries,
                sleep_time=sleep_time,
                last_error=last_error,
                last_status_code=last_status_code,
            )

            await asyncio.sleep(sleep_time)

    # All retries exhausted with retryable status code - raise final error
    # Note: response cannot be None here because if all attempts raised exceptions,
    # they would have been caught by the exception handlers above and raised before
    # reaching this point.
    raise_final_error(
        url=url,
        method=method,
        max_retries=max_retries,
        response=response,
        on_failure=on_failure,
        start_time=start_time,
    )
