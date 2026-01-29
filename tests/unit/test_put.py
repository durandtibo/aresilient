from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresnet import HttpRequestError, put_with_automatic_retry

TEST_URL = "https://api.example.com/resource"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200)


@pytest.fixture
def mock_client(mock_response: httpx.Response) -> httpx.Client:
    return Mock(spec=httpx.Client, put=Mock(return_value=mock_response))


def test_put_with_automatic_retry_successful_put(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test successful PUT request with custom client."""
    response = put_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_client.put.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_put_with_automatic_retry_with_json_payload(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test PUT request with JSON data."""
    response = put_with_automatic_retry(TEST_URL, json={"key": "value"}, client=mock_client)

    assert response.status_code == 200
    mock_client.put.assert_called_once_with(url=TEST_URL, json={"key": "value"})
    mock_sleep.assert_not_called()


def test_put_with_automatic_retry_retry_on_500_status(
    mock_response: httpx.Response, mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test retry logic for 500 status code."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=500)
    mock_client.put.side_effect = [mock_response_fail, mock_response]

    response = put_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_sleep.assert_called_once_with(0.3)


def test_put_with_automatic_retry_max_retries_exceeded(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that HttpRequestError is raised when max retries
    exceeded."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_client.put.return_value = mock_response

    with pytest.raises(HttpRequestError) as exc_info:
        put_with_automatic_retry(TEST_URL, client=mock_client, max_retries=2)

    assert exc_info.value.status_code == 503
    assert "failed with status 503 after 3 attempts" in str(exc_info.value)


def test_put_with_automatic_retry_validates_negative_max_retries(mock_client: httpx.Client) -> None:
    """Test that ValueError is raised for negative max_retries."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        put_with_automatic_retry(TEST_URL, client=mock_client, max_retries=-1)


def test_put_with_automatic_retry_validates_negative_backoff_factor(
    mock_client: httpx.Client,
) -> None:
    """Test that ValueError is raised for negative backoff_factor."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0"):
        put_with_automatic_retry(TEST_URL, client=mock_client, backoff_factor=-0.5)
