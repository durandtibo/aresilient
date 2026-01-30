from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from aresnet.exceptions import HttpRequestError
from aresnet.utils import (
    calculate_sleep_time,
    handle_request_error,
    handle_response,
    handle_timeout_exception,
    validate_retry_params,
)

TEST_URL = "https://api.example.com/data"


##################################################
#     Tests for validate_retry_params           #
##################################################
import math

import pytest

from aresnet.utils import parse_retry_after, validate_retry_params


def test_validate_retry_params_accepts_valid_values() -> None:
    """Test that validate_retry_params accepts valid parameters."""
    validate_retry_params(3, 0.3)
    validate_retry_params(0, 0.0)
    validate_retry_params(10, 1.5)


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


##################################################
#     Tests for calculate_sleep_time            #
##################################################


def test_calculate_sleep_time_exponential_backoff() -> None:
    """Test exponential backoff calculation without jitter."""
    # Attempt 0: 0.3 * 2^0 = 0.3
    sleep_time = calculate_sleep_time(0, 0.3, 0.0, None)
    assert sleep_time == 0.3

    # Attempt 1: 0.3 * 2^1 = 0.6
    sleep_time = calculate_sleep_time(1, 0.3, 0.0, None)
    assert sleep_time == 0.6

    # Attempt 2: 0.3 * 2^2 = 1.2
    sleep_time = calculate_sleep_time(2, 0.3, 0.0, None)
    assert sleep_time == 1.2


def test_calculate_sleep_time_with_jitter() -> None:
    """Test that jitter is correctly added to sleep time."""
    with patch("aresnet.utils.random.uniform", return_value=0.05):
        # Base sleep: 1.0 * 2^0 = 1.0
        # Jitter: 0.05 * 1.0 = 0.05
        # Total: 1.05
        sleep_time = calculate_sleep_time(0, 1.0, 1.0, None)
        assert sleep_time == 1.05


def test_calculate_sleep_time_zero_jitter() -> None:
    """Test that zero jitter factor results in no jitter."""
    sleep_time = calculate_sleep_time(0, 1.0, 0.0, None)
    assert sleep_time == 1.0


def test_calculate_sleep_time_with_retry_after_header() -> None:
    """Test that Retry-After header takes precedence over exponential backoff."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.headers = {"Retry-After": "120"}

    # Should use 120 from Retry-After instead of 0.3 from backoff
    sleep_time = calculate_sleep_time(0, 0.3, 0.0, mock_response)
    assert sleep_time == 120.0


def test_calculate_sleep_time_with_retry_after_and_jitter() -> None:
    """Test that jitter is applied to Retry-After value."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.headers = {"Retry-After": "100"}

    with patch("aresnet.utils.random.uniform", return_value=0.1):
        # Base sleep from Retry-After: 100
        # Jitter: 0.1 * 100 = 10
        # Total: 110
        sleep_time = calculate_sleep_time(0, 0.3, 1.0, mock_response)
        assert sleep_time == 110.0


def test_calculate_sleep_time_response_without_headers() -> None:
    """Test handling of response without headers attribute."""
    mock_response = Mock(spec=httpx.Response)
    del mock_response.headers  # Remove headers attribute

    # Should fall back to exponential backoff
    sleep_time = calculate_sleep_time(0, 0.3, 0.0, mock_response)
    assert sleep_time == 0.3


def test_calculate_sleep_time_invalid_retry_after() -> None:
    """Test that invalid Retry-After header falls back to exponential backoff."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.headers = {"Retry-After": "invalid"}

    # Should fall back to exponential backoff
    sleep_time = calculate_sleep_time(0, 0.3, 0.0, mock_response)
    assert sleep_time == 0.3


##################################################
#     Tests for handle_response                 #
##################################################


def test_handle_response_retryable_status() -> None:
    """Test that retryable status codes don't raise an exception."""
    mock_response = Mock(spec=httpx.Response, status_code=503)

    # Should not raise for status in forcelist
    handle_response(mock_response, TEST_URL, "GET", (503, 500))


def test_handle_response_non_retryable_status() -> None:
    """Test that non-retryable status codes raise HttpRequestError."""
    mock_response = Mock(spec=httpx.Response, status_code=404)

    with pytest.raises(HttpRequestError) as exc_info:
        handle_response(mock_response, TEST_URL, "GET", (503, 500))

    error = exc_info.value
    assert error.method == "GET"
    assert error.url == TEST_URL
    assert error.status_code == 404
    assert error.response == mock_response
    assert "failed with status 404" in str(error)


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
def test_handle_response_various_non_retryable_codes(status_code: int) -> None:
    """Test various non-retryable status codes."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)

    with pytest.raises(HttpRequestError) as exc_info:
        handle_response(mock_response, TEST_URL, "POST", (500, 503))

    assert exc_info.value.status_code == status_code


##################################################
#     Tests for handle_timeout_exception        #
##################################################


def test_handle_timeout_exception_not_max_retries() -> None:
    """Test that timeout exception doesn't raise when retries remain."""
    exc = httpx.TimeoutException("Request timed out")

    # Should not raise when attempt < max_retries
    handle_timeout_exception(exc, TEST_URL, "GET", 0, 3)
    handle_timeout_exception(exc, TEST_URL, "GET", 1, 3)
    handle_timeout_exception(exc, TEST_URL, "GET", 2, 3)


def test_handle_timeout_exception_at_max_retries() -> None:
    """Test that timeout exception raises HttpRequestError at max retries."""
    exc = httpx.TimeoutException("Request timed out")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_timeout_exception(exc, TEST_URL, "GET", 3, 3)

    error = exc_info.value
    assert error.method == "GET"
    assert error.url == TEST_URL
    assert error.__cause__ == exc
    assert "timed out (4 attempts)" in str(error)


def test_handle_timeout_exception_zero_max_retries() -> None:
    """Test timeout exception with zero max retries."""
    exc = httpx.TimeoutException("Request timed out")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_timeout_exception(exc, TEST_URL, "POST", 0, 0)

    error = exc_info.value
    assert "timed out (1 attempts)" in str(error)


def test_handle_timeout_exception_preserves_cause() -> None:
    """Test that the original exception is preserved as cause."""
    exc = httpx.TimeoutException("Request timed out")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_timeout_exception(exc, TEST_URL, "GET", 2, 2)

    assert exc_info.value.__cause__ == exc


##################################################
#     Tests for handle_request_error            #
##################################################


def test_handle_request_error_not_max_retries() -> None:
    """Test that request error doesn't raise when retries remain."""
    exc = httpx.RequestError("Connection failed")

    # Should not raise when attempt < max_retries
    handle_request_error(exc, TEST_URL, "GET", 0, 3)
    handle_request_error(exc, TEST_URL, "GET", 1, 3)
    handle_request_error(exc, TEST_URL, "GET", 2, 3)


def test_handle_request_error_at_max_retries() -> None:
    """Test that request error raises HttpRequestError at max retries."""
    exc = httpx.RequestError("Connection failed")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_request_error(exc, TEST_URL, "GET", 3, 3)

    error = exc_info.value
    assert error.method == "GET"
    assert error.url == TEST_URL
    assert error.__cause__ == exc
    assert "failed after 4 attempts" in str(error)


def test_handle_request_error_zero_max_retries() -> None:
    """Test request error with zero max retries."""
    exc = httpx.ConnectError("Connection refused")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_request_error(exc, TEST_URL, "POST", 0, 0)

    error = exc_info.value
    assert "failed after 1 attempts" in str(error)


def test_handle_request_error_preserves_cause() -> None:
    """Test that the original exception is preserved as cause."""
    exc = httpx.ConnectError("Connection refused")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_request_error(exc, TEST_URL, "GET", 2, 2)

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
        handle_request_error(exc, TEST_URL, "GET", 1, 1)

    assert exc_info.value.__cause__ == exc

