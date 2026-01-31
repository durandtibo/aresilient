r"""Unit tests for head_with_automatic_retry function."""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from aresilient import RETRY_STATUS_CODES, HttpRequestError, head_with_automatic_retry

TEST_URL = "https://api.example.com/resource"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200, headers={"Content-Length": "1024"})


@pytest.fixture
def mock_client(mock_response: httpx.Response) -> httpx.Client:
    return Mock(spec=httpx.Client, head=Mock(return_value=mock_response))


##############################################
#    Tests for head_with_automatic_retry     #
##############################################


def test_head_with_automatic_retry_successful_head(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test successful HEAD request with custom client."""
    response = head_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 200
    mock_client.head.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_head_with_automatic_retry_successful_head_request_with_default_client(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test successful HEAD request on first attempt."""
    with patch("httpx.Client.head", return_value=mock_response):
        response = head_with_automatic_retry(TEST_URL)

    assert response.status_code == 200
    mock_sleep.assert_not_called()


def test_head_with_automatic_retry_with_retry_on_500(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test HEAD request retries on 500 status code."""
    # First attempt fails with 500, second succeeds
    failed_response = Mock(spec=httpx.Response, status_code=500, headers={})
    success_response = Mock(spec=httpx.Response, status_code=200, headers={"Content-Length": "2048"})
    mock_client.head.side_effect = [failed_response, success_response]

    response = head_with_automatic_retry(TEST_URL, client=mock_client)

    assert response.status_code == 200
    assert mock_client.head.call_count == 2
    mock_sleep.assert_called_once()


def test_head_with_automatic_retry_with_non_retryable_status(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test HEAD request fails immediately on 404 (non-retryable)."""
    failed_response = Mock(spec=httpx.Response, status_code=404, headers={})
    mock_client.head.return_value = failed_response

    with pytest.raises(HttpRequestError) as exc_info:
        head_with_automatic_retry(TEST_URL, client=mock_client)

    assert exc_info.value.status_code == 404
    mock_client.head.assert_called_once()
    mock_sleep.assert_not_called()


def test_head_with_automatic_retry_with_max_retries_exhausted(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test HEAD request fails after max retries exhausted."""
    failed_response = Mock(spec=httpx.Response, status_code=503, headers={})
    mock_client.head.return_value = failed_response

    with pytest.raises(HttpRequestError) as exc_info:
        head_with_automatic_retry(TEST_URL, client=mock_client, max_retries=2)

    assert exc_info.value.status_code == 503
    assert mock_client.head.call_count == 3  # 1 initial + 2 retries
    assert mock_sleep.call_count == 2


def test_head_with_automatic_retry_with_custom_headers(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test HEAD request with custom headers."""
    response = head_with_automatic_retry(
        TEST_URL, client=mock_client, headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 200
    mock_client.head.assert_called_once_with(
        url=TEST_URL, headers={"Authorization": "Bearer token"}
    )
    mock_sleep.assert_not_called()


def test_head_with_automatic_retry_parameter_validation() -> None:
    """Test parameter validation for HEAD requests."""
    with pytest.raises(ValueError, match="max_retries must be >= 0"):
        head_with_automatic_retry(TEST_URL, max_retries=-1)

    with pytest.raises(ValueError, match="backoff_factor must be >= 0"):
        head_with_automatic_retry(TEST_URL, backoff_factor=-0.5)

    with pytest.raises(ValueError, match="jitter_factor must be >= 0"):
        head_with_automatic_retry(TEST_URL, jitter_factor=-0.1)

    with pytest.raises(ValueError, match="timeout must be > 0"):
        head_with_automatic_retry(TEST_URL, timeout=0)
