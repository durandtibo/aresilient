r"""Parametrized unit tests for async recovery functionality in all HTTP method wrappers.

This test module tests recovery behavior after various types of failures
across all async HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, call

import httpx
import pytest

from aresilient import HttpRequestError

from .helpers import HTTP_METHODS_ASYNC, HttpMethodTestCase

TEST_URL = "https://api.example.com/data"


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_recovery_after_multiple_failures(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test successful recovery after multiple transient failures."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(
        side_effect=[
            Mock(spec=httpx.Response, status_code=429),
            Mock(spec=httpx.Response, status_code=503),
            Mock(spec=httpx.Response, status_code=500),
            mock_response,
        ]
    )
    setattr(mock_client, test_case.client_method, client_method)

    response = await test_case.method_func(TEST_URL, client=mock_client, max_retries=5)

    assert response.status_code == test_case.status_code
    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_mixed_error_and_status_failures(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test recovery from mix of errors and retryable status codes."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(
        side_effect=[
            httpx.RequestError("Network error"),
            Mock(spec=httpx.Response, status_code=502),
            httpx.TimeoutException("Timeout"),
            mock_response,
        ]
    )
    setattr(mock_client, test_case.client_method, client_method)

    response = await test_case.method_func(TEST_URL, client=mock_client, max_retries=5)

    assert response.status_code == test_case.status_code
    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_network_error(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that NetworkError is retried appropriately."""
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.NetworkError("Network unreachable"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api.example.com/data failed after 4 attempts",
    ):
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_read_error(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that ReadError is retried appropriately."""
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.ReadError("Connection broken"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api.example.com/data failed after 4 attempts",
    ):
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_write_error(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that WriteError is retried appropriately."""
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.WriteError("Write failed"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api.example.com/data failed after 4 attempts",
    ):
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_connect_timeout(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that ConnectTimeout is retried appropriately."""
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.ConnectTimeout("Connection timeout"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api.example.com/data timed out \(4 attempts\)",
    ):
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_read_timeout(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that ReadTimeout is retried appropriately."""
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.ReadTimeout("Read timeout"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api.example.com/data timed out \(4 attempts\)",
    ):
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_pool_timeout(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that PoolTimeout is retried appropriately."""
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.PoolTimeout("Connection pool exhausted"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api.example.com/data timed out \(4 attempts\)",
    ):
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_proxy_error(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that ProxyError is retried appropriately."""
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.ProxyError("Proxy connection failed"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api.example.com/data failed after 4 attempts",
    ):
        await test_case.method_func(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]
