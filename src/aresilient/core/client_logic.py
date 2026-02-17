r"""Shared client logic for both sync and async ResilientClient classes.

This module provides shared logic for the ResilientClient and
AsyncResilientClient context manager classes to reduce code duplication
while maintaining backward compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from aresilient.backoff import BackoffStrategy
    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo
    from aresilient.circuit_breaker import CircuitBreaker


def store_client_config(
    client_instance: Any,
    *,
    timeout: float | httpx.Timeout,
    max_retries: int,
    backoff_factor: float,
    status_forcelist: tuple[int, ...],
    jitter_factor: float,
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None,
    backoff_strategy: BackoffStrategy | None,
    max_total_time: float | None,
    max_wait_time: float | None,
    circuit_breaker: CircuitBreaker | None,
    on_request: Callable[[RequestInfo], None] | None,
    on_retry: Callable[[RetryInfo], None] | None,
    on_success: Callable[[ResponseInfo], None] | None,
    on_failure: Callable[[FailureInfo], None] | None,
) -> None:
    """Store configuration on client instance.

    This function stores all retry configuration parameters on the client
    instance as private attributes, following the naming convention _<param>.

    Args:
        client_instance: The client instance to store config on.
        timeout: Maximum seconds to wait for server responses.
        max_retries: Maximum number of retry attempts.
        backoff_factor: Factor for exponential backoff.
        status_forcelist: Tuple of HTTP status codes that should trigger retry.
        jitter_factor: Factor for adding random jitter to backoff delays.
        retry_if: Optional custom predicate function to determine retry.
        backoff_strategy: Optional custom backoff strategy instance.
        max_total_time: Optional maximum total time budget in seconds.
        max_wait_time: Optional maximum backoff delay cap in seconds.
        circuit_breaker: Optional circuit breaker instance.
        on_request: Optional callback called before each request attempt.
        on_retry: Optional callback called before each retry.
        on_success: Optional callback called when request succeeds.
        on_failure: Optional callback called when all retries exhausted.
    """
    client_instance._timeout = timeout
    client_instance._max_retries = max_retries
    client_instance._backoff_factor = backoff_factor
    client_instance._status_forcelist = status_forcelist
    client_instance._jitter_factor = jitter_factor
    client_instance._retry_if = retry_if
    client_instance._backoff_strategy = backoff_strategy
    client_instance._max_total_time = max_total_time
    client_instance._max_wait_time = max_wait_time
    client_instance._circuit_breaker = circuit_breaker
    client_instance._on_request = on_request
    client_instance._on_retry = on_retry
    client_instance._on_success = on_success
    client_instance._on_failure = on_failure


def merge_request_params(
    client_instance: Any,
    *,
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
) -> dict[str, Any]:
    """Merge request-specific parameters with client defaults.

    This function takes optional request-specific parameters and returns a
    dictionary with either the request parameter (if provided) or the client's
    default value.

    Args:
        client_instance: The client instance with default config.
        max_retries: Override client's max_retries for this request.
        backoff_factor: Override client's backoff_factor for this request.
        status_forcelist: Override client's status_forcelist for this request.
        jitter_factor: Override client's jitter_factor for this request.
        retry_if: Override client's retry_if for this request.
        backoff_strategy: Override client's backoff_strategy for this request.
        max_total_time: Override client's max_total_time for this request.
        max_wait_time: Override client's max_wait_time for this request.
        circuit_breaker: Override client's circuit_breaker for this request.
        on_request: Override client's on_request callback for this request.
        on_retry: Override client's on_retry callback for this request.
        on_success: Override client's on_success callback for this request.
        on_failure: Override client's on_failure callback for this request.

    Returns:
        Dictionary with merged parameters suitable for passing to retry functions.
    """
    return {
        "max_retries": max_retries if max_retries is not None else client_instance._max_retries,
        "backoff_factor": (
            backoff_factor if backoff_factor is not None else client_instance._backoff_factor
        ),
        "status_forcelist": (
            status_forcelist if status_forcelist is not None else client_instance._status_forcelist
        ),
        "jitter_factor": (
            jitter_factor if jitter_factor is not None else client_instance._jitter_factor
        ),
        "retry_if": retry_if if retry_if is not None else client_instance._retry_if,
        "backoff_strategy": (
            backoff_strategy if backoff_strategy is not None else client_instance._backoff_strategy
        ),
        "max_total_time": (
            max_total_time if max_total_time is not None else client_instance._max_total_time
        ),
        "max_wait_time": (
            max_wait_time if max_wait_time is not None else client_instance._max_wait_time
        ),
        "circuit_breaker": (
            circuit_breaker if circuit_breaker is not None else client_instance._circuit_breaker
        ),
        "on_request": on_request if on_request is not None else client_instance._on_request,
        "on_retry": on_retry if on_retry is not None else client_instance._on_retry,
        "on_success": on_success if on_success is not None else client_instance._on_success,
        "on_failure": on_failure if on_failure is not None else client_instance._on_failure,
    }
