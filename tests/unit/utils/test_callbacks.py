from __future__ import annotations

from unittest.mock import Mock, patch

import httpx

from aresilient.utils import invoke_on_request, invoke_on_retry, invoke_on_success

TEST_URL = "https://api.example.com/data"


################################################
#     Tests for invoke_on_request             #
################################################


def test_invoke_on_request_with_none_callback() -> None:
    """Test that invoke_on_request does nothing when callback is
    None."""

    # Should not raise any errors
    invoke_on_request(
        None,
        url=TEST_URL,
        method="GET",
        attempt=0,
        max_retries=3,
    )


def test_invoke_on_request_calls_callback() -> None:
    """Test that invoke_on_request calls the provided callback."""

    mock_callback = Mock()
    invoke_on_request(
        mock_callback,
        url=TEST_URL,
        method="POST",
        attempt=1,
        max_retries=5,
    )

    mock_callback.assert_called_once()
    call_args = mock_callback.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "POST"
    assert call_args.attempt == 2  # 0-indexed to 1-indexed
    assert call_args.max_retries == 5


def test_invoke_on_request_converts_attempt_to_1_indexed() -> None:
    """Test that attempt is converted from 0-indexed to 1-indexed."""

    mock_callback = Mock()
    invoke_on_request(
        mock_callback,
        url=TEST_URL,
        method="GET",
        attempt=0,
        max_retries=3,
    )

    call_args = mock_callback.call_args[0][0]
    assert call_args.attempt == 1


################################################
#     Tests for invoke_on_success             #
################################################


def test_invoke_on_success_with_none_callback() -> None:
    """Test that invoke_on_success does nothing when callback is
    None."""

    mock_response = Mock(spec=httpx.Response)
    invoke_on_success(
        None,
        url=TEST_URL,
        method="GET",
        attempt=0,
        max_retries=3,
        response=mock_response,
        start_time=100.0,
    )


def test_invoke_on_success_calls_callback() -> None:
    """Test that invoke_on_success calls the provided callback."""

    mock_callback = Mock()
    mock_response = Mock(spec=httpx.Response)

    with patch("aresilient.utils.callbacks.time.time", return_value=105.5):
        invoke_on_success(
            mock_callback,
            url=TEST_URL,
            method="PUT",
            attempt=2,
            max_retries=5,
            response=mock_response,
            start_time=100.0,
        )

    mock_callback.assert_called_once()
    call_args = mock_callback.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "PUT"
    assert call_args.attempt == 3  # 0-indexed to 1-indexed
    assert call_args.max_retries == 5
    assert call_args.response == mock_response
    assert call_args.total_time == 5.5


def test_invoke_on_success_calculates_total_time() -> None:
    """Test that total_time is calculated correctly."""

    mock_callback = Mock()
    mock_response = Mock(spec=httpx.Response)

    with patch("aresilient.utils.callbacks.time.time", return_value=110.0):
        invoke_on_success(
            mock_callback,
            url=TEST_URL,
            method="GET",
            attempt=0,
            max_retries=3,
            response=mock_response,
            start_time=100.0,
        )

    call_args = mock_callback.call_args[0][0]
    assert call_args.total_time == 10.0


################################################
#     Tests for invoke_on_retry               #
################################################


def test_invoke_on_retry_with_none_callback() -> None:
    """Test that invoke_on_retry does nothing when callback is None."""

    invoke_on_retry(
        None,
        url=TEST_URL,
        method="GET",
        attempt=0,
        max_retries=3,
        sleep_time=1.5,
        last_error=None,
        last_status_code=None,
    )


def test_invoke_on_retry_calls_callback_with_error() -> None:
    """Test that invoke_on_retry calls callback with error info."""

    mock_callback = Mock()
    error = Exception("Test error")

    invoke_on_retry(
        mock_callback,
        url=TEST_URL,
        method="DELETE",
        attempt=1,
        max_retries=5,
        sleep_time=2.5,
        last_error=error,
        last_status_code=None,
    )

    mock_callback.assert_called_once()
    call_args = mock_callback.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "DELETE"
    assert call_args.attempt == 3  # Next attempt: 1 + 2
    assert call_args.max_retries == 5
    assert call_args.wait_time == 2.5
    assert call_args.error == error
    assert call_args.status_code is None


def test_invoke_on_retry_calls_callback_with_status_code() -> None:
    """Test that invoke_on_retry calls callback with status code."""

    mock_callback = Mock()

    invoke_on_retry(
        mock_callback,
        url=TEST_URL,
        method="GET",
        attempt=0,
        max_retries=3,
        sleep_time=0.5,
        last_error=None,
        last_status_code=503,
    )

    call_args = mock_callback.call_args[0][0]
    assert call_args.status_code == 503
    assert call_args.error is None
    assert call_args.attempt == 2  # Next attempt: 0 + 2


def test_invoke_on_retry_calculates_next_attempt() -> None:
    """Test that next attempt number is calculated correctly."""

    mock_callback = Mock()

    invoke_on_retry(
        mock_callback,
        url=TEST_URL,
        method="GET",
        attempt=3,
        max_retries=10,
        sleep_time=1.0,
        last_error=None,
        last_status_code=500,
    )

    call_args = mock_callback.call_args[0][0]
    assert call_args.attempt == 5  # Next attempt: 3 + 2
