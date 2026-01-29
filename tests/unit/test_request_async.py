"""Unit tests for asynchronous HTTP request retry logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, call

import httpx
import pytest

from aresnet import HttpRequestError, request_with_automatic_retry_async


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200)


@pytest.fixture
def mock_request_func(mock_response: httpx.Response) -> AsyncMock:
    return AsyncMock(return_value=mock_response)


########################################################
#     Tests for request_with_automatic_retry_async     #
########################################################


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_successful_request_on_first_attempt(
    mock_response: httpx.Response, mock_request_func: AsyncMock, mock_asleep: Mock
) -> None:
    """Test that a successful request returns immediately without
    retries."""
    result = await request_with_automatic_retry_async(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
    )

    assert result == mock_response
    mock_request_func.assert_called_once_with(url="https://example.com")
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_successful_request_after_retries(
    mock_response: httpx.Response, mock_asleep: Mock
) -> None:
    """Test that request succeeds after initial retryable failures."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = AsyncMock(
        side_effect=[mock_response_fail, mock_response_fail, mock_response]
    )

    result = await request_with_automatic_retry_async(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
        max_retries=3,
    )

    assert result == mock_response
    assert mock_request_func.call_args_list == [
        call(url="https://example.com"),
        call(url="https://example.com"),
        call(url="https://example.com"),
    ]
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_non_retryable_status_code_raises_immediately(
    mock_asleep: Mock,
) -> None:
    """Test that non-retryable status codes (e.g., 404) raise without
    retries."""
    mock_response = Mock(spec=httpx.Response, status_code=404)
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=Mock(), response=mock_response
    )
    mock_request_func = AsyncMock(return_value=mock_response)

    with pytest.raises(httpx.HTTPStatusError, match=r"Not Found"):
        await request_with_automatic_retry_async(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
        )

    mock_request_func.assert_called_once_with(url="https://example.com")
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [429, 500, 502, 503, 504])
async def test_request_with_automatic_retry_async_retryable_status_codes(
    status_code: int, mock_asleep: Mock
) -> None:
    """Test that retryable status codes (429, 500, 502, 503, 504)
    trigger retries."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_request_func = AsyncMock(return_value=mock_response)

    with pytest.raises(
        HttpRequestError,
        match=f"GET request to https://example.com failed with status {status_code} after 3 attempts",
    ) as exc_info:
        await request_with_automatic_retry_async(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            max_retries=2,
        )

    assert mock_request_func.call_args_list == [
        call(url="https://example.com"),
        call(url="https://example.com"),
        call(url="https://example.com"),
    ]  # 1 initial + 2 retries
    assert exc_info.value.status_code == status_code
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_timeout_exception_retries(
    mock_asleep: Mock,
) -> None:
    """Test that TimeoutException triggers retries."""
    mock_request_func = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

    with pytest.raises(
        HttpRequestError,
        match=r"POST request to https://example.com timed out \(3 attempts\)",
    ):
        await request_with_automatic_retry_async(
            url="https://example.com",
            method="POST",
            request_func=mock_request_func,
            max_retries=2,
        )

    assert mock_request_func.call_args_list == [
        call(url="https://example.com"),
        call(url="https://example.com"),
        call(url="https://example.com"),
    ]
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_request_error_retries(mock_asleep: Mock) -> None:
    """Test that RequestError (network errors) triggers retries."""
    mock_request_func = AsyncMock(side_effect=httpx.RequestError("Connection failed"))

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://example.com failed after 3 attempts: Connection failed",
    ):
        await request_with_automatic_retry_async(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            max_retries=2,
        )

    assert mock_request_func.call_args_list == [
        call(url="https://example.com"),
        call(url="https://example.com"),
        call(url="https://example.com"),
    ]
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_exponential_backoff(mock_asleep: Mock) -> None:
    """Test that exponential backoff is applied correctly."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = AsyncMock(return_value=mock_response)

    with pytest.raises(HttpRequestError):
        await request_with_automatic_retry_async(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
        )

    assert mock_request_func.call_args_list == [
        call(url="https://example.com"),
        call(url="https://example.com"),
        call(url="https://example.com"),
        call(url="https://example.com"),
    ]
    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_max_retries_zero(mock_asleep: Mock) -> None:
    """Test that max_retries=0 means only one attempt."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = AsyncMock(return_value=mock_response)

    with pytest.raises(HttpRequestError):
        await request_with_automatic_retry_async(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            max_retries=0,
        )

    mock_request_func.assert_called_once_with(url="https://example.com")
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_custom_status_forcelist(
    mock_asleep: Mock,
) -> None:
    """Test that custom status_forcelist is respected."""
    mock_response = Mock(spec=httpx.Response, status_code=400)  # 400: Not in default forcelist
    mock_request_func = AsyncMock(return_value=mock_response)

    with pytest.raises(HttpRequestError):
        await request_with_automatic_retry_async(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            max_retries=2,
            status_forcelist=(400, 503),
        )

    assert mock_request_func.call_args_list == [
        call(url="https://example.com"),
        call(url="https://example.com"),
        call(url="https://example.com"),
    ]
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_kwargs_passed_to_request_func(
    mock_request_func: AsyncMock, mock_asleep: Mock
) -> None:
    """Test that additional kwargs are passed to the request
    function."""
    await request_with_automatic_retry_async(
        url="https://example.com",
        method="POST",
        request_func=mock_request_func,
        json={"key": "value"},
        headers={"Authorization": "Bearer token"},
        timeout=30,
    )
    mock_request_func.assert_called_once_with(
        url="https://example.com",
        json={"key": "value"},
        headers={"Authorization": "Bearer token"},
        timeout=30,
    )
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_3xx_status_codes_succeed(
    mock_asleep: Mock,
) -> None:
    """Test that 3xx redirect codes are treated as success."""
    mock_response = Mock(spec=httpx.Response, status_code=301)
    mock_request_func = AsyncMock(return_value=mock_response)

    result = await request_with_automatic_retry_async(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
    )

    assert result == mock_response
    mock_request_func.assert_called_once_with(url="https://example.com")
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_http_request_error_attributes(
    mock_asleep: Mock,
) -> None:
    """Test that HttpRequestError contains correct attributes."""
    mock_response = Mock(spec=httpx.Response, status_code=502)
    mock_request_func = AsyncMock(return_value=mock_response)

    with pytest.raises(HttpRequestError) as exc_info:
        await request_with_automatic_retry_async(
            url="https://example.com/api",
            method="DELETE",
            request_func=mock_request_func,
            max_retries=1,
        )

    error = exc_info.value
    assert error.method == "DELETE"
    assert error.url == "https://example.com/api"
    assert error.status_code == 502
    assert error.response == mock_response
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
async def test_request_with_automatic_retry_async_timeout_exception_after_successful_attempts(
    mock_asleep: Mock,
) -> None:
    """Test timeout exception after some successful retries."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = AsyncMock(side_effect=[mock_response, httpx.TimeoutException("Timeout")])

    with pytest.raises(
        HttpRequestError, match=r"GET request to https://example.com timed out \(2 attempts\)"
    ):
        await request_with_automatic_retry_async(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            max_retries=1,
        )

    assert mock_request_func.call_args_list == [
        call(url="https://example.com"),
        call(url="https://example.com"),
    ]
    mock_asleep.assert_called_once_with(0.3)
