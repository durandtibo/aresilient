from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, call, patch

import pytest

from aresnet import HttpRequestError, post_with_automatic_retry

if TYPE_CHECKING:
    from collections.abc import Generator

import httpx


@pytest.fixture
def mock_sleep() -> Generator[Mock, None, None]:
    """Patch time.sleep to make tests run faster."""
    with patch("time.sleep", return_value=None) as mock:
        yield mock


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200)


@pytest.fixture
def mock_client(mock_response: httpx.Response) -> httpx.Client:
    return Mock(spec=httpx.Client, post=Mock(return_value=mock_response))


###############################################
#     Tests for post_with_automatic_retry     #
###############################################


def test_post_with_automatic_retry_successful_post_request(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test successful POST request on first attempt."""
    with patch("httpx.Client.post", return_value=mock_response):
        response = post_with_automatic_retry("https://api.example.com/data")

    mock_sleep.assert_not_called()
    assert response.status_code == 200


def test_post_with_automatic_retry_successful_post_with_custom_client(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test successful POST request with custom client."""
    response = post_with_automatic_retry("https://api.example.com/data", client=mock_client)

    mock_client.post.assert_called_once_with(url="https://api.example.com/data")
    mock_sleep.assert_not_called()
    assert response.status_code == 200


def test_post_with_automatic_retry_post_with_json_payload(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test POST request with JSON data."""
    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        response = post_with_automatic_retry("https://api.example.com/data", json={"key": "value"})

    mock_post.assert_called_once_with(url="https://api.example.com/data", json={"key": "value"})
    mock_sleep.assert_not_called()
    assert response.status_code == 200


def test_post_with_automatic_retry_retry_on_500_status(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test retry logic for 500 status code."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=500)

    with patch("httpx.Client.post", side_effect=[mock_response_fail, mock_response]):
        response = post_with_automatic_retry("https://api.example.com/data")

    assert response.status_code == 200
    mock_sleep.assert_called_once_with(0.3)


def test_post_with_automatic_retry_retry_on_503_status(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test retry logic for 503 status code."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)

    with patch("httpx.Client.post", side_effect=[mock_response_fail, mock_response]):
        response = post_with_automatic_retry("https://api.example.com/data")

    assert response.status_code == 200
    mock_sleep.assert_called_once_with(0.3)


def test_post_with_automatic_retry_max_retries_exceeded(mock_sleep: Mock) -> None:
    """Test that HttpRequestError is raised when max retries
    exceeded."""
    mock_response = Mock(spec=httpx.Response, status_code=503)

    with (
        patch("httpx.Client.post", return_value=mock_response),
        pytest.raises(HttpRequestError) as exc_info,
    ):
        post_with_automatic_retry("https://api.example.com/data", max_retries=2)

    assert exc_info.value.status_code == 503
    assert "failed with status 503 after 3 attempts" in str(exc_info.value)
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_post_with_automatic_retry_non_retryable_status_code(mock_sleep: Mock) -> None:
    """Test that 404 status code is not retried."""
    mock_response = Mock(spec=httpx.Response, status_code=404)
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=Mock(), response=mock_response
    )

    with (
        patch("httpx.Client.post", return_value=mock_response),
        pytest.raises(httpx.HTTPStatusError, match="Not Found"),
    ):
        post_with_automatic_retry("https://api.example.com/data")
    mock_sleep.assert_not_called()


def test_post_with_automatic_retry_exponential_backoff(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test exponential backoff timing."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)

    with patch(
        "httpx.Client.post", side_effect=[mock_response_fail, mock_response_fail, mock_response]
    ):
        post_with_automatic_retry("https://api.example.com/data", max_retries=3, backoff_factor=2.0)

    # Should have slept twice (after 1st and 2nd failures)
    assert mock_sleep.call_args_list == [call(2.0), call(4.0)]


def test_post_with_automatic_retry_timeout_exception(mock_sleep: Mock) -> None:
    """Test handling of timeout exception."""
    with (
        patch("httpx.Client.post", side_effect=httpx.TimeoutException("Request timeout")),
        pytest.raises(
            HttpRequestError,
            match=r"POST request to https://api.example.com/data timed out \(1 attempts\)",
        ),
    ):
        post_with_automatic_retry("https://api.example.com/data", max_retries=0)
    mock_sleep.assert_not_called()


def test_post_with_automatic_retry_timeout_exception_with_retries(mock_sleep: Mock) -> None:
    """Test timeout exception with retries."""
    with (
        patch("httpx.Client.post", side_effect=httpx.TimeoutException("Request timeout")),
        pytest.raises(
            HttpRequestError,
            match=r"POST request to https://api.example.com/data timed out \(3 attempts\)",
        ),
    ):
        post_with_automatic_retry("https://api.example.com/data", max_retries=2)
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_post_with_automatic_retry_request_error(mock_sleep: Mock) -> None:
    """Test handling of general request errors."""
    with (
        patch("httpx.Client.post", side_effect=httpx.RequestError("Connection failed")),
        pytest.raises(HttpRequestError, match="failed after 1 attempts"),
    ):
        post_with_automatic_retry("https://api.example.com/data", max_retries=0)
    mock_sleep.assert_not_called()


def test_post_with_automatic_retry_request_error_with_retries(mock_sleep: Mock) -> None:
    """Test handling of general request errors."""
    with (
        patch("httpx.Client.post", side_effect=httpx.RequestError("Connection failed")),
        pytest.raises(HttpRequestError, match="failed after 3 attempts"),
    ):
        post_with_automatic_retry("https://api.example.com/data", max_retries=2)
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_post_with_automatic_retry_negative_max_retries() -> None:
    """Test that negative max_retries raises ValueError."""
    with pytest.raises(ValueError, match="max_retries must be >= 0"):
        post_with_automatic_retry("https://api.example.com/data", max_retries=-1)


def test_post_with_automatic_retry_negative_backoff_factor() -> None:
    """Test that negative backoff_factor raises ValueError."""
    with pytest.raises(ValueError, match="backoff_factor must be >= 0"):
        post_with_automatic_retry("https://api.example.com/data", backoff_factor=-1.0)


def test_post_with_automatic_retry_zero_max_retries(mock_sleep: Mock) -> None:
    """Test with zero retries - should only try once."""
    mock_response = Mock(spec=httpx.Response, status_code=503)

    with (
        patch("httpx.Client.post", return_value=mock_response),
        pytest.raises(HttpRequestError, match="after 1 attempts"),
    ):
        post_with_automatic_retry("https://api.example.com/data", max_retries=0)
    mock_sleep.assert_not_called()


def test_post_with_automatic_retry_custom_status_forcelist(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test custom status codes for retry."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=404)

    with patch("httpx.Client.post", side_effect=[mock_response_fail, mock_response]):
        response = post_with_automatic_retry(
            "https://api.example.com/data", status_forcelist=(404,)
        )

    assert response.status_code == 200
    mock_sleep.assert_called_once_with(0.3)


def test_post_with_automatic_retry_client_close_when_owns_client(mock_client: httpx.Client) -> None:
    """Test that client is closed when created internally."""
    with patch("httpx.Client", return_value=mock_client):
        post_with_automatic_retry("https://api.example.com/data")
    mock_client.close.assert_called_once()


def test_post_with_automatic_retry_client_not_closed_when_provided(
    mock_client: httpx.Client,
) -> None:
    """Test that external client is not closed."""
    post_with_automatic_retry("https://api.example.com/data", client=mock_client)
    mock_client.close.assert_not_called()


def test_post_with_automatic_retry_custom_timeout(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test custom timeout parameter."""
    with patch("httpx.Client") as mock_client_class:
        mock_client_class.return_value = mock_client
        post_with_automatic_retry("https://api.example.com/data", timeout=30.0)

    mock_client_class.assert_called_once_with(timeout=30.0)
    mock_sleep.assert_not_called()


def test_post_with_automatic_retry_all_retries_with_429(mock_sleep: Mock) -> None:
    """Test retry behavior with 429 Too Many Requests."""
    mock_response = Mock(spec=httpx.Response, status_code=429)

    with (
        patch("httpx.Client.post", return_value=mock_response),
        pytest.raises(HttpRequestError) as exc_info,
    ):
        post_with_automatic_retry("https://api.example.com/data", max_retries=1)

    assert exc_info.value.status_code == 429
    assert "failed with status 429 after 2 attempts" in str(exc_info.value)
    assert mock_sleep.call_args_list == [call(0.3)]
