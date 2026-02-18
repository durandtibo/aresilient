r"""Shared HTTP method logic for sync and async operations.

This module contains shared HTTP method logic that is used by both
synchronous and asynchronous HTTP request implementations.
"""

from __future__ import annotations

__all__ = ["execute_http_method", "execute_http_method_async"]

from typing import TYPE_CHECKING, Any

import httpx

from aresilient.core.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresilient.core.validation import validate_retry_params
from aresilient.request import request
from aresilient.request_async import request_async

if TYPE_CHECKING:
    from collections.abc import Callable

    from aresilient.backoff import BackoffStrategy
    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo


def execute_http_method(
    url: str,
    method: str,
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
    """Execute an HTTP method with automatic retry logic (synchronous).

    This is the core shared logic for all synchronous HTTP methods.
    It handles client creation, parameter validation, and cleanup.

    Args:
        url: The URL to send the request to.
        method: The HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS).
        client: An optional httpx.Client object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None. Must be > 0.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries.
            Must be >= 0. Ignored if backoff_strategy is provided.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        jitter_factor: Factor for adding random jitter to backoff delays.
            Must be >= 0.
        retry_if: Optional custom predicate function to determine whether to retry.
        backoff_strategy: Optional custom backoff strategy.
        max_total_time: Optional maximum total time budget in seconds.
            Must be > 0 if provided.
        max_wait_time: Optional maximum backoff delay cap in seconds.
            Must be > 0 if provided.
        on_request: Optional callback called before each request attempt.
        on_retry: Optional callback called before each retry.
        on_success: Optional callback called when request succeeds.
        on_failure: Optional callback called when all retries are exhausted.
        **kwargs: Additional keyword arguments passed to the client method.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request fails after exhausting all retries.
        ValueError: If parameters are invalid.
    """
    # Input validation
    validate_retry_params(
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        jitter_factor=jitter_factor,
        timeout=timeout,
        max_total_time=max_total_time,
        max_wait_time=max_wait_time,
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
    finally:
        if owns_client:
            client.close()


async def execute_http_method_async(
    url: str,
    method: str,
    *,
    client: httpx.AsyncClient | None = None,
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
    """Execute an HTTP method with automatic retry logic (asynchronous).

    This is the core shared logic for all asynchronous HTTP methods.
    It handles client creation, parameter validation, and cleanup.

    Args:
        url: The URL to send the request to.
        method: The HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS).
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None. Must be > 0.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries.
            Must be >= 0. Ignored if backoff_strategy is provided.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        jitter_factor: Factor for adding random jitter to backoff delays.
            Must be >= 0.
        retry_if: Optional custom predicate function to determine whether to retry.
        backoff_strategy: Optional custom backoff strategy.
        max_total_time: Optional maximum total time budget in seconds.
            Must be > 0 if provided.
        max_wait_time: Optional maximum backoff delay cap in seconds.
            Must be > 0 if provided.
        on_request: Optional callback called before each request attempt.
        on_retry: Optional callback called before each retry.
        on_success: Optional callback called when request succeeds.
        on_failure: Optional callback called when all retries are exhausted.
        **kwargs: Additional keyword arguments passed to the client method.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request fails after exhausting all retries.
        ValueError: If parameters are invalid.
    """
    # Input validation
    validate_retry_params(
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        jitter_factor=jitter_factor,
        timeout=timeout,
        max_total_time=max_total_time,
        max_wait_time=max_wait_time,
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
    finally:
        if owns_client:
            await client.aclose()
