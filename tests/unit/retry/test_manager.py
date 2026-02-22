r"""Unit tests for callback manager."""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx

from aresilient.retry.config import CallbackConfig
from aresilient.retry.manager import CallbackManager


def test_callback_manager_creation() -> None:
    """Test CallbackManager initialization."""
    config = CallbackConfig()
    manager = CallbackManager(config)

    assert manager.callbacks is config


def test_on_request_callback_invoked() -> None:
    """Test on_request callback is invoked correctly."""
    mock_callback = Mock()
    config = CallbackConfig(on_request=mock_callback)
    manager = CallbackManager(config)

    manager.on_request(
        url="https://example.com",
        method="GET",
        attempt=0,
        max_retries=3,
    )

    mock_callback.assert_called_once()
    call_args = mock_callback.call_args[0][0]
    assert call_args.url == "https://example.com"
    assert call_args.method == "GET"
    assert call_args.attempt == 1  # Converted from 0-indexed to 1-indexed
    assert call_args.max_retries == 3


def test_on_request_callback_none() -> None:
    """Test on_request does nothing when callback is None."""
    config = CallbackConfig()
    manager = CallbackManager(config)

    # Should not raise
    manager.on_request(
        url="https://example.com",
        method="GET",
        attempt=0,
        max_retries=3,
    )


def test_on_retry_callback_invoked() -> None:
    """Test on_retry callback is invoked correctly."""
    mock_callback = Mock()
    config = CallbackConfig(on_retry=mock_callback)
    manager = CallbackManager(config)

    manager.on_retry(
        url="https://example.com",
        method="POST",
        attempt=0,
        max_retries=3,
        sleep_time=1.5,
        error=None,
        status_code=500,
    )

    mock_callback.assert_called_once()
    call_args = mock_callback.call_args[0][0]
    assert call_args.url == "https://example.com"
    assert call_args.method == "POST"
    assert call_args.attempt == 2  # Next attempt (0-indexed + 2)
    assert call_args.max_retries == 3
    assert call_args.wait_time == 1.5
    assert call_args.error is None
    assert call_args.status_code == 500


def test_on_retry_callback_none() -> None:
    """Test on_retry does nothing when callback is None."""
    config = CallbackConfig()
    manager = CallbackManager(config)

    # Should not raise
    manager.on_retry(
        url="https://example.com",
        method="GET",
        attempt=0,
        max_retries=3,
        sleep_time=1.5,
        error=None,
        status_code=None,
    )


def test_on_retry_callback_with_exception() -> None:
    """Test on_retry callback with exception."""
    mock_callback = Mock()
    config = CallbackConfig(on_retry=mock_callback)
    manager = CallbackManager(config)

    exc = httpx.TimeoutException("Timeout")
    manager.on_retry(
        url="https://example.com",
        method="GET",
        attempt=1,
        max_retries=3,
        sleep_time=2.0,
        error=exc,
        status_code=None,
    )

    mock_callback.assert_called_once()
    call_args = mock_callback.call_args[0][0]
    assert call_args.error is exc
    assert call_args.status_code is None


def test_on_success_callback_invoked() -> None:
    """Test on_success callback is invoked correctly."""
    mock_callback = Mock()
    config = CallbackConfig(on_success=mock_callback)
    manager = CallbackManager(config)

    mock_response = Mock(spec=httpx.Response)
    start_time = 100.0

    with patch("time.time", return_value=102.5):
        manager.on_success(
            url="https://example.com",
            method="PUT",
            attempt=2,
            max_retries=3,
            response=mock_response,
            start_time=start_time,
        )

    mock_callback.assert_called_once()
    call_args = mock_callback.call_args[0][0]
    assert call_args.url == "https://example.com"
    assert call_args.method == "PUT"
    assert call_args.attempt == 3  # Converted from 0-indexed to 1-indexed
    assert call_args.max_retries == 3
    assert call_args.response is mock_response
    assert call_args.total_time == 2.5


def test_on_success_callback_none() -> None:
    """Test on_success does nothing when callback is None."""
    config = CallbackConfig()
    manager = CallbackManager(config)

    mock_response = Mock(spec=httpx.Response)

    # Should not raise
    manager.on_success(
        url="https://example.com",
        method="GET",
        attempt=0,
        max_retries=3,
        response=mock_response,
        start_time=100.0,
    )


def test_on_failure_callback_invoked() -> None:
    """Test on_failure callback is invoked correctly."""
    mock_callback = Mock()
    config = CallbackConfig(on_failure=mock_callback)
    manager = CallbackManager(config)

    error = Exception("Test error")
    start_time = 100.0

    with patch("time.time", return_value=105.0):
        manager.on_failure(
            url="https://example.com",
            method="DELETE",
            attempt=3,
            max_retries=3,
            error=error,
            status_code=500,
            start_time=start_time,
        )

    mock_callback.assert_called_once()
    call_args = mock_callback.call_args[0]
    failure_info = call_args[0]
    assert failure_info.url == "https://example.com"
    assert failure_info.method == "DELETE"
    assert failure_info.attempt == 4  # Converted from 0-indexed to 1-indexed
    assert failure_info.max_retries == 3
    assert failure_info.error is error
    assert failure_info.status_code == 500
    assert failure_info.total_time == 5.0


def test_on_failure_callback_none() -> None:
    """Test on_failure does nothing when callback is None."""
    config = CallbackConfig()
    manager = CallbackManager(config)

    error = Exception("Test error")

    # Should not raise
    manager.on_failure(
        url="https://example.com",
        method="GET",
        attempt=3,
        max_retries=3,
        error=error,
        status_code=None,
        start_time=100.0,
    )


def test_all_callbacks_invoked() -> None:
    """Test all callbacks can be invoked together."""
    on_request_mock = Mock()
    on_retry_mock = Mock()
    on_success_mock = Mock()
    on_failure_mock = Mock()

    config = CallbackConfig(
        on_request=on_request_mock,
        on_retry=on_retry_mock,
        on_success=on_success_mock,
        on_failure=on_failure_mock,
    )
    manager = CallbackManager(config)

    # Invoke each callback
    manager.on_request("https://example.com", "GET", 0, 3)
    manager.on_retry("https://example.com", "GET", 0, 3, 1.0, None, 500)

    mock_response = Mock(spec=httpx.Response)
    with patch("time.time", return_value=100.0):
        manager.on_success("https://example.com", "GET", 1, 3, mock_response, 99.0)

    error = Exception("Test")
    with patch("time.time", return_value=100.0):
        manager.on_failure("https://example.com", "GET", 3, 3, error, None, 99.0)

    # Verify all were called
    on_request_mock.assert_called_once()
    on_retry_mock.assert_called_once()
    on_success_mock.assert_called_once()
    on_failure_mock.assert_called_once()
