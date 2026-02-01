r"""Unit tests for retry_if custom predicate functionality."""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresilient import HttpRequestError
from aresilient.request import request_with_automatic_retry

TEST_URL = "https://api.example.com/data"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200, text="success")


@pytest.fixture
def mock_request_func(mock_response: httpx.Response) -> Mock:
    return Mock(return_value=mock_response)


########################################################
#     Tests for retry_if with successful responses     #
########################################################


def test_retry_if_returns_false_for_successful_response(
    mock_response: httpx.Response, mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test retry_if that returns False for successful response (no retry)."""

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return False

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
    )

    assert response == mock_response
    mock_request_func.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_retry_if_returns_true_for_successful_response(mock_sleep: Mock) -> None:
    """Test retry_if that returns True even for successful response (triggers retry)."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=200, text="success")
    mock_request_func = Mock(return_value=mock_response_ok)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Always retry - should exhaust retries
        return True

    with pytest.raises(HttpRequestError, match="failed with status 200 after 4 attempts"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
            max_retries=3,
        )

    # Should have tried 4 times (initial + 3 retries)
    assert mock_request_func.call_count == 4
    # Should have slept 3 times between attempts
    assert mock_sleep.call_count == 3


def test_retry_if_checks_response_content(mock_sleep: Mock) -> None:
    """Test retry_if that checks response content and retries on specific text."""
    mock_response_retry = Mock(spec=httpx.Response, status_code=200, text="please retry")
    mock_response_ok = Mock(spec=httpx.Response, status_code=200, text="success")
    mock_request_func = Mock(side_effect=[mock_response_retry, mock_response_ok])

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry if response contains "retry"
        if response and "retry" in response.text.lower():
            return True
        return False

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_request_func.call_count == 2
    mock_sleep.assert_called_once()


#####################################################
#     Tests for retry_if with error responses     #
#####################################################


def test_retry_if_returns_false_for_error_response(mock_sleep: Mock) -> None:
    """Test retry_if that returns False for error response (no retry, immediate fail)."""
    mock_response_error = Mock(spec=httpx.Response, status_code=500)
    mock_request_func = Mock(return_value=mock_response_error)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return False  # Never retry

    with pytest.raises(HttpRequestError, match="failed with status 500"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
        )

    # Should only try once since retry_if returns False
    mock_request_func.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_retry_if_returns_true_for_error_response(mock_sleep: Mock) -> None:
    """Test retry_if that returns True for error response (triggers retry)."""
    mock_response_error = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(side_effect=[mock_response_error, mock_response_ok])

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        if response and response.status_code >= 500:
            return True
        return False

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_request_func.call_count == 2
    mock_sleep.assert_called_once()


def test_retry_if_with_status_code_logic(mock_sleep: Mock) -> None:
    """Test retry_if that implements custom status code retry logic."""
    mock_response_429 = Mock(spec=httpx.Response, status_code=429)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(side_effect=[mock_response_429, mock_response_ok])

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Only retry on 429
        if response and response.status_code == 429:
            return True
        return False

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_request_func.call_count == 2


def test_retry_if_does_not_retry_non_retryable_status(mock_sleep: Mock) -> None:
    """Test retry_if that doesn't retry on 404 (client error)."""
    mock_response_404 = Mock(spec=httpx.Response, status_code=404)
    mock_request_func = Mock(return_value=mock_response_404)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Only retry on server errors (5xx)
        if response and 500 <= response.status_code < 600:
            return True
        return False

    with pytest.raises(HttpRequestError, match="failed with status 404"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
        )

    # Should only try once
    mock_request_func.assert_called_once()
    mock_sleep.assert_not_called()


###################################################
#     Tests for retry_if with exceptions     #
###################################################


def test_retry_if_returns_false_for_exception(mock_sleep: Mock) -> None:
    """Test retry_if that returns False for exceptions (no retry)."""
    mock_request_func = Mock(side_effect=httpx.TimeoutException("timeout"))

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return False  # Never retry

    with pytest.raises(HttpRequestError, match="timed out"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
        )

    # Should only try once
    mock_request_func.assert_called_once()
    mock_sleep.assert_not_called()


def test_retry_if_returns_true_for_exception(mock_sleep: Mock) -> None:
    """Test retry_if that returns True for exceptions (triggers retry)."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(
        side_effect=[httpx.TimeoutException("timeout"), mock_response_ok]
    )

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry on timeout exceptions
        if isinstance(exception, httpx.TimeoutException):
            return True
        return False

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_request_func.call_count == 2
    mock_sleep.assert_called_once()


def test_retry_if_with_connection_error(mock_sleep: Mock) -> None:
    """Test retry_if that handles connection errors."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(
        side_effect=[httpx.ConnectError("connection failed"), mock_response_ok]
    )

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry on connection errors
        if isinstance(exception, httpx.ConnectError):
            return True
        return False

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_request_func.call_count == 2


def test_retry_if_exhausts_retries_with_exception(mock_sleep: Mock) -> None:
    """Test retry_if exhausts retries when exception keeps occurring."""
    mock_request_func = Mock(side_effect=httpx.TimeoutException("timeout"))

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Always retry timeouts
        if isinstance(exception, httpx.TimeoutException):
            return True
        return False

    with pytest.raises(HttpRequestError, match="timed out"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
            max_retries=2,
        )

    # Should try 3 times (initial + 2 retries)
    assert mock_request_func.call_count == 3


#########################################################
#     Tests for retry_if with mixed scenarios     #
#########################################################


def test_retry_if_complex_logic(mock_sleep: Mock) -> None:
    """Test retry_if with complex custom logic combining response and exception checks."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500, text="server error")
    mock_response_200_retry = Mock(spec=httpx.Response, status_code=200, text="rate limit exceeded")
    mock_response_ok = Mock(spec=httpx.Response, status_code=200, text="success")

    mock_request_func = Mock(
        side_effect=[mock_response_500, mock_response_200_retry, mock_response_ok]
    )

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry on server errors
        if response and response.status_code >= 500:
            return True
        # Retry if response contains rate limit message
        if response and "rate limit" in response.text.lower():
            return True
        # Retry on network errors
        if isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)):
            return True
        return False

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_request_func.call_count == 3
    assert mock_sleep.call_count == 2


def test_retry_if_none_uses_default_behavior(mock_sleep: Mock) -> None:
    """Test that when retry_if is None, default status_forcelist behavior is used."""
    mock_response_503 = Mock(spec=httpx.Response, status_code=503)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(side_effect=[mock_response_503, mock_response_ok])

    # No retry_if provided - should use default behavior
    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(503,),
    )

    assert response == mock_response_ok
    assert mock_request_func.call_count == 2
    mock_sleep.assert_called_once()


############################################
#     Tests for retry_if with callbacks     #
############################################


def test_retry_if_with_on_retry_callback(mock_sleep: Mock) -> None:
    """Test retry_if works correctly with on_retry callback."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(side_effect=[mock_response_500, mock_response_ok])

    retry_callback = Mock()

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        if response and response.status_code >= 500:
            return True
        return False

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        on_retry=retry_callback,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_request_func.call_count == 2
    retry_callback.assert_called_once()


def test_retry_if_with_on_failure_callback(mock_sleep: Mock) -> None:
    """Test retry_if triggers on_failure callback when retries exhausted."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)
    mock_request_func = Mock(return_value=mock_response_500)

    failure_callback = Mock()

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        if response and response.status_code >= 500:
            return True
        return False

    with pytest.raises(HttpRequestError):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
            on_failure=failure_callback,
            max_retries=2,
        )

    failure_callback.assert_called_once()
