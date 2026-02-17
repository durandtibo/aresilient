r"""Contains synchronous HTTP PUT request with automatic retry logic."""

from __future__ import annotations

__all__ = ["put_with_automatic_retry"]

from typing import TYPE_CHECKING, Any

from aresilient.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresilient.core.http_logic import execute_http_method

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from aresilient.backoff import BackoffStrategy
    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo


def put_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    jitter_factor: float = 0.0,
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None = None,
    backoff_strategy: BackoffStrategy | None = None,
    max_total_time: float | None = None,
    max_wait_time: float | None = None,
    on_request: Callable[[RequestInfo], None] | None = None,
    on_retry: Callable[[RetryInfo], None] | None = None,
    on_success: Callable[[ResponseInfo], None] | None = None,
    on_failure: Callable[[FailureInfo], None] | None = None,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP PUT request with automatic retry logic for transient
    errors.

    This function performs an HTTP PUT request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies a
    backoff retry strategy (exponential by default). The function validates
    the HTTP response and raises detailed errors for failures.

    Args:
        url: The URL to send the PUT request to.
        client: An optional httpx.Client object to use for making requests.
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
        **kwargs: Additional keyword arguments passed to ``httpx.Client.put()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries, or if max_total_time is exceeded.
        ValueError: If max_retries, backoff_factor, or jitter_factor are negative,
            or if timeout, max_total_time, or max_wait_time are non-positive.

    Example:
        ```pycon
        >>> from aresilient import put_with_automatic_retry
        >>> response = put_with_automatic_retry(
        ...     "https://api.example.com/resource/123", json={"name": "updated"}
        ... )  # doctest: +SKIP

        ```
    """
    return execute_http_method(
        url=url,
        method="PUT",
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        jitter_factor=jitter_factor,
        retry_if=retry_if,
        backoff_strategy=backoff_strategy,
        max_total_time=max_total_time,
        max_wait_time=max_wait_time,
        on_request=on_request,
        on_retry=on_retry,
        on_success=on_success,
        on_failure=on_failure,
        **kwargs,
    )
