r"""Parametrized unit tests for retry_if custom predicate functionality
(async).

This test module uses pytest parametrization to test retry_if
functionality across all async HTTP methods (GET, POST, PUT, DELETE,
PATCH, HEAD, OPTIONS) in a consistent and maintainable way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, call

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
    from collections.abc import Awaitable, Callable

TEST_URL = "https://api.example.com/data"


@dataclass
class AsyncHttpMethodTestCase:
    """Test case definition for async HTTP method testing.

    Attributes:
        method_name: The HTTP method name (e.g., "GET", "POST").
        method_func: The async function to test (e.g., get_with_automatic_retry_async).
        client_method: The httpx.AsyncClient method name (e.g., "get", "post").
        success_code: Expected success status code.
    """

    method_name: str
    method_func: Callable[..., Awaitable[httpx.Response]]
    client_method: str
    success_code: int


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


########################################################
#     Tests for retry_if with successful responses     #
########################################################


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_returns_false_for_successful_response(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if that returns False for successful response (no
    retry)."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.success_code, text="success")
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_async_client, test_case.client_method, AsyncMock(return_value=mock_response))

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return False

    response = await test_case.method_func(
        TEST_URL, client=mock_async_client, retry_if=retry_predicate
    )

    assert response == mock_response
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_returns_true_for_successful_response(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if that returns True even for successful response
    (triggers retry)."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.success_code, text="success")
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_async_client, test_case.client_method, AsyncMock(return_value=mock_response_ok))

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Always retry - should exhaust retries
        return True

    with pytest.raises(
        HttpRequestError, match=f"failed with status {test_case.success_code} after 4 attempts"
    ):
        await test_case.method_func(
            TEST_URL, client=mock_async_client, retry_if=retry_predicate, max_retries=3
        )

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_checks_response_content(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if that checks response content and retries on
    specific text."""
    mock_response_retry = Mock(
        spec=httpx.Response, status_code=test_case.success_code, text="please retry"
    )
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.success_code, text="success")
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=[mock_response_retry, mock_response_ok]),
    )

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry if response contains "retry"
        return bool(response and "retry" in response.text.lower())

    response = await test_case.method_func(
        TEST_URL, client=mock_async_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    mock_asleep.assert_called_once_with(0.3)


#####################################################
#     Tests for retry_if with error responses       #
#####################################################


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_returns_false_for_error_response(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if that returns False for error response (no retry,
    immediate fail)."""
    mock_response_error = Mock(spec=httpx.Response, status_code=500)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_async_client, test_case.client_method, AsyncMock(return_value=mock_response_error))

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return False  # Never retry

    with pytest.raises(HttpRequestError, match="failed with status 500"):
        await test_case.method_func(TEST_URL, client=mock_async_client, retry_if=retry_predicate)

    # Should only try once since retry_if returns False
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_returns_true_for_error_response(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if that returns True for error response (triggers
    retry)."""
    mock_response_error = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.success_code)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=[mock_response_error, mock_response_ok]),
    )

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return bool(response and response.status_code >= 500)

    response = await test_case.method_func(
        TEST_URL, client=mock_async_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    mock_asleep.assert_called_once_with(0.3)


###################################################
#     Tests for retry_if with exceptions          #
###################################################


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_returns_false_for_exception(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if that returns False for exceptions (no retry)."""
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=httpx.TimeoutException("timeout")),
    )

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return False  # Never retry

    with pytest.raises(HttpRequestError, match="timed out"):
        await test_case.method_func(TEST_URL, client=mock_async_client, retry_if=retry_predicate)

    # Should only try once
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_returns_true_for_exception(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if that returns True for exceptions (triggers
    retry)."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.success_code)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=[httpx.TimeoutException("timeout"), mock_response_ok]),
    )

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry on timeout exceptions
        return bool(isinstance(exception, httpx.TimeoutException))

    response = await test_case.method_func(
        TEST_URL, client=mock_async_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_with_connection_error(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if that handles connection errors."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.success_code)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=[httpx.ConnectError("connection failed"), mock_response_ok]),
    )

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry on connection errors
        return bool(isinstance(exception, httpx.ConnectError))

    response = await test_case.method_func(
        TEST_URL, client=mock_async_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_exhausts_retries_with_exception(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if exhausts retries when exception keeps occurring."""
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=httpx.TimeoutException("timeout")),
    )

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Always retry timeouts
        return bool(isinstance(exception, httpx.TimeoutException))

    with pytest.raises(HttpRequestError, match="timed out"):
        await test_case.method_func(
            TEST_URL, client=mock_async_client, retry_if=retry_predicate, max_retries=2
        )

    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


#########################################################
#     Tests for retry_if with mixed scenarios           #
#########################################################


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_complex_logic(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if with complex custom logic combining response and
    exception checks."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500, text="server error")
    mock_response_200_retry = Mock(spec=httpx.Response, status_code=200, text="rate limit exceeded")
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.success_code, text="success")

    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=[mock_response_500, mock_response_200_retry, mock_response_ok]),
    )

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry on server errors
        if response and response.status_code >= 500:
            return True
        # Retry if response contains rate limit message
        if response and "rate limit" in response.text.lower():
            return True
        # Retry on network errors
        return bool(isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)))

    response = await test_case.method_func(
        TEST_URL, client=mock_async_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_none_uses_default_behavior(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test that when retry_if is None, default status_forcelist
    behavior is used."""
    mock_response_503 = Mock(spec=httpx.Response, status_code=503)
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.success_code)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=[mock_response_503, mock_response_ok]),
    )

    # No retry_if provided - should use default behavior
    response = await test_case.method_func(
        TEST_URL, client=mock_async_client, status_forcelist=(503,), max_retries=3
    )

    assert response == mock_response_ok
    mock_asleep.assert_called_once_with(0.3)


############################################
#     Tests for retry_if with callbacks    #
############################################


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_with_on_retry_callback(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if works correctly with on_retry callback."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.success_code)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(
        mock_async_client,
        test_case.client_method,
        AsyncMock(side_effect=[mock_response_500, mock_response_ok]),
    )

    retry_callback = Mock()

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return bool(response and response.status_code >= 500)

    response = await test_case.method_func(
        TEST_URL,
        client=mock_async_client,
        retry_if=retry_predicate,
        on_retry=retry_callback,
        max_retries=3,
    )

    assert response == mock_response_ok
    retry_callback.assert_called_once()
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_if_with_on_failure_callback(
    test_case: AsyncHttpMethodTestCase, mock_asleep: Mock
) -> None:
    """Test retry_if triggers on_failure callback when retries
    exhausted."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)
    mock_async_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_async_client, test_case.client_method, AsyncMock(return_value=mock_response_500))

    failure_callback = Mock()

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return bool(response and response.status_code >= 500)

    with pytest.raises(HttpRequestError):
        await test_case.method_func(
            TEST_URL,
            client=mock_async_client,
            retry_if=retry_predicate,
            on_failure=failure_callback,
            max_retries=2,
        )

    failure_callback.assert_called_once()
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]
