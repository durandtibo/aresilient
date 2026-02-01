r"""Contains asynchronous HTTP POST request with automatic retry
logic."""

from __future__ import annotations

__all__ = ["post_with_automatic_retry_async"]

from typing import TYPE_CHECKING, Any

import httpx

from aresilient.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresilient.request_async import request_with_automatic_retry_async
from aresilient.utils import validate_retry_params

if TYPE_CHECKING:
    from collections.abc import Callable

    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo


async def post_with_automatic_retry_async(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
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
    r"""Send an HTTP POST request asynchronously with automatic retry
    logic for transient errors.

    This function performs an HTTP POST request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the POST request to.
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None. Must be > 0.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: backoff_factor * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        jitter_factor: Factor for adding random jitter to backoff delays. The jitter
            is calculated as: random.uniform(0, jitter_factor) * base_sleep_time,
            and this jitter is ADDED to the base sleep time. Set to 0 to disable
            jitter (default). Recommended value is 0.1 for 10% jitter to prevent
            thundering herd issues. Must be >= 0.
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
        **kwargs: Additional keyword arguments passed to ``httpx.AsyncClient.post()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries, backoff_factor, or jitter_factor are negative,
            or if timeout is non-positive.

    Example:
        ```pycon
        >>> import asyncio
        >>> from aresilient import post_with_automatic_retry_async
        >>> async def example():
        ...     response = await post_with_automatic_retry_async(
        ...         "https://api.example.com/data", json={"key": "value"}
        ...     )
        ...     return response.json()
        ...
        >>> asyncio.run(example())  # doctest: +SKIP

        ```
    """
    # Input validation
    validate_retry_params(
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        jitter_factor=jitter_factor,
        timeout=timeout,
    )

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    try:
        return await request_with_automatic_retry_async(
            url=url,
            method="POST",
            request_func=client.post,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            jitter_factor=jitter_factor,
            retry_if=retry_if,
            on_request=on_request,
            on_retry=on_retry,
            on_success=on_success,
            on_failure=on_failure,
            **kwargs,
        )
    finally:
        if owns_client:
            await client.aclose()
