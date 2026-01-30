r"""Contain asynchronous HTTP GET request with automatic retry logic."""

from __future__ import annotations

__all__ = ["get_with_automatic_retry_async"]

from typing import Any

import httpx

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresnet.request_async import request_with_automatic_retry_async
from aresnet.utils import validate_retry_params


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
    # Input validation
    validate_retry_params(max_retries, backoff_factor)

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    try:
        return await request_with_automatic_retry_async(
            url=url,
            method="GET",
            request_func=client.get,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            **kwargs,
        )
    finally:
        if owns_client:
            await client.aclose()
