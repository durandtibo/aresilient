r"""Contains utility functions for synchronous HTTP requests with
automatic retry logic."""

from __future__ import annotations

__all__ = ["request_with_automatic_retry"]

import logging
import time
from typing import TYPE_CHECKING, Any

from aresilient.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    RETRY_STATUS_CODES,
)
from aresilient.utils import (
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
    from aresilient.backoff import BackoffStrategy
    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo
    from collections.abc import Callable

import httpx

from aresilient.backoff import calculate_sleep_time
from aresilient.circuit_breaker import CircuitBreaker

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
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: backoff_factor * (2 ** attempt) seconds,
            where attempt is 0-indexed (0, 1, 2, ...). Ignored if backoff_strategy
            is provided.
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
        circuit_breaker: Optional CircuitBreaker instance to use for preventing
            cascading failures. When provided, the circuit breaker will track
            failures and stop making requests if the failure threshold is reached,
            transitioning to an OPEN state where requests fail fast. After a
            recovery timeout, it will transition to HALF_OPEN to test if the
            service has recovered.
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
            or fails after exhausting all retries, or if max_total_time is exceeded.

    Example:
        ```pycon
        >>> import httpx
        >>> from aresilient import request_with_automatic_retry
        >>> from aresilient import LinearBackoff
        >>> def log_retry(info):
        ...     print(f"Retry {info.attempt}/{info.max_retries + 1}")
        ...
        >>> with httpx.Client() as client:
        ...     response = request_with_automatic_retry(
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
    response: httpx.Response | None = None
    start_time = time.time()
    last_error: Exception | None = None
    last_status_code: int | None = None

    # Retry loop: attempt 0 is initial try, 1..max_retries are retries
    for attempt in range(max_retries + 1):
        try:
            # Check circuit breaker before making request
            if circuit_breaker is not None:
                circuit_breaker.check()

            # Call on_request callback before each attempt
            invoke_on_request(
                on_request,
                url=url,
                method=method,
                attempt=attempt,
                max_retries=max_retries,
            )

            response = request_func(url=url, **kwargs)

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

                    # Record success in circuit breaker (if not already recorded by call())
                    if circuit_breaker is not None:
                        circuit_breaker.record_success()

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
                # This is a retry case, record as failure in circuit breaker
                if circuit_breaker is not None:
                    from aresilient.exceptions import HttpRequestError

                    circuit_breaker.record_failure(
                        HttpRequestError(
                            method=method,
                            url=url,
                            message=f"Retry predicate returned True for status {response.status_code}",
                            status_code=response.status_code,
                            response=response,
                        )
                    )

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
            # Record failure in circuit breaker for retryable status codes
            if circuit_breaker is not None:
                from aresilient.exceptions import HttpRequestError

                circuit_breaker.record_failure(
                    HttpRequestError(
                        method=method,
                        url=url,
                        message=f"Request failed with retryable status {response.status_code}",
                        status_code=response.status_code,
                        response=response,
                    )
                )

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
            # Check if max_total_time would be exceeded before sleeping
            if max_total_time is not None:
                elapsed_time = time.time() - start_time
                if elapsed_time >= max_total_time:
                    # Time budget exceeded - raise error without retrying
                    logger.debug(
                        f"{method} request to {url} exceeded max_total_time "
                        f"({elapsed_time:.2f}s >= {max_total_time:.2f}s) "
                        f"after {attempt + 1} attempts"
                    )
                    raise_final_error(
                        url=url,
                        method=method,
                        max_retries=max_retries,
                        response=response,
                        on_failure=on_failure,
                        start_time=start_time,
                    )

            sleep_time = calculate_sleep_time(
                attempt=attempt,
                backoff_factor=backoff_factor,
                jitter_factor=jitter_factor,
                response=response,
                backoff_strategy=backoff_strategy,
                max_wait_time=max_wait_time,
            )

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

            time.sleep(sleep_time)

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
