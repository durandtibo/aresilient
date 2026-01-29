from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresnet import HttpRequestError, patch_with_automatic_retry

TEST_URL = "https://api.example.com/resource/123"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200)


@pytest.fixture
def mock_client(mock_response: httpx.Response) -> httpx.Client:
    return Mock(spec=httpx.Client, patch=Mock(return_value=mock_response))


def test_patch_with_automatic_retry_successful_patch(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test successful PATCH request with custom client."""
    response = patch_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_with_json_payload(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test PATCH request with JSON data."""
    response = patch_with_automatic_retry(TEST_URL, json={"status": "updated"}, client=mock_client)

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(url=TEST_URL, json={"status": "updated"})
    mock_sleep.assert_not_called()


def test_patch_with_automatic_retry_retry_on_429_status(
    mock_response: httpx.Response, mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test retry logic for 429 status code."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=429)
    mock_client.patch.side_effect = [mock_response_fail, mock_response]

    response = patch_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_sleep.assert_called_once_with(0.3)


def test_patch_with_automatic_retry_max_retries_exceeded(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that HttpRequestError is raised when max retries
    exceeded."""
    mock_response = Mock(spec=httpx.Response, status_code=502)
    mock_client.patch.return_value = mock_response

    with pytest.raises(HttpRequestError) as exc_info:
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=2)

    assert exc_info.value.status_code == 502
    assert "failed with status 502 after 3 attempts" in str(exc_info.value)


def test_patch_with_automatic_retry_validates_negative_max_retries(
    mock_client: httpx.Client,
) -> None:
    """Test that ValueError is raised for negative max_retries."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        patch_with_automatic_retry(TEST_URL, client=mock_client, max_retries=-1)


def test_patch_with_automatic_retry_validates_negative_backoff_factor(
    mock_client: httpx.Client,
) -> None:
    """Test that ValueError is raised for negative backoff_factor."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0"):
        patch_with_automatic_retry(TEST_URL, client=mock_client, backoff_factor=-0.5)
