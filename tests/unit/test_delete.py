from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresnet import HttpRequestError, delete_with_automatic_retry

TEST_URL = "https://api.example.com/resource/123"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=204)


@pytest.fixture
def mock_client(mock_response: httpx.Response) -> httpx.Client:
    return Mock(spec=httpx.Client, delete=Mock(return_value=mock_response))


def test_delete_with_automatic_retry_successful_delete(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test successful DELETE request with custom client."""
    response = delete_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 204
    mock_client.delete.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_delete_with_automatic_retry_retry_on_503_status(
    mock_response: httpx.Response, mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test retry logic for 503 status code."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client.delete.side_effect = [mock_response_fail, mock_response]

    response = delete_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 204
    mock_sleep.assert_called_once_with(0.3)


def test_delete_with_automatic_retry_max_retries_exceeded(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that HttpRequestError is raised when max retries
    exceeded."""
    mock_response = Mock(spec=httpx.Response, status_code=500)
    mock_client.delete.return_value = mock_response

    with pytest.raises(HttpRequestError) as exc_info:
        delete_with_automatic_retry(TEST_URL, client=mock_client, max_retries=2)

    assert exc_info.value.status_code == 500
    assert "failed with status 500 after 3 attempts" in str(exc_info.value)


def test_delete_with_automatic_retry_validates_negative_max_retries(
    mock_client: httpx.Client,
) -> None:
    """Test that ValueError is raised for negative max_retries."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        delete_with_automatic_retry(TEST_URL, client=mock_client, max_retries=-1)


def test_delete_with_automatic_retry_validates_negative_backoff_factor(
    mock_client: httpx.Client,
) -> None:
    """Test that ValueError is raised for negative backoff_factor."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0"):
        delete_with_automatic_retry(TEST_URL, client=mock_client, backoff_factor=-0.5)
