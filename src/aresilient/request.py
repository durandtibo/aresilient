r"""Contains utility functions for synchronous HTTP requests with
automatic retry logic."""

from __future__ import annotations

__all__ = ["request"]

from typing import TYPE_CHECKING, Any

from aresilient.core.config import ClientConfig
from aresilient.retry import (
    CallbackConfig,
    RetryConfig,
    RetryExecutor,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from aresilient.backoff import BackoffStrategy
    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo
    from aresilient.circuit_breaker import CircuitBreaker


def request(
    url: str,
    method: str,
    request_func: Callable[..., httpx.Response],
    *,
    config: ClientConfig | None = None,
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
    """Perform an HTTP request with automatic retry logic.

    This function implements a retry mechanism with exponential backoff for
    handling transient HTTP errors. It attempts the request up to max_retries + 1
    times, waiting progressively longer between each retry.

    The retry logic handles three types of failures:
    1. Retryable HTTP status codes (e.g., 429, 500, 502, 503, 504)
    2. Timeout exceptions (httpx.TimeoutException)
    3. General network errors (httpx.RequestError)

    Backoff Strategy:
    - Default: Exponential backoff: backoff_factor * (2 ** attempt)
    - Custom: Use backoff_strategy parameter for alternative strategies
      (Linear, Fibonacci, Constant, or custom implementations)
    - Jitter: Optional randomization added to prevent thundering herd
    - Retry-After header: If present in the response (429/503), the server's
      suggested wait time is used instead of backoff calculation

    Args:
        url: The URL to send the request to.
        method: The HTTP method name (e.g., "GET", "POST") for logging.
        request_func: The function to call to make the request (e.g.,
            client.get, client.post).
        config: An optional ClientConfig object with retry configuration.
            If provided, its values are used as defaults. Individual parameters
            override the config when specified.
        max_retries: Maximum number of retry attempts for failed requests.
            Overrides config.max_retries if provided. Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: backoff_factor * (2 ** attempt) seconds,
            where attempt is 0-indexed (0, 1, 2, ...). Overrides
            config.backoff_factor if provided. Ignored if backoff_strategy is
            provided.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
            Overrides config.status_forcelist if provided.
        jitter_factor: Factor for adding random jitter to backoff delays. The jitter
            is calculated as: random.uniform(0, jitter_factor) * base_sleep_time,
            and this jitter is ADDED to the base sleep time. Set to 0 to disable
            jitter (default). Recommended value is 0.1 for 10% jitter to prevent
            thundering herd issues. Overrides config.jitter_factor if provided.
        retry_if: Optional custom predicate function to determine whether to retry
            based on the response or exception. Called with (response, exception)
            where at least one will be non-None. Should return True to retry, False
            to not retry. If provided, this takes precedence over status_forcelist
            for determining retry behavior. Overrides config.retry_if if provided.
        backoff_strategy: Optional custom backoff strategy (e.g., LinearBackoff,
            FibonacciBackoff, ConstantBackoff, or custom BackoffStrategy implementation).
            If provided, this strategy's calculate() method will be used instead of
            the default exponential backoff. The backoff_factor parameter is ignored
            when a custom strategy is provided. Overrides config.backoff_strategy if
            provided.
        max_total_time: Optional maximum total time budget in seconds for all retry
            attempts. If the total elapsed time exceeds this value, the retry loop
            will stop and raise an error even if max_retries has not been reached.
            Must be > 0 if provided. Overrides config.max_total_time if provided.
        max_wait_time: Optional maximum backoff delay cap in seconds. Individual
            backoff delays will not exceed this value, even with exponential backoff
            growth or Retry-After headers. Must be > 0 if provided. Overrides
            config.max_wait_time if provided.
        circuit_breaker: Optional CircuitBreaker instance to use for preventing
            cascading failures. When provided, the circuit breaker will track
            failures and stop making requests if the failure threshold is reached,
            transitioning to an OPEN state where requests fail fast. After a
            recovery timeout, it will transition to HALF_OPEN to test if the
            service has recovered. Overrides config.circuit_breaker if provided.
        on_request: Optional callback called before each request attempt.
            Receives RequestInfo with url, method, attempt, max_retries.
            Overrides config.on_request if provided.
        on_retry: Optional callback called before each retry (after backoff).
            Receives RetryInfo with url, method, attempt, max_retries, wait_time,
            error, status_code. Overrides config.on_retry if provided.
        on_success: Optional callback called when request succeeds.
            Receives ResponseInfo with url, method, attempt, max_retries, response,
            total_time. Overrides config.on_success if provided.
        on_failure: Optional callback called when all retries are exhausted.
            Receives FailureInfo with url, method, attempt, max_retries, error,
            status_code, total_time. Overrides config.on_failure if provided.
        **kwargs: Additional keyword arguments passed to the request function.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries, or if max_total_time is exceeded.

    Example:
        ```pycon
        >>> import httpx
        >>> from aresilient import request
        >>> from aresilient.backoff import LinearBackoff
        >>> def log_retry(info):
        ...     print(f"Retry {info.attempt}/{info.max_retries + 1}")
        ...
        >>> with httpx.Client() as client:
        ...     response = request(
        ...         url="https://api.example.com/data",
        ...         method="GET",
        ...         request_func=client.get,
        ...         max_retries=5,
        ...         backoff_strategy=LinearBackoff(base_delay=1.0),
        ...         jitter_factor=0.1,  # Add 10% jitter
        ...         max_total_time=30.0,  # Stop after 30s total
        ...         max_wait_time=5.0,  # Cap backoff at 5s max
        ...         on_retry=log_retry,
        ...     )  # doctest: +SKIP
        ...

        ```
    """
    # Build effective config: use provided config as base, then apply overrides
    effective_config = (config if config is not None else ClientConfig()).merge(
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
    )

    # Create retry configuration
    retry_config = RetryConfig(
        max_retries=effective_config.max_retries,
        backoff_factor=effective_config.backoff_factor,
        status_forcelist=effective_config.status_forcelist,
        jitter_factor=effective_config.jitter_factor,
        retry_if=effective_config.retry_if,
        backoff_strategy=effective_config.backoff_strategy,
        max_total_time=effective_config.max_total_time,
        max_wait_time=effective_config.max_wait_time,
    )

    # Create callback configuration
    callback_config = CallbackConfig(
        on_request=effective_config.on_request,
        on_retry=effective_config.on_retry,
        on_success=effective_config.on_success,
        on_failure=effective_config.on_failure,
    )

    # Create executor and execute request
    executor = RetryExecutor(retry_config, callback_config, effective_config.circuit_breaker)
    return executor.execute(url, method, request_func, **kwargs)
