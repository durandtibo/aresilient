r"""Parametrized unit tests for callback functionality in all async HTTP
method wrappers.

This test module uses pytest parametrization to test callback
functionality across all async HTTP methods (GET, POST, PUT, DELETE,
PATCH, HEAD, OPTIONS) in a consistent and maintainable way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from aresilient import (
    HttpRequestError,
    delete_with_automatic_retry_async,
    get_with_automatic_retry_async,
    head_with_automatic_retry_async,
    options_with_automatic_retry_async,
    patch_with_automatic_retry_async,
    post_with_automatic_retry_async,
    put_with_automatic_retry_async,
)

if TYPE_CHECKING:
    from collections.abc import Callable

TEST_URL = "https://api.example.com/data"


@dataclass
class AsyncHttpMethodTestCase:
    """Test case definition for async HTTP method testing.

    Attributes:
        method_name: The HTTP method name (e.g., "GET", "POST").
        method_func: The async function to test (e.g., get_with_automatic_retry_async).
        client_method: The httpx.AsyncClient method name (e.g., "get", "post").
        success_code: Expected success status code. Optional, not used in all tests.
    """

    method_name: str
    method_func: Callable[..., httpx.Response]
    client_method: str
    success_code: int | None = None


# Define test parameters for all async HTTP methods
HTTP_METHODS_ASYNC = [
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="GET",
            method_func=get_with_automatic_retry_async,
            client_method="get",
            success_code=200,
        ),
        id="GET",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="POST",
            method_func=post_with_automatic_retry_async,
            client_method="post",
            success_code=201,
        ),
        id="POST",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="PUT",
            method_func=put_with_automatic_retry_async,
            client_method="put",
            success_code=200,
        ),
        id="PUT",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="DELETE",
            method_func=delete_with_automatic_retry_async,
            client_method="delete",
            success_code=204,
        ),
        id="DELETE",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="PATCH",
            method_func=patch_with_automatic_retry_async,
            client_method="patch",
            success_code=200,
        ),
        id="PATCH",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="HEAD",
            method_func=head_with_automatic_retry_async,
            client_method="head",
            success_code=200,
        ),
        id="HEAD",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="OPTIONS",
            method_func=options_with_automatic_retry_async,
            client_method="options",
            success_code=200,
        ),
        id="OPTIONS",
    ),
]


##################################################
#     Parametrized Tests for Async HTTP Methods #
#     with callback functionality               #
##################################################


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_http_method_async_on_request_callback(
    test_case: AsyncHttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that on_request callback is called for all async HTTP
    methods."""
    on_request_callback = Mock()
    mock_response = Mock(spec=httpx.Response, status_code=test_case.success_code)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_async_client, test_case.client_method, AsyncMock(return_value=mock_response))

    response = await test_case.method_func(
        TEST_URL, client=mock_async_client, on_request=on_request_callback
    )

    assert response.status_code == test_case.success_code
    on_request_callback.assert_called_once()
    call_args = on_request_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == test_case.method_name
    assert call_args["attempt"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_http_method_async_on_success_callback(
    test_case: AsyncHttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that on_success callback is called for successful async HTTP
    requests."""
    on_success_callback = Mock()
    mock_response = Mock(spec=httpx.Response, status_code=test_case.success_code)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_async_client, test_case.client_method, AsyncMock(return_value=mock_response))

    response = await test_case.method_func(
        TEST_URL, client=mock_async_client, on_success=on_success_callback
    )

    assert response.status_code == test_case.success_code
    on_success_callback.assert_called_once()
    call_args = on_success_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == test_case.method_name
    assert call_args["response"].status_code == test_case.success_code


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_http_method_async_on_retry_callback(
    test_case: AsyncHttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that on_retry callback is called when async HTTP request is
    retried."""
    on_retry_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_success_response = Mock(spec=httpx.Response, status_code=test_case.success_code)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=[mock_fail_response, mock_success_response]),
    )

    response = await test_case.method_func(
        TEST_URL, client=mock_async_client, on_retry=on_retry_callback
    )

    assert response.status_code == test_case.success_code
    on_retry_callback.assert_called_once()
    call_args = on_retry_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == test_case.method_name
    assert call_args["status_code"] == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_http_method_async_on_failure_callback(
    test_case: AsyncHttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that on_failure callback is called when async retries are
    exhausted."""
    on_failure_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_async_client, test_case.client_method, AsyncMock(return_value=mock_fail_response))

    with pytest.raises(HttpRequestError):
        await test_case.method_func(
            TEST_URL,
            client=mock_async_client,
            max_retries=2,
            on_failure=on_failure_callback,
        )

    on_failure_callback.assert_called_once()
    call_args = on_failure_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == test_case.method_name
    assert call_args["status_code"] == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_http_method_async_all_callbacks_together(
    test_case: AsyncHttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that all callbacks work together for async HTTP requests."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()

    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_success_response = Mock(spec=httpx.Response, status_code=test_case.success_code)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=[mock_fail_response, mock_success_response]),
    )

    response = await test_case.method_func(
        TEST_URL,
        client=mock_async_client,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_success=on_success_callback,
        on_failure=on_failure_callback,
    )

    assert response.status_code == test_case.success_code
    assert on_request_callback.call_count == 2  # Two attempts
    on_retry_callback.assert_called_once()  # One retry
    on_success_callback.assert_called_once()  # One success
    on_failure_callback.assert_not_called()  # No failure


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_http_method_async_callbacks_with_timeout_error(
    test_case: AsyncHttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that callbacks work when async HTTP request times out."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_failure_callback = Mock()

    mock_success_response = Mock(spec=httpx.Response, status_code=test_case.success_code)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=[httpx.TimeoutException("timeout"), mock_success_response]),
    )

    response = await test_case.method_func(
        TEST_URL,
        client=mock_async_client,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_failure=on_failure_callback,
    )

    assert response.status_code == test_case.success_code
    assert on_request_callback.call_count == 2
    on_retry_callback.assert_called_once()

    # Check that retry callback received error info
    retry_call_args = on_retry_callback.call_args[0][0]
    assert isinstance(retry_call_args["error"], httpx.TimeoutException)
