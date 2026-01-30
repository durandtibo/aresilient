r"""Unified HTTP request functions with automatic retry logic.

This module provides a simplified interface for making HTTP requests with
automatic retry logic. It consolidates both synchronous and asynchronous
implementations for all HTTP methods (GET, POST, PUT, DELETE, PATCH).
"""

from __future__ import annotations

__all__ = [
    "delete_with_automatic_retry",
    "delete_with_automatic_retry_async",
    "get_with_automatic_retry",
    "get_with_automatic_retry_async",
    "patch_with_automatic_retry",
    "patch_with_automatic_retry_async",
    "post_with_automatic_retry",
    "post_with_automatic_retry_async",
    "put_with_automatic_retry",
    "put_with_automatic_retry_async",
]

from typing import Any

import httpx

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresnet.request import request_with_automatic_retry
from aresnet.request_async import request_with_automatic_retry_async
from aresnet.utils import validate_retry_params


def _make_http_request(
    method: str,
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Generic synchronous HTTP request with automatic retry logic.

    This is an internal helper function that implements the core retry logic
    for all HTTP methods. It validates parameters, manages the client lifecycle,
    and delegates to the request retry function.

    Args:
        method: The HTTP method to use (e.g., "GET", "POST", "PUT", "DELETE", "PATCH").
        url: The URL to send the request to.
        client: An optional httpx.Client object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to the httpx.Client method.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.
    """
    validate_retry_params(max_retries, backoff_factor)

    owns_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        request_func = getattr(client, method.lower())
        return request_with_automatic_retry(
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


async def _make_http_request_async(
    method: str,
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Generic asynchronous HTTP request with automatic retry logic.

    This is an internal helper function that implements the core retry logic
    for all async HTTP methods. It validates parameters, manages the async client
    lifecycle, and delegates to the async request retry function.

    Args:
        method: The HTTP method to use (e.g., "GET", "POST", "PUT", "DELETE", "PATCH").
        url: The URL to send the request to.
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to the httpx.AsyncClient method.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.
    """
    validate_retry_params(max_retries, backoff_factor)

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    try:
        request_func = getattr(client, method.lower())
        return await request_with_automatic_retry_async(
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


# GET methods
def get_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP GET request with automatic retry logic for transient
    errors.

    This function performs an HTTP GET request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the GET request to.
        client: An optional httpx.Client object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.Client.get()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> from aresnet import get_with_automatic_retry
        >>> response = get_with_automatic_retry("https://api.example.com/data")  # doctest: +SKIP

        ```
    """
    return _make_http_request(
        "GET",
        url,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


async def get_with_automatic_retry_async(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP GET request asynchronously with automatic retry
    logic for transient errors.

    This function performs an HTTP GET request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the GET request to.
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.AsyncClient.get()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> import asyncio
        >>> from aresnet import get_with_automatic_retry_async
        >>> async def example():
        ...     response = await get_with_automatic_retry_async("https://api.example.com/data")
        ...     return response.json()
        ...
        >>> asyncio.run(example())  # doctest: +SKIP

        ```
    """
    return await _make_http_request_async(
        "GET",
        url,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


# POST methods
def post_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP POST request with automatic retry logic for
    transient errors.

    This function performs an HTTP POST request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the POST request to.
        client: An optional httpx.Client object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.Client.post()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> from aresnet import post_with_automatic_retry
        >>> response = post_with_automatic_retry(
        ...     "https://api.example.com/data", json={"key": "value"}
        ... )  # doctest: +SKIP

        ```
    """
    return _make_http_request(
        "POST",
        url,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


async def post_with_automatic_retry_async(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP POST request asynchronously with automatic retry
    logic for transient errors.

    This function performs an HTTP POST request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the POST request to.
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.AsyncClient.post()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> import asyncio
        >>> from aresnet import post_with_automatic_retry_async
        >>> async def example():
        ...     response = await post_with_automatic_retry_async(
        ...         "https://api.example.com/data", json={"key": "value"}
        ...     )
        ...     return response.status_code
        ...
        >>> asyncio.run(example())  # doctest: +SKIP

        ```
    """
    return await _make_http_request_async(
        "POST",
        url,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


# PUT methods
def put_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP PUT request with automatic retry logic for transient
    errors.

    This function performs an HTTP PUT request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the PUT request to.
        client: An optional httpx.Client object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.Client.put()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> from aresnet import put_with_automatic_retry
        >>> response = put_with_automatic_retry(
        ...     "https://api.example.com/resource/123", json={"name": "updated"}
        ... )  # doctest: +SKIP

        ```
    """
    return _make_http_request(
        "PUT",
        url,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


async def put_with_automatic_retry_async(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP PUT request asynchronously with automatic retry
    logic for transient errors.

    This function performs an HTTP PUT request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the PUT request to.
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.AsyncClient.put()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> import asyncio
        >>> from aresnet import put_with_automatic_retry_async
        >>> async def example():
        ...     response = await put_with_automatic_retry_async(
        ...         "https://api.example.com/resource/123", json={"name": "updated"}
        ...     )
        ...     return response.status_code
        ...
        >>> asyncio.run(example())  # doctest: +SKIP

        ```
    """
    return await _make_http_request_async(
        "PUT",
        url,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


# DELETE methods
def delete_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP DELETE request with automatic retry logic for
    transient errors.

    This function performs an HTTP DELETE request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the DELETE request to.
        client: An optional httpx.Client object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.Client.delete()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> from aresnet import delete_with_automatic_retry
        >>> response = delete_with_automatic_retry(
        ...     "https://api.example.com/resource/123"
        ... )  # doctest: +SKIP
        >>> response.status_code  # doctest: +SKIP
        204
        ```
    """
    return _make_http_request(
        "DELETE",
        url,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


async def delete_with_automatic_retry_async(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP DELETE request asynchronously with automatic retry
    logic for transient errors.

    This function performs an HTTP DELETE request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the DELETE request to.
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.AsyncClient.delete()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> import asyncio
        >>> from aresnet import delete_with_automatic_retry_async
        >>> async def example():
        ...     response = await delete_with_automatic_retry_async(
        ...         "https://api.example.com/resource/123"
        ...     )
        ...     return response.status_code
        ...
        >>> asyncio.run(example())  # doctest: +SKIP
        204
        ```
    """
    return await _make_http_request_async(
        "DELETE",
        url,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


# PATCH methods
def patch_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP PATCH request with automatic retry logic for
    transient errors.

    This function performs an HTTP PATCH request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the PATCH request to.
        client: An optional httpx.Client object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.Client.patch()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> from aresnet import patch_with_automatic_retry
        >>> response = patch_with_automatic_retry(
        ...     "https://api.example.com/resource/123", json={"status": "active"}
        ... )  # doctest: +SKIP

        ```
    """
    return _make_http_request(
        "PATCH",
        url,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


async def patch_with_automatic_retry_async(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP PATCH request asynchronously with automatic retry
    logic for transient errors.

    This function performs an HTTP PATCH request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the PATCH request to.
        client: An optional httpx.AsyncClient object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.AsyncClient.patch()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> import asyncio
        >>> from aresnet import patch_with_automatic_retry_async
        >>> async def example():
        ...     response = await patch_with_automatic_retry_async(
        ...         "https://api.example.com/resource/123", json={"status": "active"}
        ...     )
        ...     return response.status_code
        ...
        >>> asyncio.run(example())  # doctest: +SKIP

        ```
    """
    return await _make_http_request_async(
        "PATCH",
        url,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )
