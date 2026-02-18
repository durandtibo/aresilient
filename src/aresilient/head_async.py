r"""Contains asynchronous HTTP HEAD request with automatic retry
logic."""

from __future__ import annotations

__all__ = ["head_async"]

from typing import TYPE_CHECKING, Any

from aresilient.core.config import (
    ClientConfig,
    DEFAULT_TIMEOUT,
)
from aresilient.core.http_logic import execute_http_method_async

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from aresilient.backoff import BackoffStrategy
    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo
    from aresilient.circuit_breaker import CircuitBreaker


async def head_async(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    config: ClientConfig | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int | None = None,
    backoff_factor: float | None = None,
    status_forcelist: tuple[int, ...] | None = None,
    jitter_factor: float | None = None,
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None = None,
    backoff_strategy: BackoffStrategy | None = None,
    max_total_time: float | None = None,
    max_wait_time: float | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    on_request: Callable[[RequestInfo], None] | None = None,
    on_retry: Callable[[RetryInfo], None] | None = None,
    on_success: Callable[[ResponseInfo], None] | None = None,
    on_failure: Callable[[FailureInfo], None] | None = None,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP HEAD request asynchronously with automatic retry
    logic for transient errors.

    This function performs an HTTP HEAD request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies a
    backoff retry strategy (exponential by default). The function validates
    the HTTP response and raises detailed errors for failures.

    HEAD requests retrieve only the headers without the response body, making
    them useful for checking resource existence, metadata, ETags, content
    length, and performing lightweight validation without downloading data.

    Args:
        url: The URL to send the HEAD request to.
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None. Must be > 0.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: backoff_factor * (2 ** attempt) seconds,
            where attempt is the 0-indexed retry number (0, 1, 2, ...).
            Must be >= 0. Ignored if backoff_strategy is provided.
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
        backoff_strategy: Optional custom backoff strategy (e.g., LinearBackoff,
            FibonacciBackoff, ConstantBackoff, or custom BackoffStrategy implementation).
            If provided, this strategy's calculate() method will be used instead of
            the default exponential backoff. The backoff_factor parameter is ignored
            when a custom strategy is provided.
        max_total_time: Optional maximum total time budget in seconds for all retry
            attempts. If the total elapsed time exceeds this value, the retry loop
            will stop and raise an error even if max_retries has not been reached.
            Must be > 0 if provided. Useful for enforcing strict SLA guarantees.
        max_wait_time: Optional maximum backoff delay cap in seconds. Individual
            backoff delays will not exceed this value, even with exponential backoff
            growth or Retry-After headers. Must be > 0 if provided. Useful for
            preventing very long waits in exponential backoff scenarios.
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
        **kwargs: Additional keyword arguments passed to ``httpx.AsyncClient.head()``.

    Returns:
        An httpx.Response object containing the server's HTTP response headers.
        The response body will be empty.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries, or if max_total_time is exceeded.
        ValueError: If max_retries, backoff_factor, or jitter_factor are negative,
            or if timeout, max_total_time, or max_wait_time are non-positive.

    Example:
        ```pycon
        >>> import asyncio
        >>> from aresilient import head_async
        >>> async def example():
        ...     response = await head_async("https://api.example.com/large-file.zip")
        ...     if response.status_code == 200:
        ...         print(f"Content-Length: {response.headers.get('Content-Length')}")
        ...     return response
        ...
        >>> asyncio.run(example())  # doctest: +SKIP

        ```
    """
    return await execute_http_method_async(
        url=url,
        method="HEAD",
        client=client,
        config=config,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        jitter_factor=jitter_factor,
        retry_if=retry_if,
        backoff_strategy=backoff_strategy,
        max_total_time=max_total_time,
        max_wait_time=max_wait_time,
        circuit_breaker=circuit_breaker,
        on_request=on_request,
        on_retry=on_retry,
        on_success=on_success,
        on_failure=on_failure,
        **kwargs,
    )
