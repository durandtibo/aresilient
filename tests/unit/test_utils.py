from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from aresilient.exceptions import HttpRequestError
from aresilient.utils import (
    calculate_sleep_time,
    handle_exception_with_callback,
    handle_request_error,
    handle_response,
    handle_timeout_exception,
    invoke_on_request,
    invoke_on_retry,
    invoke_on_success,
    raise_final_error,
    validate_retry_params,
)

TEST_URL = "https://api.example.com/data"


###########################################
#     Tests for validate_retry_params     #
###########################################


@pytest.mark.parametrize(("max_retries", "backoff_factor"), [(0, 0.0), (3, 0.3), (10, 1.5)])
def test_validate_retry_params_accepts_valid_values(
    max_retries: int, backoff_factor: float
) -> None:
    """Test that validate_retry_params accepts valid parameters."""
    validate_retry_params(max_retries=max_retries, backoff_factor=backoff_factor)


def test_validate_retry_params_rejects_negative_max_retries() -> None:
    """Test that validate_retry_params rejects negative max_retries."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0, got -1"):
        validate_retry_params(-1, 0.3)


def test_validate_retry_params_rejects_negative_backoff_factor() -> None:
    """Test that validate_retry_params rejects negative
    backoff_factor."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0, got -0.5"):
        validate_retry_params(3, -0.5)


def test_validate_retry_params_rejects_both_negative() -> None:
    """Test that validate_retry_params rejects both negative values."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        validate_retry_params(-1, -0.5)


@pytest.mark.parametrize("jitter_factor", [0.0, 0.1, 1.0])
def test_validate_retry_params_accepts_valid_jitter_factor(jitter_factor: float) -> None:
    """Test that validate_retry_params accepts valid jitter_factor."""
    validate_retry_params(max_retries=3, backoff_factor=0.5, jitter_factor=jitter_factor)


def test_validate_retry_params_rejects_negative_jitter_factor() -> None:
    """Test that validate_retry_params rejects negative
    jitter_factor."""
    with pytest.raises(ValueError, match=r"jitter_factor must be >= 0, got -0.1"):
        validate_retry_params(3, 0.5, jitter_factor=-0.1)


def test_validate_retry_params_accepts_valid_timeout() -> None:
    """Test that validate_retry_params accepts valid timeout."""
    validate_retry_params(max_retries=3, backoff_factor=0.5, timeout=10.0)
    validate_retry_params(max_retries=3, backoff_factor=0.5, timeout=0.1)


def test_validate_retry_params_rejects_negative_timeout() -> None:
    """Test that validate_retry_params rejects negative timeout."""
    with pytest.raises(ValueError, match=r"timeout must be > 0, got -1.0"):
        validate_retry_params(3, 0.5, timeout=-1.0)


def test_validate_retry_params_rejects_zero_timeout() -> None:
    """Test that validate_retry_params rejects zero timeout."""
    with pytest.raises(ValueError, match=r"timeout must be > 0, got 0"):
        validate_retry_params(3, 0.5, timeout=0)


##########################################
#     Tests for calculate_sleep_time     #
##########################################


@pytest.mark.parametrize(("attempt", "sleep_time"), [(0, 0.3), (1, 0.6), (2, 1.2)])
def test_calculate_sleep_time_exponential_backoff(attempt: int, sleep_time: float) -> None:
    """Test exponential backoff calculation without jitter."""
    assert (
        calculate_sleep_time(attempt, backoff_factor=0.3, jitter_factor=0.0, response=None)
        == sleep_time
    )


def test_calculate_sleep_time_with_jitter() -> None:
    """Test that jitter is correctly added to sleep time."""
    with patch("aresilient.utils.random.uniform", return_value=0.05):
        # Base sleep: 1.0 * 2^0 = 1.0
        # Jitter: 0.05 * 1.0 = 0.05
        # Total: 1.05
        assert (
            calculate_sleep_time(attempt=0, backoff_factor=1.0, jitter_factor=1.0, response=None)
            == 1.05
        )


def test_calculate_sleep_time_zero_jitter() -> None:
    """Test that zero jitter factor results in no jitter."""
    assert (
        calculate_sleep_time(attempt=0, backoff_factor=1.0, jitter_factor=0.0, response=None) == 1.0
    )


def test_calculate_sleep_time_with_retry_after_header() -> None:
    """Test that Retry-After header takes precedence over exponential
    backoff."""
    mock_response = Mock(spec=httpx.Response, headers={"Retry-After": "120"})

    # Should use 120 from Retry-After instead of 0.3 from backoff
    assert (
        calculate_sleep_time(
            attempt=0, backoff_factor=0.3, jitter_factor=0.0, response=mock_response
        )
        == 120.0
    )


def test_calculate_sleep_time_with_retry_after_and_jitter() -> None:
    """Test that jitter is applied to Retry-After value."""
    mock_response = Mock(spec=httpx.Response, headers={"Retry-After": "100"})

    with patch("aresilient.utils.random.uniform", return_value=0.1):
        # Base sleep from Retry-After: 100
        # Jitter: 0.1 * 100 = 10
        # Total: 110
        assert (
            calculate_sleep_time(
                attempt=0, backoff_factor=0.3, jitter_factor=1.0, response=mock_response
            )
            == 110.0
        )


def test_calculate_sleep_time_response_without_headers() -> None:
    """Test handling of response without headers attribute."""
    mock_response = Mock(spec=httpx.Response)
    del mock_response.headers  # Remove headers attribute

    # Should fall back to exponential backoff
    assert (
        calculate_sleep_time(
            attempt=0, backoff_factor=0.3, jitter_factor=0.0, response=mock_response
        )
        == 0.3
    )


def test_calculate_sleep_time_invalid_retry_after() -> None:
    """Test that invalid Retry-After header falls back to exponential
    backoff."""
    mock_response = Mock(spec=httpx.Response, headers={"Retry-After": "invalid"})

    # Should fall back to exponential backoff
    assert (
        calculate_sleep_time(
            attempt=0, backoff_factor=0.3, jitter_factor=0.0, response=mock_response
        )
        == 0.3
    )


#####################################
#     Tests for handle_response     #
#####################################


def test_handle_response_retryable_status() -> None:
    """Test that retryable status codes don't raise an exception."""
    mock_response = Mock(spec=httpx.Response, status_code=503)

    # Should not raise for status in forcelist
    handle_response(mock_response, TEST_URL, method="GET", status_forcelist=(503, 500))


def test_handle_response_non_retryable_status() -> None:
    """Test that non-retryable status codes raise HttpRequestError."""
    mock_response = Mock(spec=httpx.Response, status_code=404)

    with pytest.raises(HttpRequestError, match=r"failed with status 404") as exc_info:
        handle_response(mock_response, TEST_URL, method="GET", status_forcelist=(503, 500))

    error = exc_info.value
    assert error.method == "GET"
    assert error.url == TEST_URL
    assert error.status_code == 404
    assert error.response == mock_response


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
def test_handle_response_various_non_retryable_codes(status_code: int) -> None:
    """Test various non-retryable status codes."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)

    with pytest.raises(HttpRequestError, match=rf"failed with status {status_code}") as exc_info:
        handle_response(mock_response, TEST_URL, method="POST", status_forcelist=(500, 503))

    assert exc_info.value.status_code == status_code


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
        handle_timeout_exception(exc, TEST_URL, method="GET", attempt=3, max_retries=3)

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
        handle_timeout_exception(exc, TEST_URL, method="POST", attempt=0, max_retries=0)


def test_handle_timeout_exception_preserves_cause() -> None:
    """Test that the original exception is preserved as cause."""
    exc = httpx.TimeoutException("Request timed out")

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://api.example.com/data timed out \(3 attempts\)",
    ) as exc_info:
        handle_timeout_exception(exc, TEST_URL, method="GET", attempt=2, max_retries=2)

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
        handle_request_error(exc, TEST_URL, method="GET", attempt=3, max_retries=3)

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
        handle_request_error(exc, TEST_URL, method="POST", attempt=0, max_retries=0)


def test_handle_request_error_preserves_cause() -> None:
    """Test that the original exception is preserved as cause."""
    exc = httpx.ConnectError("Connection refused")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_request_error(exc, TEST_URL, method="GET", attempt=2, max_retries=2)

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
        handle_request_error(exc, TEST_URL, method="GET", attempt=1, max_retries=1)

    assert exc_info.value.__cause__ == exc


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
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "POST"
    assert call_args["attempt"] == 2  # 0-indexed to 1-indexed
    assert call_args["max_retries"] == 5


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
    assert call_args["attempt"] == 1


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

    with patch("aresilient.utils.time.time", return_value=105.5):
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
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "PUT"
    assert call_args["attempt"] == 3  # 0-indexed to 1-indexed
    assert call_args["max_retries"] == 5
    assert call_args["response"] == mock_response
    assert call_args["total_time"] == 5.5


def test_invoke_on_success_calculates_total_time() -> None:
    """Test that total_time is calculated correctly."""

    mock_callback = Mock()
    mock_response = Mock(spec=httpx.Response)

    with patch("aresilient.utils.time.time", return_value=110.0):
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
    assert call_args["total_time"] == 10.0


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
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "DELETE"
    assert call_args["attempt"] == 3  # Next attempt: 1 + 2
    assert call_args["max_retries"] == 5
    assert call_args["wait_time"] == 2.5
    assert call_args["error"] == error
    assert call_args["status_code"] is None


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
    assert call_args["status_code"] == 503
    assert call_args["error"] is None
    assert call_args["attempt"] == 2  # Next attempt: 0 + 2


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
    assert call_args["attempt"] == 5  # Next attempt: 3 + 2


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
        patch("aresilient.utils.time.time", return_value=105.0),
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
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "POST"
    assert call_args["attempt"] == 6  # 0-indexed to 1-indexed
    assert call_args["max_retries"] == 5
    assert call_args["status_code"] is None
    assert call_args["total_time"] == 5.0
    assert isinstance(call_args["error"], HttpRequestError)


def test_handle_exception_with_callback_reraises_error() -> None:
    """Test that the HttpRequestError is re-raised."""

    def failing_handler(
        _exc: Exception, url: str, method: str, _attempt: int, _max_retries: int
    ) -> None:
        raise HttpRequestError(method=method, url=url, message="Test failure")

    exc = Exception("Original error")

    with pytest.raises(HttpRequestError, match="Test failure"):
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
        patch("aresilient.utils.time.time", return_value=110.0),
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
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "DELETE"
    assert call_args["attempt"] == 3  # max_retries + 1
    assert call_args["max_retries"] == 2
    assert call_args["status_code"] == 500
    assert call_args["total_time"] == 10.0
    assert isinstance(call_args["error"], HttpRequestError)


def test_raise_final_error_calls_on_failure_without_response() -> None:
    """Test that on_failure callback is called without response."""

    mock_on_failure = Mock()

    with (
        patch("aresilient.utils.time.time", return_value=115.0),
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
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "PUT"
    assert call_args["attempt"] == 5  # max_retries + 1
    assert call_args["max_retries"] == 4
    assert call_args["status_code"] is None
    assert call_args["total_time"] == 15.0
    assert isinstance(call_args["error"], HttpRequestError)


def test_raise_final_error_calculates_total_time() -> None:
    """Test that total_time is calculated correctly."""

    mock_response = Mock(spec=httpx.Response, status_code=429)

    with (
        patch("aresilient.utils.time.time", return_value=123.456),
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
