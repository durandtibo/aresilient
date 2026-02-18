r"""Shared HTTP method logic for sync and async operations.

This module contains shared HTTP method logic that is used by both
synchronous and asynchronous HTTP request implementations.
"""

from __future__ import annotations

__all__ = ["execute_http_method", "execute_http_method_async"]

from typing import Any

import httpx

from aresilient.core.config import DEFAULT_TIMEOUT, ClientConfig
from aresilient.core.validation import validate_timeout
from aresilient.request import request
from aresilient.request_async import request_async


def execute_http_method(
    url: str,
    method: str,
    *,
    client: httpx.Client | None = None,
    config: ClientConfig | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
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
            If None, default ClientConfig values are used.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None. Must be > 0.
        **kwargs: Additional keyword arguments passed to the client method.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request fails after exhausting all retries.
        ValueError: If parameters are invalid.
    """
    # Validate timeout (not part of ClientConfig)
    validate_timeout(timeout)

    config = config or ClientConfig()

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
            config=config,
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
            If None, default ClientConfig values are used.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None. Must be > 0.
        **kwargs: Additional keyword arguments passed to the client method.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request fails after exhausting all retries.
        ValueError: If parameters are invalid.
    """
    # Validate timeout (not part of ClientConfig)
    validate_timeout(timeout)

    config = config or ClientConfig()

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
            config=config,
            **kwargs,
        )
    finally:
        if owns_client:
            await client.aclose()
