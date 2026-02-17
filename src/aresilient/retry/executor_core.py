r"""Shared core logic for retry executors.

This module provides shared helper functions used by both synchronous and
asynchronous retry executors. These functions encapsulate common logic for
circuit breaker recording, error creation, and time budget validation.
"""

from __future__ import annotations

__all__ = [
    "check_time_budget_exceeded",
    "create_exception_error",
    "record_failure",
    "record_response_failure",
    "record_success",
]

import time
from typing import TYPE_CHECKING

import httpx

from aresilient.exceptions import HttpRequestError
from aresilient.utils.exceptions import raise_final_error

if TYPE_CHECKING:
    from aresilient.circuit_breaker import CircuitBreaker
    from aresilient.retry.config import RetryConfig
    from aresilient.retry.manager import CallbackManager


def record_success(circuit_breaker: CircuitBreaker | None) -> None:
    """Record success in circuit breaker if present.

    Args:
        circuit_breaker: Optional circuit breaker to record success.
    """
    if circuit_breaker is not None:
        circuit_breaker.record_success()


def record_failure(circuit_breaker: CircuitBreaker | None, error: Exception) -> None:
    """Record failure in circuit breaker if present.

    Args:
        circuit_breaker: Optional circuit breaker to record failure.
        error: The exception that occurred.
    """
    if circuit_breaker is not None:
        circuit_breaker.record_failure(error)


def record_response_failure(
    circuit_breaker: CircuitBreaker | None,
    response: httpx.Response,
    url: str,
    method: str,
) -> None:
    """Record response failure in circuit breaker if present.

    Args:
        circuit_breaker: Optional circuit breaker to record failure.
        response: The response that failed.
        url: The URL being requested.
        method: The HTTP method being used.
    """
    if circuit_breaker is None:
        return

    error = HttpRequestError(
        method=method,
        url=url,
        message=f"{method} request to {url} failed with status {response.status_code}",
        status_code=response.status_code,
        response=response,
    )
    circuit_breaker.record_failure(error)


def create_exception_error(
    exc: Exception,
    url: str,
    method: str,
    attempt: int,
) -> HttpRequestError:
    """Create HttpRequestError from exception.

    Args:
        exc: The exception that occurred.
        url: The URL being requested.
        method: The HTTP method being used.
        attempt: Current attempt number (0-indexed).

    Returns:
        HttpRequestError with appropriate message.
    """
    if isinstance(exc, httpx.TimeoutException):
        return HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} timed out ({attempt + 1} attempts)",
            cause=exc,
        )
    return HttpRequestError(
        method=method,
        url=url,
        message=f"{method} request to {url} failed after {attempt + 1} attempts: {exc}",
        cause=exc,
    )


def check_time_budget_exceeded(
    config: RetryConfig,
    callbacks: CallbackManager,
    start_time: float,
    url: str,
    method: str,
    attempt: int,
    response: httpx.Response | None,
) -> None:
    """Check if time budget is exceeded and raise error if so.

    Args:
        config: Retry configuration containing max_total_time.
        callbacks: Callback manager for invoking on_failure.
        start_time: When the request started.
        url: The URL being requested.
        method: The HTTP method being used.
        attempt: Current attempt number (0-indexed).
        response: The response if available.

    Raises:
        HttpRequestError: If time budget is exceeded.
    """
    if config.max_total_time is None:
        return

    elapsed_time = time.time() - start_time
    if elapsed_time < config.max_total_time:
        return

    # Time budget exceeded - raise error immediately
    if response is not None:
        raise_final_error(
            url=url,
            method=method,
            max_retries=config.max_retries,
            response=response,
            on_failure=callbacks.callbacks.on_failure,
            start_time=start_time,
        )

    # We have an exception but no response
    error = HttpRequestError(
        method=method,
        url=url,
        message=(
            f"{method} request to {url} failed after {attempt + 1} attempts "
            f"(max_total_time exceeded)"
        ),
    )
    callbacks.on_failure(
        url=url,
        method=method,
        attempt=attempt,
        max_retries=config.max_retries,
        error=error,
        status_code=None,
        start_time=start_time,
    )
    raise error
