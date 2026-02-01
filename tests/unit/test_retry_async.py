r"""Parametrized unit tests for async retry functionality in all HTTP
method wrappers.

This test module contains retry-related tests that verify the async
retry behavior across all async HTTP methods (GET, POST, PUT, DELETE,
PATCH, HEAD, OPTIONS) in a consistent and maintainable way.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, call

import httpx
import pytest

from aresilient import RETRY_STATUS_CODES, HttpRequestError
from tests.helpers import HTTP_METHODS_ASYNC, HttpMethodTestCase

TEST_URL = "https://api.example.com/data"


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_on_500_status(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test retry logic for 500 status code."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=500)
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=[mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    response = await test_case.method_func(TEST_URL, client=mock_client)

    assert response.status_code == test_case.status_code
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_retry_on_503_status(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test retry logic for 503 status code."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=[mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    response = await test_case.method_func(TEST_URL, client=mock_client)

    assert response.status_code == test_case.status_code
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_max_retries_exceeded(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that HttpRequestError is raised when max retries
    exceeded."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    with pytest.raises(HttpRequestError) as exc_info:
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=2)

    assert exc_info.value.status_code == 503
    assert "failed with status 503 after 3 attempts" in str(exc_info.value)
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_non_retryable_status_code(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that 404 status code is not retried."""
    mock_response = Mock(spec=httpx.Response, status_code=404)
    mock_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api\.example\.com/data failed with status 404",
    ):
        await test_case.method_func(TEST_URL, client=mock_client)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_zero_max_retries(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test with zero retries - should only try once."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to {TEST_URL} failed with status 503 after 1 attempts",
    ):
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=0)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_custom_status_forcelist(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test custom status codes for retry."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=404)
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=[mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    response = await test_case.method_func(TEST_URL, client=mock_client, status_forcelist=(404,))

    assert response.status_code == test_case.status_code
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
@pytest.mark.parametrize("status_code", RETRY_STATUS_CODES)
async def test_default_retry_status_codes(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
    status_code: int,
) -> None:
    """Test default retry status codes."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=status_code)
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=[mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    response = await test_case.method_func(TEST_URL, client=mock_client)

    assert response.status_code == test_case.status_code
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_all_retries_with_429(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test retry behavior with 429 Too Many Requests."""
    mock_response = Mock(spec=httpx.Response, status_code=429)
    mock_client = Mock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    with pytest.raises(HttpRequestError) as exc_info:
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=1)

    assert exc_info.value.status_code == 429
    assert "failed with status 429 after 2 attempts" in str(exc_info.value)
    assert mock_asleep.call_args_list == [call(0.3)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_timeout_exception_with_retries(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test timeout exception with retries."""
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api.example.com/data timed out \(3 attempts\)",
    ):
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=2)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_request_error_with_retries(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test handling of general request errors with retries."""
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(HttpRequestError, match=r"failed after 3 attempts"):
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=2)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]
