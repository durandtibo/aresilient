r"""Contain utility functions for HTTP requests."""

from __future__ import annotations

__all__ = [
    "http_method_with_retry_wrapper",
    "http_method_with_retry_wrapper_async",
    "validate_retry_params",
]

from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Callable

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)


def validate_retry_params(max_retries: int, backoff_factor: float) -> None:
    """Validate retry parameters.

    Args:
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries.
            Must be >= 0.

    Raises:
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> from aresnet.utils import validate_retry_params
        >>> validate_retry_params(max_retries=3, backoff_factor=0.5)
        >>> validate_retry_params(max_retries=-1, backoff_factor=0.5)  # doctest: +SKIP

        ```
    """
    if max_retries < 0:
        msg = f"max_retries must be >= 0, got {max_retries}"
        raise ValueError(msg)
    if backoff_factor < 0:
        msg = f"backoff_factor must be >= 0, got {backoff_factor}"
        raise ValueError(msg)


def http_method_with_retry_wrapper(
    url: str,
    method: str,
    client_method_name: str,
    request_with_retry: Callable[..., httpx.Response],
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    """Wrap HTTP methods with automatic retry logic.

    This function provides the common implementation used by all HTTP method
    functions (GET, POST, PUT, DELETE, PATCH) to reduce code duplication.
    It handles client creation, validation, and cleanup.

    Args:
        url: The URL to send the request to.
        method: The HTTP method name (e.g., "GET", "POST") for logging.
        client_method_name: The name of the httpx.Client method to call
            (e.g., "get", "post").
        request_with_retry: The retry logic function to use.
        client: An optional httpx.Client object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to the request function.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.
    """
    # Input validation
    validate_retry_params(max_retries, backoff_factor)

    owns_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        request_func = getattr(client, client_method_name)
        return request_with_retry(
            url=url,
            method=method,
            request_func=request_func,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            **kwargs,
        )
    finally:
        if owns_client:
            client.close()


async def http_method_with_retry_wrapper_async(
    url: str,
    method: str,
    client_method_name: str,
    request_with_retry: Callable[..., httpx.Response],
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    """Wrap async HTTP methods with automatic retry logic.

    This function provides the common implementation used by all async HTTP method
    functions (GET, POST, PUT, DELETE, PATCH) to reduce code duplication.
    It handles client creation, validation, and cleanup.

    Args:
        url: The URL to send the request to.
        method: The HTTP method name (e.g., "GET", "POST") for logging.
        client_method_name: The name of the httpx.AsyncClient method to call
            (e.g., "get", "post").
        request_with_retry: The async retry logic function to use.
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to the request function.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.
    """
    # Input validation
    validate_retry_params(max_retries, backoff_factor)

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    try:
        request_func = getattr(client, client_method_name)
        return await request_with_retry(
            url=url,
            method=method,
            request_func=request_func,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            **kwargs,
        )
    finally:
        if owns_client:
            await client.aclose()
