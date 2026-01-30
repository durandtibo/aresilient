r"""Contain utility functions for HTTP requests."""

from __future__ import annotations

__all__ = [
    "http_method_with_retry_wrapper",
    "http_method_with_retry_wrapper_async",
    "validate_retry_params",
]

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
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
    request_func: Callable[..., httpx.Response],
    request_with_retry: Callable[..., httpx.Response],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    """Wrap HTTP methods with automatic retry logic.

    This function provides the common implementation used by all HTTP method
    functions (GET, POST, PUT, DELETE, PATCH) to reduce code duplication.
    It handles validation and delegates to the retry logic.

    Args:
        url: The URL to send the request to.
        method: The HTTP method name (e.g., "GET", "POST") for logging.
        request_func: The httpx.Client method to call (e.g., client.get, client.post).
        request_with_retry: The retry logic function to use.
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

    return request_with_retry(
        url=url,
        method=method,
        request_func=request_func,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


async def http_method_with_retry_wrapper_async(
    url: str,
    method: str,
    request_func: Callable[..., httpx.Response],
    request_with_retry: Callable[..., httpx.Response],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    """Wrap async HTTP methods with automatic retry logic.

    This function provides the common implementation used by all async HTTP method
    functions (GET, POST, PUT, DELETE, PATCH) to reduce code duplication.
    It handles validation and delegates to the retry logic.

    Args:
        url: The URL to send the request to.
        method: The HTTP method name (e.g., "GET", "POST") for logging.
        request_func: The httpx.AsyncClient method to call (e.g., client.get, client.post).
        request_with_retry: The async retry logic function to use.
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

    return await request_with_retry(
        url=url,
        method=method,
        request_func=request_func,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )
