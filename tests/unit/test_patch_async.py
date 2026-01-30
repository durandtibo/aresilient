r"""Unit tests for patch_with_automatic_retry_async function."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, call, patch

import httpx
import pytest

from aresnet import (
    RETRY_STATUS_CODES,
    HttpRequestError,
    patch_with_automatic_retry_async,
)

TEST_URL = "https://api.example.com/resource/123"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200)


@pytest.fixture
def mock_client(mock_response: httpx.Response) -> httpx.AsyncClient:
    return Mock(
        spec=httpx.AsyncClient,
        patch=AsyncMock(return_value=mock_response),
        aclose=AsyncMock(),
    )


##################################################
#     Tests for patch_with_automatic_retry_async     #
##################################################


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_successful_patch(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test successful PATCH request with custom client."""
    response = await patch_with_automatic_retry_async(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(url=TEST_URL)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_successful_patch_request_with_default_client(
    mock_response: httpx.Response, mock_asleep: Mock
) -> None:
    """Test successful PATCH request on first attempt."""
    with patch("httpx.AsyncClient.patch", new_callable=AsyncMock, return_value=mock_response):
        response = await patch_with_automatic_retry_async(TEST_URL)

    assert response.status_code == 200
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_patch_with_json_payload(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test PATCH request with JSON data."""
    response = await patch_with_automatic_retry_async(
        TEST_URL, json={"status": "updated"}, client=mock_client
    )

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(url=TEST_URL, json={"status": "updated"})
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_retry_on_500_status(
    mock_response: httpx.Response, mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test retry logic for 500 status code."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=500)
    mock_client.patch.side_effect = [mock_response_fail, mock_response]

    response = await patch_with_automatic_retry_async(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_retry_on_503_status(
    mock_response: httpx.Response, mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test retry logic for 503 status code."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client.patch.side_effect = [mock_response_fail, mock_response]

    response = await patch_with_automatic_retry_async(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_max_retries_exceeded(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that HttpRequestError is raised when max retries
    exceeded."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_client.patch.return_value = mock_response

    with pytest.raises(HttpRequestError) as exc_info:
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=2)

    assert exc_info.value.status_code == 503
    assert "failed with status 503 after 3 attempts" in str(exc_info.value)
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_non_retryable_status_code(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that 404 status code is not retried."""
    mock_response = Mock(spec=httpx.Response, status_code=404)
    mock_client.patch.return_value = mock_response

    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api\.example\.com/resource/123 failed with status 404",
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_exponential_backoff(
    mock_response: httpx.Response, mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test exponential backoff timing."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client.patch.side_effect = [mock_response_fail, mock_response_fail, mock_response]

    await patch_with_automatic_retry_async(TEST_URL, client=mock_client, backoff_factor=2.0)

    # Should have slept twice (after 1st and 2nd failures)
    assert mock_asleep.call_args_list == [call(2.0), call(4.0)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_timeout_exception(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test handling of timeout exception."""
    mock_client.patch.side_effect = httpx.TimeoutException("Request timeout")

    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 timed out \(1 attempts\)",
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=0)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_timeout_exception_with_retries(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test timeout exception with retries."""
    mock_client.patch.side_effect = httpx.TimeoutException("Request timeout")

    with (
        pytest.raises(
            HttpRequestError,
            match=r"PATCH request to https://api.example.com/resource/123 timed out \(3 attempts\)",
        ),
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=2)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_request_error(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test handling of general request errors."""
    mock_client.patch.side_effect = httpx.RequestError("Connection failed")

    with pytest.raises(
        HttpRequestError,
        match=(
            r"PATCH request to https://api.example.com/resource/123 failed after 1 attempts: "
            r"Connection failed"
        ),
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=0)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_request_error_with_retries(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test handling of general request errors."""
    mock_client.patch.side_effect = httpx.RequestError("Connection failed")

    with pytest.raises(HttpRequestError, match=r"failed after 3 attempts"):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=2)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_negative_max_retries() -> None:
    """Test that negative max_retries raises ValueError."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        await patch_with_automatic_retry_async(TEST_URL, max_retries=-1)


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_negative_backoff_factor() -> None:
    """Test that negative backoff_factor raises ValueError."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0"):
        await patch_with_automatic_retry_async(TEST_URL, backoff_factor=-1.0)


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_zero_max_retries(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test with zero retries - should only try once."""
    mock_client.patch.return_value = Mock(spec=httpx.Response, status_code=503)

    with pytest.raises(
        HttpRequestError,
        match=rf"PATCH request to {TEST_URL} failed with status 503 after 1 attempts",
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=0)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_custom_status_forcelist(
    mock_response: httpx.Response, mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test custom status codes for retry."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=404)
    mock_client.patch.side_effect = [mock_response_fail, mock_response]

    response = await patch_with_automatic_retry_async(
        TEST_URL, client=mock_client, status_forcelist=(404,)
    )

    assert response.status_code == 200
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", RETRY_STATUS_CODES)
async def test_patch_with_automatic_retry_async_default_retry_status_codes(
    mock_response: httpx.Response,
    mock_client: httpx.AsyncClient,
    mock_asleep: Mock,
    status_code: int,
) -> None:
    """Test that default retry status codes trigger retries."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=status_code)
    mock_client.patch.side_effect = [mock_response_fail, mock_response]

    response = await patch_with_automatic_retry_async(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_client_close_when_owns_client(
    mock_client: httpx.AsyncClient,
) -> None:
    """Test that client is closed when created internally."""
    with patch("httpx.AsyncClient", return_value=mock_client):
        await patch_with_automatic_retry_async(TEST_URL)
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_client_not_closed_when_provided(
    mock_client: httpx.AsyncClient,
) -> None:
    """Test that external client is not closed."""
    await patch_with_automatic_retry_async(TEST_URL, client=mock_client)
    mock_client.aclose.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_custom_timeout(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test custom timeout parameter."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = mock_client
        await patch_with_automatic_retry_async(TEST_URL, timeout=30.0)

    mock_client_class.assert_called_once_with(timeout=30.0)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_all_retries_with_429(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test retry behavior with 429 Too Many Requests."""
    mock_response = Mock(spec=httpx.Response, status_code=429)
    mock_client.patch.return_value = mock_response

    with pytest.raises(HttpRequestError) as exc_info:
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=1)

    assert exc_info.value.status_code == 429
    assert "failed with status 429 after 2 attempts" in str(exc_info.value)
    assert mock_asleep.call_args_list == [call(0.3)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_with_httpx_timeout_object(
    mock_response: httpx.Response, mock_asleep: Mock
) -> None:
    """Test PATCH request with httpx.Timeout object."""
    timeout_config = httpx.Timeout(10.0, connect=5.0)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_instance = Mock()
        mock_client_instance.patch = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        mock_client_class.return_value = mock_client_instance
        response = await patch_with_automatic_retry_async(TEST_URL, timeout=timeout_config)

    mock_client_class.assert_called_once_with(timeout=timeout_config)
    assert response.status_code == 200
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_recovery_after_multiple_failures(
    mock_response: httpx.Response, mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test successful recovery after multiple transient failures."""
    mock_client.patch.side_effect = [
        Mock(spec=httpx.Response, status_code=429),
        Mock(spec=httpx.Response, status_code=503),
        Mock(spec=httpx.Response, status_code=500),
        mock_response,
    ]

    response = await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=5)

    assert response.status_code == 200
    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [200, 201, 202, 204, 206])
async def test_patch_with_automatic_retry_async_successful_2xx_status_codes(
    mock_asleep: Mock, mock_client: httpx.AsyncClient, status_code: int
) -> None:
    """Test that various 2xx status codes are considered successful."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_client.patch.return_value = mock_response

    response = await patch_with_automatic_retry_async(TEST_URL, client=mock_client)

    assert response.status_code == status_code
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [301, 302, 303, 304, 307, 308])
async def test_patch_with_automatic_retry_async_successful_3xx_status_codes(
    mock_asleep: Mock, mock_client: httpx.AsyncClient, status_code: int
) -> None:
    """Test that 3xx redirect status codes are considered successful."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_client.patch.return_value = mock_response

    response = await patch_with_automatic_retry_async(TEST_URL, client=mock_client)

    assert response.status_code == status_code
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_with_headers(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test PATCH request with custom headers."""
    response = await patch_with_automatic_retry_async(
        TEST_URL,
        client=mock_client,
        headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(
        url=TEST_URL,
        headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
    )
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_with_data(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test PATCH request with form data."""
    response = await patch_with_automatic_retry_async(
        TEST_URL, client=mock_client, data={"field1": "value1", "field2": "value2"}
    )

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(
        url=TEST_URL, data={"field1": "value1", "field2": "value2"}
    )
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_error_message_includes_url(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that error message includes the URL."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_client.patch.return_value = mock_response

    with pytest.raises(
        HttpRequestError,
        match=(
            r"PATCH request to https://api.example.com/resource/123 failed with status 503 "
            r"after 1 attempts"
        ),
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=0)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_client_close_on_exception(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that client is closed even when exception occurs."""
    mock_client.patch.side_effect = httpx.TimeoutException("Timeout")

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        pytest.raises(
            HttpRequestError,
            match=r"PATCH request to https://api.example.com/resource/123 timed out \(1 attempts\)",
        ),
    ):
        await patch_with_automatic_retry_async(TEST_URL, max_retries=0)

    mock_client.aclose.assert_called_once()
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_mixed_error_and_status_failures(
    mock_response: httpx.Response, mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test recovery from mix of errors and retryable status codes."""
    mock_client.patch.side_effect = [
        httpx.RequestError("Network error"),
        Mock(spec=httpx.Response, status_code=502),
        httpx.TimeoutException("Timeout"),
        mock_response,
    ]

    response = await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=5)

    assert response.status_code == 200
    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_network_error(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that NetworkError is retried appropriately."""
    mock_client.patch.side_effect = httpx.NetworkError("Network unreachable")
    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 failed after 4 attempts",
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_read_error(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that ReadError is retried appropriately."""
    mock_client.patch.side_effect = httpx.ReadError("Connection broken")
    with (
        pytest.raises(
            HttpRequestError,
            match=r"PATCH request to https://api.example.com/resource/123 failed after 4 attempts",
        ),
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_write_error(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that WriteError is retried appropriately."""
    mock_client.patch.side_effect = httpx.WriteError("Write failed")

    with (
        pytest.raises(
            HttpRequestError,
            match=r"PATCH request to https://api.example.com/resource/123 failed after 4 attempts",
        ),
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_connect_timeout(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that ConnectTimeout is retried appropriately."""
    mock_client.patch.side_effect = httpx.ConnectTimeout("Connection timeout")

    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 timed out \(4 attempts\)",
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_read_timeout(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that ReadTimeout is retried appropriately."""
    mock_client.patch.side_effect = httpx.ReadTimeout("Read timeout")

    with (
        pytest.raises(
            HttpRequestError,
            match=r"PATCH request to https://api.example.com/resource/123 timed out \(4 attempts\)",
        ),
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_pool_timeout(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that PoolTimeout is retried appropriately."""
    mock_client.patch.side_effect = httpx.PoolTimeout("Connection pool exhausted")

    with (
        pytest.raises(
            HttpRequestError,
            match=r"PATCH request to https://api.example.com/resource/123 timed out \(4 attempts\)",
        ),
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_proxy_error(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that ProxyError is retried appropriately."""
    mock_client.patch.side_effect = httpx.ProxyError("Proxy connection failed")

    with (
        pytest.raises(
            HttpRequestError,
            match=r"PATCH request to https://api.example.com/resource/123 failed after 4 attempts",
        ),
    ):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=3)

    assert mock_asleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_validation_negative_max_retries(
    mock_client: httpx.AsyncClient,
) -> None:
    """Test that negative max_retries raises ValueError."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, max_retries=-1)


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_validation_negative_backoff_factor(
    mock_client: httpx.AsyncClient,
) -> None:
    """Test that negative backoff_factor raises ValueError."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0"):
        await patch_with_automatic_retry_async(TEST_URL, client=mock_client, backoff_factor=-0.5)
