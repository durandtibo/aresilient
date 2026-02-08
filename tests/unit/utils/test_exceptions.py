from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from aresilient.exceptions import HttpRequestError
from aresilient.utils import (
    handle_exception_with_callback,
    handle_request_error,
    handle_timeout_exception,
    raise_final_error,
)

TEST_URL = "https://api.example.com/data"


##############################################
#     Tests for handle_timeout_exception     #
##############################################


@pytest.mark.parametrize("attempt", [0, 1, 2])
def test_handle_timeout_exception_not_max_retries(attempt: int) -> None:
    """Test that timeout exception doesn't raise when retries remain."""
    exc = httpx.TimeoutException("Request timed out")
    # Should not raise when attempt < max_retries
    handle_timeout_exception(exc, TEST_URL, method="GET", attempt=attempt, max_retries=3)


def test_handle_timeout_exception_at_max_retries() -> None:
    """Test that timeout exception raises HttpRequestError at max
    retries."""
    exc = httpx.TimeoutException("Request timed out")

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://api.example.com/data timed out \(4 attempts\)",
    ) as exc_info:
        handle_timeout_exception(exc=exc, url=TEST_URL, method="GET", attempt=3, max_retries=3)

    error = exc_info.value
    assert error.method == "GET"
    assert error.url == TEST_URL
    assert error.__cause__ == exc


def test_handle_timeout_exception_zero_max_retries() -> None:
    """Test timeout exception with zero max retries."""
    exc = httpx.TimeoutException("Request timed out")

    with pytest.raises(
        HttpRequestError,
        match=r"POST request to https://api.example.com/data timed out \(1 attempts\)",
    ):
        handle_timeout_exception(exc=exc, url=TEST_URL, method="POST", attempt=0, max_retries=0)


def test_handle_timeout_exception_preserves_cause() -> None:
    """Test that the original exception is preserved as cause."""
    exc = httpx.TimeoutException("Request timed out")

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://api.example.com/data timed out \(3 attempts\)",
    ) as exc_info:
        handle_timeout_exception(exc=exc, url=TEST_URL, method="GET", attempt=2, max_retries=2)

    assert exc_info.value.__cause__ == exc


##########################################
#     Tests for handle_request_error     #
##########################################


@pytest.mark.parametrize("attempt", [0, 1, 2])
def test_handle_request_error_not_max_retries(attempt: int) -> None:
    """Test that request error doesn't raise when retries remain."""
    exc = httpx.RequestError("Connection failed")
    # Should not raise when attempt < max_retries
    handle_request_error(exc, TEST_URL, method="GET", attempt=attempt, max_retries=3)


def test_handle_request_error_at_max_retries() -> None:
    """Test that request error raises HttpRequestError at max
    retries."""
    exc = httpx.RequestError("Connection failed")

    with pytest.raises(
        HttpRequestError,
        match=(
            r"GET request to https://api.example.com/data failed after 4 attempts: "
            r"Connection failed"
        ),
    ) as exc_info:
        handle_request_error(exc=exc, url=TEST_URL, method="GET", attempt=3, max_retries=3)

    error = exc_info.value
    assert error.method == "GET"
    assert error.url == TEST_URL
    assert error.__cause__ == exc


def test_handle_request_error_zero_max_retries() -> None:
    """Test request error with zero max retries."""
    exc = httpx.ConnectError("Connection refused")

    with pytest.raises(
        HttpRequestError,
        match=(
            r"POST request to https://api.example.com/data failed after 1 attempts: "
            r"Connection refused"
        ),
    ):
        handle_request_error(exc=exc, url=TEST_URL, method="POST", attempt=0, max_retries=0)


def test_handle_request_error_preserves_cause() -> None:
    """Test that the original exception is preserved as cause."""
    exc = httpx.ConnectError("Connection refused")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_request_error(exc=exc, url=TEST_URL, method="GET", attempt=2, max_retries=2)

    assert exc_info.value.__cause__ == exc


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ConnectError("Connection refused"),
        httpx.ReadError("Read failed"),
        httpx.WriteError("Write failed"),
        httpx.ProxyError("Proxy error"),
    ],
)
def test_handle_request_error_various_error_types(exc: httpx.RequestError) -> None:
    """Test handling of various request error types."""
    with pytest.raises(HttpRequestError) as exc_info:
        handle_request_error(exc=exc, url=TEST_URL, method="GET", attempt=1, max_retries=1)

    assert exc_info.value.__cause__ == exc


########################################################
#     Tests for handle_exception_with_callback        #
########################################################


def test_handle_exception_with_callback_non_final_attempt() -> None:
    """Test that callback is not called on non-final attempts."""

    mock_on_failure = Mock()
    mock_handler = Mock()
    exc = Exception("Test error")

    handle_exception_with_callback(
        exc,
        url=TEST_URL,
        method="GET",
        attempt=0,
        max_retries=3,
        handler_func=mock_handler,
        on_failure=mock_on_failure,
        start_time=100.0,
    )

    mock_handler.assert_called_once_with(exc, TEST_URL, "GET", 0, 3)
    mock_on_failure.assert_not_called()


def test_handle_exception_with_callback_final_attempt_without_callback() -> None:
    """Test final attempt without on_failure callback."""

    def failing_handler(
        _exc: Exception, url: str, method: str, _attempt: int, _max_retries: int
    ) -> None:
        raise HttpRequestError(method=method, url=url, message="Failed")

    exc = Exception("Test error")

    with pytest.raises(HttpRequestError):
        handle_exception_with_callback(
            exc,
            url=TEST_URL,
            method="GET",
            attempt=3,
            max_retries=3,
            handler_func=failing_handler,
            on_failure=None,
            start_time=100.0,
        )


def test_handle_exception_with_callback_final_attempt_with_callback() -> None:
    """Test that callback is called on final attempt."""

    def failing_handler(
        exc: Exception, url: str, method: str, _attempt: int, _max_retries: int
    ) -> None:
        raise HttpRequestError(method=method, url=url, message="Failed", cause=exc)

    mock_on_failure = Mock()
    exc = Exception("Test error")

    with (
        patch("aresilient.utils.exceptions.time.time", return_value=105.0),
        pytest.raises(HttpRequestError),
    ):
        handle_exception_with_callback(
            exc,
            url=TEST_URL,
            method="POST",
            attempt=5,
            max_retries=5,
            handler_func=failing_handler,
            on_failure=mock_on_failure,
            start_time=100.0,
        )

    mock_on_failure.assert_called_once()
    call_args = mock_on_failure.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "POST"
    assert call_args.attempt == 6  # 0-indexed to 1-indexed
    assert call_args.max_retries == 5
    assert call_args.status_code is None
    assert call_args.total_time == 5.0
    assert isinstance(call_args.error, HttpRequestError)


def test_handle_exception_with_callback_reraises_error() -> None:
    """Test that the HttpRequestError is re-raised."""

    def failing_handler(
        _exc: Exception, url: str, method: str, _attempt: int, _max_retries: int
    ) -> None:
        raise HttpRequestError(method=method, url=url, message="Test failure")

    exc = Exception("Original error")

    with pytest.raises(HttpRequestError, match=r"Test failure"):
        handle_exception_with_callback(
            exc,
            url=TEST_URL,
            method="GET",
            attempt=2,
            max_retries=2,
            handler_func=failing_handler,
            on_failure=None,
            start_time=100.0,
        )


################################################
#     Tests for raise_final_error             #
################################################


def test_raise_final_error_with_response() -> None:
    """Test raise_final_error with a response object."""

    mock_response = Mock(spec=httpx.Response, status_code=503)

    with pytest.raises(HttpRequestError) as exc_info:
        raise_final_error(
            url=TEST_URL,
            method="GET",
            max_retries=3,
            response=mock_response,
            on_failure=None,
            start_time=100.0,
        )

    error = exc_info.value
    assert error.method == "GET"
    assert error.url == TEST_URL
    assert error.status_code == 503
    assert error.response == mock_response
    assert "503" in str(error)
    assert "4 attempts" in str(error)


def test_raise_final_error_without_response() -> None:
    """Test raise_final_error without a response object."""

    with pytest.raises(HttpRequestError) as exc_info:
        raise_final_error(
            url=TEST_URL,
            method="POST",
            max_retries=5,
            response=None,
            on_failure=None,
            start_time=100.0,
        )

    error = exc_info.value
    assert error.method == "POST"
    assert error.url == TEST_URL
    assert error.status_code is None
    assert error.response is None
    assert "6 attempts" in str(error)


def test_raise_final_error_calls_on_failure_with_response() -> None:
    """Test that on_failure callback is called with response."""

    mock_on_failure = Mock()
    mock_response = Mock(spec=httpx.Response, status_code=500)

    with (
        patch("aresilient.utils.exceptions.time.time", return_value=110.0),
        pytest.raises(HttpRequestError),
    ):
        raise_final_error(
            url=TEST_URL,
            method="DELETE",
            max_retries=2,
            response=mock_response,
            on_failure=mock_on_failure,
            start_time=100.0,
        )

    mock_on_failure.assert_called_once()
    call_args = mock_on_failure.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "DELETE"
    assert call_args.attempt == 3  # max_retries + 1
    assert call_args.max_retries == 2
    assert call_args.status_code == 500
    assert call_args.total_time == 10.0
    assert isinstance(call_args.error, HttpRequestError)


def test_raise_final_error_calls_on_failure_without_response() -> None:
    """Test that on_failure callback is called without response."""

    mock_on_failure = Mock()

    with (
        patch("aresilient.utils.exceptions.time.time", return_value=115.0),
        pytest.raises(HttpRequestError),
    ):
        raise_final_error(
            url=TEST_URL,
            method="PUT",
            max_retries=4,
            response=None,
            on_failure=mock_on_failure,
            start_time=100.0,
        )

    mock_on_failure.assert_called_once()
    call_args = mock_on_failure.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "PUT"
    assert call_args.attempt == 5  # max_retries + 1
    assert call_args.max_retries == 4
    assert call_args.status_code is None
    assert call_args.total_time == 15.0
    assert isinstance(call_args.error, HttpRequestError)


def test_raise_final_error_calculates_total_time() -> None:
    """Test that total_time is calculated correctly."""

    mock_response = Mock(spec=httpx.Response, status_code=429)

    with (
        patch("aresilient.utils.exceptions.time.time", return_value=123.456),
        pytest.raises(HttpRequestError),
    ):
        raise_final_error(
            url=TEST_URL,
            method="GET",
            max_retries=3,
            response=mock_response,
            on_failure=None,
            start_time=100.0,
        )
