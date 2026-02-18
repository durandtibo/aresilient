r"""Shared HTTP method logic for sync and async operations.

This module contains shared HTTP method logic that is used by both
synchronous and asynchronous HTTP request implementations.
"""

from __future__ import annotations

__all__ = ["execute_http_method", "execute_http_method_async"]

from typing import TYPE_CHECKING, Any

import httpx

from aresilient.core.config import (
    ClientConfig,
    DEFAULT_TIMEOUT,
)
from aresilient.core.validation import validate_timeout
from aresilient.request import request
from aresilient.request_async import request_async

if TYPE_CHECKING:
    from collections.abc import Callable

    from aresilient.backoff import BackoffStrategy
    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo
    from aresilient.circuit_breaker import CircuitBreaker


def execute_http_method(
    url: str,
    method: str,
    *,
    client: httpx.Client | None = None,
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
    """Execute an HTTP method with automatic retry logic (synchronous).

    This is the core shared logic for all synchronous HTTP methods.
    It handles client creation, parameter validation, and cleanup.

    Args:
        url: The URL to send the request to.
        method: The HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS).
        client: An optional httpx.Client object to use for making requests.
            If None, a new client will be created and closed after use.
        config: An optional ClientConfig object with retry configuration.
            If provided, its values are used as defaults. Individual parameters
            (max_retries, backoff_factor, etc.) override the config when specified.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None. Must be > 0.
        max_retries: Maximum number of retry attempts for failed requests.
            Overrides config.max_retries if provided. Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries.
            Overrides config.backoff_factor if provided. Must be >= 0.
            Ignored if backoff_strategy is provided.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
            Overrides config.status_forcelist if provided.
        jitter_factor: Factor for adding random jitter to backoff delays.
            Overrides config.jitter_factor if provided. Must be >= 0.
        retry_if: Optional custom predicate function to determine whether to retry.
            Overrides config.retry_if if provided.
        backoff_strategy: Optional custom backoff strategy.
            Overrides config.backoff_strategy if provided.
        max_total_time: Optional maximum total time budget in seconds.
            Overrides config.max_total_time if provided. Must be > 0 if provided.
        max_wait_time: Optional maximum backoff delay cap in seconds.
            Overrides config.max_wait_time if provided. Must be > 0 if provided.
        circuit_breaker: Optional circuit breaker instance.
            Overrides config.circuit_breaker if provided.
        on_request: Optional callback called before each request attempt.
            Overrides config.on_request if provided.
        on_retry: Optional callback called before each retry.
            Overrides config.on_retry if provided.
        on_success: Optional callback called when request succeeds.
            Overrides config.on_success if provided.
        on_failure: Optional callback called when all retries are exhausted.
            Overrides config.on_failure if provided.
        **kwargs: Additional keyword arguments passed to the client method.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request fails after exhausting all retries.
        ValueError: If parameters are invalid.
    """
    # Validate timeout (not part of ClientConfig)
    validate_timeout(timeout)

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

    # Client management
    owns_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        # Get the appropriate request method from the client
        request_func = getattr(client, method.lower())
        return request(
            url=url,
            method=method,
            request_func=request_func,
            **effective_config.to_dict(),
            **kwargs,
        )
    finally:
        if owns_client:
            client.close()


async def execute_http_method_async(
    url: str,
    method: str,
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
    """Execute an HTTP method with automatic retry logic (asynchronous).

    This is the core shared logic for all asynchronous HTTP methods.
    It handles client creation, parameter validation, and cleanup.

    Args:
        url: The URL to send the request to.
        method: The HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS).
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        config: An optional ClientConfig object with retry configuration.
            If provided, its values are used as defaults. Individual parameters
            (max_retries, backoff_factor, etc.) override the config when specified.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None. Must be > 0.
        max_retries: Maximum number of retry attempts for failed requests.
            Overrides config.max_retries if provided. Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries.
            Overrides config.backoff_factor if provided. Must be >= 0.
            Ignored if backoff_strategy is provided.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
            Overrides config.status_forcelist if provided.
        jitter_factor: Factor for adding random jitter to backoff delays.
            Overrides config.jitter_factor if provided. Must be >= 0.
        retry_if: Optional custom predicate function to determine whether to retry.
            Overrides config.retry_if if provided.
        backoff_strategy: Optional custom backoff strategy.
            Overrides config.backoff_strategy if provided.
        max_total_time: Optional maximum total time budget in seconds.
            Overrides config.max_total_time if provided. Must be > 0 if provided.
        max_wait_time: Optional maximum backoff delay cap in seconds.
            Overrides config.max_wait_time if provided. Must be > 0 if provided.
        circuit_breaker: Optional circuit breaker instance.
            Overrides config.circuit_breaker if provided.
        on_request: Optional callback called before each request attempt.
            Overrides config.on_request if provided.
        on_retry: Optional callback called before each retry.
            Overrides config.on_retry if provided.
        on_success: Optional callback called when request succeeds.
            Overrides config.on_success if provided.
        on_failure: Optional callback called when all retries are exhausted.
            Overrides config.on_failure if provided.
        **kwargs: Additional keyword arguments passed to the client method.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request fails after exhausting all retries.
        ValueError: If parameters are invalid.
    """
    # Validate timeout (not part of ClientConfig)
    validate_timeout(timeout)

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

    # Client management
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    try:
        # Get the appropriate request method from the client
        request_func = getattr(client, method.lower())
        return await request_async(
            url=url,
            method=method,
            request_func=request_func,
            **effective_config.to_dict(),
            **kwargs,
        )
    finally:
        if owns_client:
            await client.aclose()
