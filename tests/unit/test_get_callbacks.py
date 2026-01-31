r"""Unit tests for callback functionality in HTTP method wrappers (GET)."""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from aresilient import HttpRequestError, get_with_automatic_retry

TEST_URL = "https://api.example.com/data"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200)


@pytest.fixture
def mock_client(mock_response: httpx.Response) -> httpx.Client:
    return Mock(spec=httpx.Client, get=Mock(return_value=mock_response))


##################################################
#     Tests for get_with_automatic_retry         #
#     with callback functionality                #
##################################################


def test_get_on_request_callback(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that on_request callback is called for GET requests."""
    on_request_callback = Mock()

    response = get_with_automatic_retry(
        TEST_URL, client=mock_client, on_request=on_request_callback
    )

    assert response.status_code == 200
    on_request_callback.assert_called_once()
    call_args = on_request_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "GET"
    assert call_args["attempt"] == 1


def test_get_on_success_callback(
    mock_client: httpx.Client, mock_sleep: Mock
) -> None:
    """Test that on_success callback is called for successful GET requests."""
    on_success_callback = Mock()

    response = get_with_automatic_retry(
        TEST_URL, client=mock_client, on_success=on_success_callback
    )

    assert response.status_code == 200
    on_success_callback.assert_called_once()
    call_args = on_success_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "GET"
    assert call_args["response"].status_code == 200


def test_get_on_retry_callback(mock_response: httpx.Response, mock_sleep: Mock) -> None:
    """Test that on_retry callback is called when GET request is retried."""
    on_retry_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(
        spec=httpx.Client, get=Mock(side_effect=[mock_fail_response, mock_response])
    )

    response = get_with_automatic_retry(
        TEST_URL, client=mock_client, on_retry=on_retry_callback
    )

    assert response.status_code == 200
    on_retry_callback.assert_called_once()
    call_args = on_retry_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "GET"
    assert call_args["status_code"] == 503


def test_get_on_failure_callback(mock_sleep: Mock) -> None:
    """Test that on_failure callback is called when GET retries are exhausted."""
    on_failure_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client, get=Mock(return_value=mock_fail_response))

    with pytest.raises(HttpRequestError):
        get_with_automatic_retry(
            TEST_URL,
            client=mock_client,
            max_retries=2,
            on_failure=on_failure_callback,
        )

    on_failure_callback.assert_called_once()
    call_args = on_failure_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "GET"
    assert call_args["status_code"] == 503


def test_get_all_callbacks_together(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test that all callbacks work together for GET requests."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()

    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(
        spec=httpx.Client, get=Mock(side_effect=[mock_fail_response, mock_response])
    )

    response = get_with_automatic_retry(
        TEST_URL,
        client=mock_client,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_success=on_success_callback,
        on_failure=on_failure_callback,
    )

    assert response.status_code == 200
    assert on_request_callback.call_count == 2  # Two attempts
    on_retry_callback.assert_called_once()  # One retry
    on_success_callback.assert_called_once()  # One success
    on_failure_callback.assert_not_called()  # No failure


def test_get_callbacks_with_default_client(mock_sleep: Mock) -> None:
    """Test that callbacks work with default client (not provided)."""
    on_request_callback = Mock()
    on_success_callback = Mock()

    mock_response = Mock(spec=httpx.Response, status_code=200)
    with patch("httpx.Client.get", return_value=mock_response):
        response = get_with_automatic_retry(
            TEST_URL,
            on_request=on_request_callback,
            on_success=on_success_callback,
        )

    assert response.status_code == 200
    on_request_callback.assert_called_once()
    on_success_callback.assert_called_once()


def test_get_callbacks_with_timeout_error(mock_sleep: Mock) -> None:
    """Test that callbacks work when GET request times out."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_failure_callback = Mock()

    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_client = Mock(
        spec=httpx.Client,
        get=Mock(side_effect=[httpx.TimeoutException("timeout"), mock_response]),
    )

    response = get_with_automatic_retry(
        TEST_URL,
        client=mock_client,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_failure=on_failure_callback,
    )

    assert response.status_code == 200
    assert on_request_callback.call_count == 2
    on_retry_callback.assert_called_once()

    # Check that retry callback received error info
    retry_call_args = on_retry_callback.call_args[0][0]
    assert isinstance(retry_call_args["error"], httpx.TimeoutException)
