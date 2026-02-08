r"""Shared test helpers and fixtures for HTTP method wrapper tests.

This module contains common test infrastructure used across multiple
test files to reduce duplication and improve maintainability.
"""

from __future__ import annotations

__all__ = [
    "HTTPBIN_URL",
    "HTTP_METHODS",
    "HTTP_METHODS_ASYNC",
    "AsyncHttpMethodTestCase",
    "HttpMethodTestCase",
    "assert_successful_request",
    "assert_successful_request_async",
    "create_mock_async_client_with_side_effect",
    "create_mock_client_with_side_effect",
    "setup_mock_async_client_for_method",
    "setup_mock_client_for_method",
]

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from aresilient import (
    delete_with_automatic_retry,
    delete_with_automatic_retry_async,
    get_with_automatic_retry,
    get_with_automatic_retry_async,
    head_with_automatic_retry,
    head_with_automatic_retry_async,
    options_with_automatic_retry,
    options_with_automatic_retry_async,
    patch_with_automatic_retry,
    patch_with_automatic_retry_async,
    post_with_automatic_retry,
    post_with_automatic_retry_async,
    put_with_automatic_retry,
    put_with_automatic_retry_async,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


@dataclass
class HttpMethodTestCase:
    """Test case definition for HTTP method testing.

    Attributes:
        method_name: The HTTP method name (e.g., "GET", "POST").
        method_func: The function to test (e.g., get_with_automatic_retry).
        client_method: The httpx.Client method name (e.g., "get", "post").
        status_code: Expected success status code.
        test_url: The full test URL (e.g., "https://httpbin.org/get"). Optional.
        supports_body: Whether the HTTP method supports request bodies. Optional.
    """

    method_name: str
    method_func: Callable[..., httpx.Response]
    client_method: str
    status_code: int | None = None
    test_url: str | None = None
    supports_body: bool | None = None


@dataclass
class AsyncHttpMethodTestCase:
    """Test case definition for async HTTP method testing.

    Attributes:
        method_name: The HTTP method name (e.g., "GET", "POST").
        method_func: The async function to test (e.g., get_with_automatic_retry_async).
        client_method: The httpx.AsyncClient method name (e.g., "get", "post").
        status_code: Expected success status code.
        test_url: The full test URL (e.g., "https://httpbin.org/get"). Optional.
        supports_body: Whether the HTTP method supports request bodies. Optional.
    """

    method_name: str
    method_func: Callable[..., Awaitable[httpx.Response]]
    client_method: str
    status_code: int | None = None
    test_url: str | None = None
    supports_body: bool | None = None


# Define test parameters for all sync HTTP methods
HTTP_METHODS = [
    pytest.param(
        HttpMethodTestCase(
            method_name="GET",
            method_func=get_with_automatic_retry,
            client_method="get",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="GET",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="POST",
            method_func=post_with_automatic_retry,
            client_method="post",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/post",
            supports_body=True,
        ),
        id="POST",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="PUT",
            method_func=put_with_automatic_retry,
            client_method="put",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/put",
            supports_body=True,
        ),
        id="PUT",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="DELETE",
            method_func=delete_with_automatic_retry,
            client_method="delete",
            status_code=204,
            test_url=f"{HTTPBIN_URL}/delete",
            supports_body=False,
        ),
        id="DELETE",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="PATCH",
            method_func=patch_with_automatic_retry,
            client_method="patch",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/patch",
            supports_body=True,
        ),
        id="PATCH",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="HEAD",
            method_func=head_with_automatic_retry,
            client_method="head",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="HEAD",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="OPTIONS",
            method_func=options_with_automatic_retry,
            client_method="options",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="OPTIONS",
    ),
]


# Define test parameters for all async HTTP methods
HTTP_METHODS_ASYNC = [
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="GET",
            method_func=get_with_automatic_retry_async,
            client_method="get",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="GET",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="POST",
            method_func=post_with_automatic_retry_async,
            client_method="post",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/post",
            supports_body=True,
        ),
        id="POST",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="PUT",
            method_func=put_with_automatic_retry_async,
            client_method="put",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/put",
            supports_body=True,
        ),
        id="PUT",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="DELETE",
            method_func=delete_with_automatic_retry_async,
            client_method="delete",
            status_code=204,
            test_url=f"{HTTPBIN_URL}/delete",
            supports_body=False,
        ),
        id="DELETE",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="PATCH",
            method_func=patch_with_automatic_retry_async,
            client_method="patch",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/patch",
            supports_body=True,
        ),
        id="PATCH",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="HEAD",
            method_func=head_with_automatic_retry_async,
            client_method="head",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="HEAD",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="OPTIONS",
            method_func=options_with_automatic_retry_async,
            client_method="options",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="OPTIONS",
    ),
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
    """Create a mock httpx.AsyncClient with a specified method
    configured.

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
    **kwargs: dict,
) -> httpx.Response:
    """Assert that a request function succeeds and returns expected
    status.

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
    **kwargs: dict,
) -> httpx.Response:
    """Assert that an async request function succeeds and returns
    expected status.

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


def create_mock_client_with_side_effect(
    client_method: str,
    side_effect: list[httpx.Response | Exception],
) -> tuple[Mock, list[Mock]]:
    """Create a mock httpx.Client with a method that has side effects.

    This utility is commonly used for testing retry logic where multiple
    responses (failures followed by success) are returned.

    Args:
        client_method: The HTTP method name (e.g., "get", "post", "put").
        side_effect: A list of mock responses or exceptions to return in sequence.
            Each element will be returned/raised on successive calls.

    Returns:
        A tuple of (mock_client, mock_responses) where:
        - mock_client: A Mock object configured as httpx.Client with the
          specified method set up with side_effect
        - mock_responses: The list of mock response objects passed as side_effect

    Example:
        >>> fail_response = Mock(spec=httpx.Response, status_code=503)
        >>> success_response = Mock(spec=httpx.Response, status_code=200)
        >>> client, responses = create_mock_client_with_side_effect(
        ...     "get", [fail_response, success_response]
        ... )
        >>> # First call returns 503, second call returns 200
    """
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, client_method, Mock(side_effect=side_effect))
    return mock_client, side_effect


def create_mock_async_client_with_side_effect(
    client_method: str,
    side_effect: list[httpx.Response | Exception],
) -> tuple[Mock, list[Mock]]:
    """Create a mock httpx.AsyncClient with a method that has side effects.

    This utility is commonly used for testing async retry logic where multiple
    responses (failures followed by success) are returned.

    Args:
        client_method: The HTTP method name (e.g., "get", "post", "put").
        side_effect: A list of mock responses or exceptions to return in sequence.
            Each element will be returned/raised on successive calls.

    Returns:
        A tuple of (mock_client, mock_responses) where:
        - mock_client: A Mock object configured as httpx.AsyncClient with the
          specified method set up with side_effect and aclose method mocked
        - mock_responses: The list of mock response objects passed as side_effect

    Example:
        >>> fail_response = Mock(spec=httpx.Response, status_code=503)
        >>> success_response = Mock(spec=httpx.Response, status_code=200)
        >>> client, responses = create_mock_async_client_with_side_effect(
        ...     "get", [fail_response, success_response]
        ... )
        >>> # First call returns 503, second call returns 200
    """
    mock_client = Mock(spec=httpx.AsyncClient, aclose=AsyncMock())
    setattr(mock_client, client_method, AsyncMock(side_effect=side_effect))
    return mock_client, side_effect
