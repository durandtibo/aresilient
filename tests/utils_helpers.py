r"""Test utility functions to reduce boilerplate in tests.

This module provides reusable utility functions for common test patterns,
as described in Option 4 of UNIT_TEST_IMPROVEMENT_OPTIONS.md.

These utilities help reduce code duplication across test files and improve
test readability by extracting common patterns into well-named functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import httpx

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


__all__ = [
    "assert_successful_request",
    "assert_successful_request_async",
    "setup_mock_client_for_method",
    "setup_mock_async_client_for_method",
]


def setup_mock_client_for_method(
    client_method: str,
    status_code: int = 200,
    response_kwargs: dict | None = None,
) -> tuple[Mock, Mock]:
    """Create a mock httpx.Client with a specified method configured.

    This utility creates a properly configured mock client for testing,
    reducing boilerplate code in test setup.

    Args:
        client_method: The HTTP method name (e.g., "get", "post", "put").
        status_code: The status code the mock response should return.
            Default is 200.
        response_kwargs: Additional keyword arguments to configure the mock
            response. Default is None.

    Returns:
        A tuple of (mock_client, mock_response) where:
        - mock_client: A Mock object configured as httpx.Client with the
          specified method set up
        - mock_response: The Mock response object that the method will return

    Example:
        >>> client, response = setup_mock_client_for_method("get", 200)
        >>> result = get_with_automatic_retry("https://example.com", client=client)
        >>> assert result.status_code == 200
    """
    if response_kwargs is None:
        response_kwargs = {}

    mock_response = Mock(spec=httpx.Response, status_code=status_code, **response_kwargs)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, client_method, Mock(return_value=mock_response))

    return mock_client, mock_response


def setup_mock_async_client_for_method(
    client_method: str,
    status_code: int = 200,
    response_kwargs: dict | None = None,
) -> tuple[Mock, Mock]:
    """Create a mock httpx.AsyncClient with a specified method configured.

    This utility creates a properly configured mock async client for testing,
    reducing boilerplate code in async test setup.

    Args:
        client_method: The HTTP method name (e.g., "get", "post", "put").
        status_code: The status code the mock response should return.
            Default is 200.
        response_kwargs: Additional keyword arguments to configure the mock
            response. Default is None.

    Returns:
        A tuple of (mock_client, mock_response) where:
        - mock_client: A Mock object configured as httpx.AsyncClient with the
          specified method set up and aclose method mocked
        - mock_response: The Mock response object that the method will return

    Example:
        >>> client, response = setup_mock_async_client_for_method("get", 200)
        >>> result = await get_with_automatic_retry_async("https://example.com", client=client)
        >>> assert result.status_code == 200
    """
    if response_kwargs is None:
        response_kwargs = {}

    mock_response = Mock(spec=httpx.Response, status_code=status_code, **response_kwargs)
    mock_client = Mock(spec=httpx.AsyncClient, aclose=AsyncMock())
    setattr(mock_client, client_method, AsyncMock(return_value=mock_response))

    return mock_client, mock_response


def assert_successful_request(
    method_func: Callable[..., httpx.Response],
    url: str,
    client: httpx.Client,
    expected_status: int = 200,
    **kwargs,
) -> httpx.Response:
    """Assert that a request function succeeds and returns expected status.

    This utility combines the common pattern of calling a request function
    and asserting its status code, reducing test boilerplate.

    Args:
        method_func: The request function to call (e.g., get_with_automatic_retry).
        url: The URL to request.
        client: The httpx.Client to use for the request.
        expected_status: The expected HTTP status code. Default is 200.
        **kwargs: Additional keyword arguments to pass to the method function
            (e.g., headers, json, data).

    Returns:
        The httpx.Response object returned by the method function.

    Raises:
        AssertionError: If the response status code doesn't match expected_status.

    Example:
        >>> client, _ = setup_mock_client_for_method("get", 200)
        >>> response = assert_successful_request(
        ...     get_with_automatic_retry,
        ...     "https://example.com",
        ...     client,
        ...     headers={"X-Custom": "value"}
        ... )
        >>> assert response.status_code == 200
    """
    response = method_func(url, client=client, **kwargs)
    assert response.status_code == expected_status
    return response


async def assert_successful_request_async(
    method_func: Callable[..., Awaitable[httpx.Response]],
    url: str,
    client: httpx.AsyncClient,
    expected_status: int = 200,
    **kwargs,
) -> httpx.Response:
    """Assert that an async request function succeeds and returns expected status.

    This utility combines the common pattern of calling an async request function
    and asserting its status code, reducing test boilerplate.

    Args:
        method_func: The async request function to call (e.g.,
            get_with_automatic_retry_async).
        url: The URL to request.
        client: The httpx.AsyncClient to use for the request.
        expected_status: The expected HTTP status code. Default is 200.
        **kwargs: Additional keyword arguments to pass to the method function
            (e.g., headers, json, data).

    Returns:
        The httpx.Response object returned by the method function.

    Raises:
        AssertionError: If the response status code doesn't match expected_status.

    Example:
        >>> client, _ = setup_mock_async_client_for_method("get", 200)
        >>> response = await assert_successful_request_async(
        ...     get_with_automatic_retry_async,
        ...     "https://example.com",
        ...     client,
        ...     headers={"X-Custom": "value"}
        ... )
        >>> assert response.status_code == 200
    """
    response = await method_func(url, client=client, **kwargs)
    assert response.status_code == expected_status
    return response
