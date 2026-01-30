r"""Unit tests for patch_with_automatic_retry function."""

from __future__ import annotations

from unittest.mock import Mock, call, patch

import httpx
import pytest

from aresnet import RETRY_STATUS_CODES, HttpRequestError, patch_with_automatic_retry

TEST_URL = "https://api.example.com/resource/123"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200)


@pytest.fixture
def mock_client(mock_response: httpx.Response) -> httpx.Client:
    return Mock(spec=httpx.Client, patch=Mock(return_value=mock_response))


##################################################
#     Tests for patch_with_automatic_retry     #
##################################################


def test_patch_with_automatic_retry_successful_patch(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test successful PATCH request with custom client."""
    response = patch_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_successful_patch_request_with_default_client(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test successful PATCH request on first attempt."""
    with patch("httpx.Client.patch", return_value=mock_response):
        response = patch_with_automatic_retry(TEST_URL)

    assert response.status_code == 200
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_with_json_payload(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test PATCH request with JSON data."""
    response = patch_with_automatic_retry(TEST_URL, json={"status": "updated"}, client=mock_client)

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(url=TEST_URL, json={"status": "updated"})
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_retry_on_500_status(
    mock_response: httpx.Response, mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test retry logic for 500 status code."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=500)
    mock_client.patch.side_effect = [mock_response_fail, mock_response]

    response = patch_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_sleep.assert_called_once_with(0.3)


def test_patch_with_automatic_retry_retry_on_503_status(
    mock_response: httpx.Response, mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test retry logic for 503 status code."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client.patch.side_effect = [mock_response_fail, mock_response]

    response = patch_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_sleep.assert_called_once_with(0.3)


def test_patch_with_automatic_retry_max_retries_exceeded(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that HttpRequestError is raised when max retries
    exceeded."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_client.patch.return_value = mock_response

    with pytest.raises(HttpRequestError) as exc_info:
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=2)

    assert exc_info.value.status_code == 503
    assert "failed with status 503 after 3 attempts" in str(exc_info.value)
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_patch_with_automatic_retry_non_retryable_status_code(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that 404 status code is not retried."""
    mock_response = Mock(spec=httpx.Response, status_code=404)
    mock_client.patch.return_value = mock_response

    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api\.example\.com/resource/123 failed with status 404",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client)

    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_exponential_backoff(
    mock_response: httpx.Response, mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test exponential backoff timing."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client.patch.side_effect = [mock_response_fail, mock_response_fail, mock_response]

    patch_with_automatic_retry(TEST_URL, client=mock_client, backoff_factor=2.0)

    # Should have slept twice (after 1st and 2nd failures)
    assert mock_sleep.call_args_list == [call(2.0), call(4.0)]


def test_patch_with_automatic_retry_timeout_exception(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test handling of timeout exception."""
    mock_client.patch.side_effect = httpx.TimeoutException("Request timeout")

    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 timed out \(1 attempts\)",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=0)

    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_timeout_exception_with_retries(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test timeout exception with retries."""
    mock_client.patch.side_effect = httpx.TimeoutException("Request timeout")

    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 timed out \(3 attempts\)",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=2)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_patch_with_automatic_retry_request_error(
    mock_client: httpx.Client, mock_sleep: Mock
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
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=0)

    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_request_error_with_retries(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test handling of general request errors with retries."""
    mock_client.patch.side_effect = httpx.RequestError("Connection failed")

    with pytest.raises(HttpRequestError, match=r"failed after 3 attempts"):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=2)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_patch_with_automatic_retry_validates_negative_max_retries() -> None:
    """Test that ValueError is raised for negative max_retries."""
    with pytest.raises(ValueError, match="max_retries must be >= 0"):
        patch_with_automatic_retry(TEST_URL, max_retries=-1)


def test_patch_with_automatic_retry_validates_negative_backoff_factor() -> None:
    """Test that ValueError is raised for negative backoff_factor."""
    with pytest.raises(ValueError, match="backoff_factor must be >= 0"):
        patch_with_automatic_retry(TEST_URL, backoff_factor=-1.0)


def test_patch_with_automatic_retry_zero_max_retries(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test with zero retries - should only try once."""
    mock_client.patch.return_value = Mock(spec=httpx.Response, status_code=503)

    with pytest.raises(
        HttpRequestError,
        match=rf"PATCH request to {TEST_URL} failed with status 503 after 1 attempts",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=0)

    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_custom_status_forcelist(
    mock_response: httpx.Response, mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test custom status codes for retry."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=404)
    mock_client.patch.side_effect = [mock_response_fail, mock_response]

    response = patch_with_automatic_retry(TEST_URL, client=mock_client, status_forcelist=(404,))

    assert response.status_code == 200
    mock_sleep.assert_called_once_with(0.3)


@pytest.mark.parametrize("status_code", RETRY_STATUS_CODES)
def test_patch_with_automatic_retry_default_retry_status_codes(
    mock_response: httpx.Response, mock_client: httpx.Client, mock_sleep: Mock, status_code: int
) -> None:
    """Test default retry status codes."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=status_code)
    mock_client.patch.side_effect = [mock_response_fail, mock_response]

    response = patch_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_sleep.assert_called_once_with(0.3)


def test_patch_with_automatic_retry_client_close_when_owns_client(
    mock_client: httpx.Client,
) -> None:
    """Test that client is closed when created internally."""
    with patch("httpx.Client", return_value=mock_client):
        patch_with_automatic_retry(TEST_URL)
    mock_client.close.assert_called_once()


def test_patch_with_automatic_retry_client_not_closed_when_provided(
    mock_client: httpx.Client,
) -> None:
    """Test that external client is not closed."""
    patch_with_automatic_retry(TEST_URL, client=mock_client)
    mock_client.close.assert_not_called()


def test_patch_with_automatic_retry_custom_timeout(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test custom timeout parameter."""
    with patch("httpx.Client") as mock_client_class:
        mock_client_class.return_value = mock_client
        patch_with_automatic_retry(TEST_URL, timeout=30.0)

    mock_client_class.assert_called_once_with(timeout=30.0)
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_all_retries_with_429(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test retry behavior with 429 Too Many Requests."""
    mock_response = Mock(spec=httpx.Response, status_code=429)
    mock_client.patch.return_value = mock_response

    with pytest.raises(HttpRequestError) as exc_info:
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=1)

    assert exc_info.value.status_code == 429
    assert "failed with status 429 after 2 attempts" in str(exc_info.value)
    assert mock_sleep.call_args_list == [call(0.3)]


def test_patch_with_automatic_retry_with_httpx_timeout_object(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test PATCH request with httpx.Timeout object."""
    timeout_config = httpx.Timeout(10.0, connect=5.0)

    with patch("httpx.Client") as mock_client_class:
        mock_client_instance = Mock()
        mock_client_instance.patch = Mock(return_value=mock_response)
        mock_client_instance.close = Mock()
        mock_client_class.return_value = mock_client_instance
        response = patch_with_automatic_retry(TEST_URL, timeout=timeout_config)

    mock_client_class.assert_called_once_with(timeout=timeout_config)
    assert response.status_code == 200
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_recovery_after_multiple_failures(
    mock_response: httpx.Response, mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test successful recovery after multiple transient failures."""
    mock_client.patch.side_effect = [
        Mock(spec=httpx.Response, status_code=429),
        Mock(spec=httpx.Response, status_code=503),
        Mock(spec=httpx.Response, status_code=500),
        mock_response,
    ]

    response = patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=5)

    assert response.status_code == 200
    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.parametrize("status_code", [200, 201, 202, 204, 206])
def test_patch_with_automatic_retry_successful_2xx_status_codes(
    mock_sleep: Mock, mock_client: httpx.Client, status_code: int
) -> None:
    """Test that various 2xx status codes are considered successful."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_client.patch.return_value = mock_response

    response = patch_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == status_code
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("status_code", [301, 302, 303, 304, 307, 308])
def test_patch_with_automatic_retry_successful_3xx_status_codes(
    mock_sleep: Mock, mock_client: httpx.Client, status_code: int
) -> None:
    """Test that 3xx redirect status codes are considered successful."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_client.patch.return_value = mock_response

    response = patch_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == status_code
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_with_headers(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test PATCH request with custom headers."""
    response = patch_with_automatic_retry(
        TEST_URL,
        client=mock_client,
        headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(
        url=TEST_URL,
        headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
    )
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_with_data(mock_client: httpx.Client, mock_sleep: Mock) -> None:
    """Test PATCH request with form data."""
    response = patch_with_automatic_retry(
        TEST_URL, client=mock_client, data={"field1": "value1", "field2": "value2"}
    )

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(
        url=TEST_URL, data={"field1": "value1", "field2": "value2"}
    )
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_error_message_includes_url(
    mock_client: httpx.Client, mock_sleep: Mock
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
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=0)

    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_client_close_on_exception(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that client is closed even when exception occurs."""
    mock_client.patch.side_effect = httpx.TimeoutException("Timeout")

    with (
        patch("httpx.Client", return_value=mock_client),
        pytest.raises(
            HttpRequestError,
            match=r"PATCH request to https://api.example.com/resource/123 timed out \(1 attempts\)",
        ),
    ):
        patch_with_automatic_retry(TEST_URL, max_retries=0)

    mock_client.close.assert_called_once()
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_mixed_error_and_status_failures(
    mock_response: httpx.Response, mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test recovery from mix of errors and retryable status codes."""
    mock_client.patch.side_effect = [
        httpx.RequestError("Network error"),
        Mock(spec=httpx.Response, status_code=502),
        httpx.TimeoutException("Timeout"),
        mock_response,
    ]

    response = patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=5)

    assert response.status_code == 200
    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_patch_with_automatic_retry_network_error(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that NetworkError is retried appropriately."""
    mock_client.patch.side_effect = httpx.NetworkError("Network unreachable")
    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 failed after 4 attempts",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=3)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_patch_with_automatic_retry_read_error(mock_client: httpx.Client, mock_sleep: Mock) -> None:
    """Test that ReadError is retried appropriately."""
    mock_client.patch.side_effect = httpx.ReadError("Read error")
    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 failed after 4 attempts",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=3)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_patch_with_automatic_retry_write_error(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that WriteError is retried appropriately."""
    mock_client.patch.side_effect = httpx.WriteError("Write error")
    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 failed after 4 attempts",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=3)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_patch_with_automatic_retry_connect_timeout(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that ConnectTimeout is retried appropriately."""
    mock_client.patch.side_effect = httpx.ConnectTimeout("Connection timeout")
    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 timed out \(4 attempts\)",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=3)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_patch_with_automatic_retry_read_timeout(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that ReadTimeout is retried appropriately."""
    mock_client.patch.side_effect = httpx.ReadTimeout("Read timeout")
    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 timed out \(4 attempts\)",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=3)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_patch_with_automatic_retry_pool_timeout(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that PoolTimeout is retried appropriately."""
    mock_client.patch.side_effect = httpx.PoolTimeout("Pool timeout")
    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 timed out \(4 attempts\)",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=3)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_patch_with_automatic_retry_proxy_error(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that ProxyError is retried appropriately."""
    mock_client.patch.side_effect = httpx.ProxyError("Proxy error")

    with pytest.raises(
        HttpRequestError,
        match=r"PATCH request to https://api.example.com/resource/123 failed after 4 attempts",
    ):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=3)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_patch_with_automatic_retry_validation_negative_max_retries(
    mock_client: httpx.Client,
) -> None:
    """Test that negative max_retries raises ValueError."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=-1)


def test_patch_with_automatic_retry_validation_negative_backoff_factor(
    mock_client: httpx.Client,
) -> None:
    """Test that negative backoff_factor raises ValueError."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0"):
        patch_with_automatic_retry(TEST_URL, client=mock_client, backoff_factor=-0.5)
