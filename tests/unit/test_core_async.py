r"""Parametrized unit tests for async core functionality in all HTTP
method wrappers.

This test module uses pytest parametrization to test core functionality
across all async HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
in a consistent and maintainable way. Tests that are common to all
methods are defined here to reduce duplication.

Method-specific tests remain in their respective test files:
- test_get_async.py: GET-specific tests (e.g., params support)
- test_post_async.py: POST-specific tests (e.g., data/form submission)
- test_put_async.py: PUT-specific tests
- test_delete_async.py: DELETE-specific tests
- test_patch_async.py: PATCH-specific tests
- test_head_async.py: HEAD-specific tests (e.g., response body handling)
- test_options_async.py: OPTIONS-specific tests

Retry, backoff, and recovery tests are in their respective specialized files:
- test_retry_async.py: Retry mechanism tests
- test_backoff_async.py: Backoff strategy tests
- test_recovery_async.py: Error recovery and specific exception tests
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from aresilient import HttpRequestError
from aresilient.core import ClientConfig
from tests.helpers import HTTP_METHODS_ASYNC, HttpMethodTestCase

TEST_URL = "https://api.example.com/data"


############################################################
#     Parametrized Tests for Core HTTP Method Features     #
############################################################


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_successful_request_with_custom_client(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test successful request with custom client."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    response = await test_case.method_func(TEST_URL, client=mock_client)

    assert response.status_code == test_case.status_code
    client_method = getattr(mock_client, test_case.client_method)
    client_method.assert_called_once_with(url=TEST_URL)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_successful_request_with_default_client(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test successful request on first attempt with default client."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)

    with patch(f"httpx.AsyncClient.{test_case.client_method}", return_value=mock_response):
        response = await test_case.method_func(TEST_URL)

    assert response.status_code == test_case.status_code
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_request_with_json_payload(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test request with JSON data."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    response = await test_case.method_func(TEST_URL, json={"key": "value"}, client=mock_client)

    assert response.status_code == test_case.status_code
    client_method = getattr(mock_client, test_case.client_method)
    client_method.assert_called_once_with(url=TEST_URL, json={"key": "value"})
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_timeout_exception(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test handling of timeout exception."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api.example.com/data timed out \(1 attempts\)",
    ):
        await test_case.method_func(
            TEST_URL, client=mock_client, config=ClientConfig(max_retries=0)
        )

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_request_error(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test handling of general request errors."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=(
            rf"{test_case.method_name} request to https://api.example.com/data failed after 1 attempts: "
            r"Connection failed"
        ),
    ):
        await test_case.method_func(
            TEST_URL, client=mock_client, config=ClientConfig(max_retries=0)
        )

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_negative_max_retries(test_case: HttpMethodTestCase) -> None:
    """Test that negative max_retries raises ValueError via
    ClientConfig."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        await test_case.method_func(TEST_URL, config=ClientConfig(max_retries=-1))


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_negative_timeout(test_case: HttpMethodTestCase) -> None:
    """Test that negative timeout raises ValueError."""
    with pytest.raises(ValueError, match=r"timeout must be > 0"):
        await test_case.method_func(TEST_URL, timeout=-1.0)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_zero_timeout(test_case: HttpMethodTestCase) -> None:
    """Test that zero timeout raises ValueError."""
    with pytest.raises(ValueError, match=r"timeout must be > 0"):
        await test_case.method_func(TEST_URL, timeout=0.0)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_client_close_when_owns_client(test_case: HttpMethodTestCase) -> None:
    """Test that client is closed when created internally."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    with patch("httpx.AsyncClient", return_value=mock_client):
        await test_case.method_func(TEST_URL)

    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_client_not_closed_when_provided(test_case: HttpMethodTestCase) -> None:
    """Test that external client is not closed."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    await test_case.method_func(TEST_URL, client=mock_client)

    mock_client.aclose.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_custom_timeout(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test custom timeout parameter."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = mock_client
        await test_case.method_func(TEST_URL, timeout=30.0)

    mock_client_class.assert_called_once_with(timeout=30.0)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_with_httpx_timeout_object(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test request with httpx.Timeout object."""
    timeout_config = httpx.Timeout(10.0, connect=5.0)
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_instance = AsyncMock()
        setattr(
            mock_client_instance, test_case.client_method, AsyncMock(return_value=mock_response)
        )
        mock_client_instance.aclose = AsyncMock()
        mock_client_class.return_value = mock_client_instance
        response = await test_case.method_func(TEST_URL, timeout=timeout_config)

    mock_client_class.assert_called_once_with(timeout=timeout_config)
    assert response.status_code == test_case.status_code
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
@pytest.mark.parametrize("status_code", [200, 201, 202, 204, 206])
async def test_successful_2xx_status_codes(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
    status_code: int,
) -> None:
    """Test that various 2xx status codes are considered successful."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    response = await test_case.method_func(TEST_URL, client=mock_client)

    assert response.status_code == status_code
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
@pytest.mark.parametrize("status_code", [301, 302, 303, 304, 307, 308])
async def test_successful_3xx_status_codes(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
    status_code: int,
) -> None:
    """Test that 3xx redirect status codes are considered successful."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    response = await test_case.method_func(TEST_URL, client=mock_client)

    assert response.status_code == status_code
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_with_headers(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test request with custom headers."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    response = await test_case.method_func(
        TEST_URL,
        client=mock_client,
        headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
    )

    assert response.status_code == test_case.status_code
    client_method = getattr(mock_client, test_case.client_method)
    client_method.assert_called_once_with(
        url=TEST_URL,
        headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
    )
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_error_message_includes_url(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that error message includes the URL."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    with pytest.raises(
        HttpRequestError,
        match=(
            rf"{test_case.method_name} request to https://api.example.com/data failed with status 503 "
            r"after 1 attempts"
        ),
    ):
        await test_case.method_func(
            TEST_URL, client=mock_client, config=ClientConfig(max_retries=0)
        )

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_client_close_on_exception(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that client is closed even when exception occurs."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
    setattr(mock_client, test_case.client_method, client_method)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        pytest.raises(
            HttpRequestError,
            match=rf"{test_case.method_name} request to https://api.example.com/data timed out \(1 attempts\)",
        ),
    ):
        await test_case.method_func(TEST_URL, config=ClientConfig(max_retries=0))

    mock_client.aclose.assert_called_once()
    mock_asleep.assert_not_called()


############################################################
#     Tests for ClientConfig parameter support (async)     #
############################################################


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_successful_request_with_config(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test successful async request using ClientConfig."""
    config = ClientConfig(max_retries=2)
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    response = await test_case.method_func(TEST_URL, client=mock_client, config=config)

    assert response.status_code == test_case.status_code
    client_method = getattr(mock_client, test_case.client_method)
    client_method.assert_called_once_with(url=TEST_URL)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_config_values_are_used(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that config values are respected when async request
    fails."""
    config = ClientConfig(max_retries=0)
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    with pytest.raises(
        HttpRequestError,
        match=(
            rf"{test_case.method_name} request to https://api.example.com/data failed with status 503 "
            r"after 1 attempts"
        ),
    ):
        await test_case.method_func(TEST_URL, client=mock_client, config=config)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_config_none_uses_defaults(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that config=None uses default values for async requests."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response))

    response = await test_case.method_func(TEST_URL, client=mock_client, config=None)

    assert response.status_code == test_case.status_code
    mock_asleep.assert_not_called()


##################################################################
#     Tests for individual retry parameter support (async)       #
##################################################################


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_individual_max_retries_param(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that max_retries can be passed directly to async functions."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(
        mock_client,
        test_case.client_method,
        AsyncMock(side_effect=[mock_response_fail, mock_response_ok]),
    )

    response = await test_case.method_func(TEST_URL, client=mock_client, max_retries=1)

    assert response.status_code == test_case.status_code
    assert getattr(mock_client, test_case.client_method).call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_individual_max_retries_overrides_config(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that direct max_retries parameter overrides config value for async functions."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    setattr(mock_client, test_case.client_method, AsyncMock(return_value=mock_response_fail))

    # config says max_retries=3 but we override with max_retries=0
    with pytest.raises(HttpRequestError):
        await test_case.method_func(
            TEST_URL, client=mock_client, config=ClientConfig(max_retries=3), max_retries=0
        )

    # Only 1 attempt (no retries)
    assert getattr(mock_client, test_case.client_method).call_count == 1
    mock_asleep.assert_not_called()
