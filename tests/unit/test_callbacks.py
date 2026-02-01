r"""Unit tests for callback functionality."""

from __future__ import annotations

from unittest.mock import Mock, call

import httpx
import pytest

from aresilient import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    HttpRequestError,
)
from aresilient.request import request_with_automatic_retry

TEST_URL = "https://api.example.com/data"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200)


@pytest.fixture
def mock_request_func(mock_response: httpx.Response) -> Mock:
    return Mock(return_value=mock_response)


##################################################
#     Tests for on_request callback              #
##################################################


def test_on_request_callback_called_on_first_attempt(
    mock_response: httpx.Response, mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test that on_request callback is called before the first
    attempt."""
    on_request_callback = Mock()

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        on_request=on_request_callback,
    )

    assert response == mock_response
    on_request_callback.assert_called_once()
    call_args = on_request_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "GET"
    assert call_args["attempt"] == 1
    assert call_args["max_retries"] == DEFAULT_MAX_RETRIES
    mock_sleep.assert_not_called()


def test_on_request_callback_called_on_each_retry(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test that on_request callback is called before each retry
    attempt."""
    on_request_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(503,),
        on_request=on_request_callback,
    )

    assert response == mock_response
    assert on_request_callback.call_count == 3

    # Check first attempt
    first_call = on_request_callback.call_args_list[0][0][0]
    assert first_call["attempt"] == 1
    assert first_call["max_retries"] == DEFAULT_MAX_RETRIES

    # Check second attempt
    second_call = on_request_callback.call_args_list[1][0][0]
    assert second_call["attempt"] == 2

    # Check third attempt
    third_call = on_request_callback.call_args_list[2][0][0]
    assert third_call["attempt"] == 3
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


##################################################
#     Tests for on_retry callback                #
##################################################


def test_on_retry_callback_called_before_retry(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test that on_retry callback is called before each retry."""
    on_retry_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(503,),
        on_retry=on_retry_callback,
    )

    assert response == mock_response
    on_retry_callback.assert_called_once()
    call_args = on_retry_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "GET"
    assert call_args["attempt"] == 2  # Next attempt
    assert call_args["max_retries"] == DEFAULT_MAX_RETRIES
    assert call_args["wait_time"] == DEFAULT_BACKOFF_FACTOR
    assert call_args["status_code"] == 503
    assert call_args["error"] is None
    mock_sleep.assert_called_once_with(0.3)


def test_on_retry_callback_not_called_on_first_success(
    mock_response: httpx.Response, mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test that on_retry callback is not called when request succeeds
    on first attempt."""
    on_retry_callback = Mock()

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        on_retry=on_retry_callback,
    )

    assert response == mock_response
    on_retry_callback.assert_not_called()
    mock_sleep.assert_not_called()


def test_on_retry_callback_with_timeout_exception(mock_sleep: Mock) -> None:
    """Test that on_retry callback receives error information on
    timeout."""
    on_retry_callback = Mock()
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(side_effect=[httpx.TimeoutException("timeout"), mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        on_retry=on_retry_callback,
    )

    assert response == mock_response
    on_retry_callback.assert_called_once()
    call_args = on_retry_callback.call_args[0][0]
    assert isinstance(call_args["error"], httpx.TimeoutException)
    assert call_args["status_code"] is None
    mock_sleep.assert_called_once_with(0.3)


def test_on_retry_callback_with_request_error(mock_sleep: Mock) -> None:
    """Test that on_retry callback receives error information on request
    error."""
    on_retry_callback = Mock()
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(side_effect=[httpx.ConnectError("connection failed"), mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        on_retry=on_retry_callback,
    )

    assert response == mock_response
    on_retry_callback.assert_called_once()
    call_args = on_retry_callback.call_args[0][0]
    assert isinstance(call_args["error"], httpx.ConnectError)
    assert call_args["status_code"] is None
    mock_sleep.assert_called_once_with(0.3)


##################################################
#     Tests for on_success callback              #
##################################################


def test_on_success_callback_called_on_success(
    mock_response: httpx.Response, mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test that on_success callback is called when request succeeds."""
    on_success_callback = Mock()

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        on_success=on_success_callback,
    )

    assert response == mock_response
    on_success_callback.assert_called_once()
    call_args = on_success_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "GET"
    assert call_args["attempt"] == 1
    assert call_args["max_retries"] == DEFAULT_MAX_RETRIES
    assert call_args["response"] == mock_response
    assert "total_time" in call_args
    assert call_args["total_time"] >= 0
    mock_sleep.assert_not_called()


def test_on_success_callback_after_retries(mock_response: httpx.Response, mock_sleep: Mock) -> None:
    """Test that on_success callback is called after successful
    retry."""
    on_success_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(503,),
        on_success=on_success_callback,
    )

    assert response == mock_response
    on_success_callback.assert_called_once()
    call_args = on_success_callback.call_args[0][0]
    assert call_args["attempt"] == 3  # Succeeded on third attempt
    assert call_args["response"] == mock_response
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_on_success_callback_not_called_on_failure(mock_sleep: Mock) -> None:
    """Test that on_success callback is not called when request
    fails."""
    on_success_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(HttpRequestError):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            status_forcelist=(503,),
            max_retries=2,
            on_success=on_success_callback,
        )

    on_success_callback.assert_not_called()
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


##################################################
#     Tests for on_failure callback              #
##################################################


def test_on_failure_callback_called_on_retryable_status_failure(
    mock_sleep: Mock,
) -> None:
    """Test that on_failure callback is called when retries are
    exhausted."""
    on_failure_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(HttpRequestError):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            status_forcelist=(503,),
            max_retries=2,
            on_failure=on_failure_callback,
        )

    on_failure_callback.assert_called_once()
    call_args = on_failure_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "GET"
    assert call_args["attempt"] == 3  # max_retries + 1
    assert call_args["max_retries"] == 2
    assert isinstance(call_args["error"], HttpRequestError)
    assert call_args["status_code"] == 503
    assert "total_time" in call_args
    assert call_args["total_time"] >= 0
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_on_failure_callback_not_called_on_success(
    mock_response: httpx.Response, mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test that on_failure callback is not called when request
    succeeds."""
    on_failure_callback = Mock()

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        on_failure=on_failure_callback,
    )

    assert response == mock_response
    on_failure_callback.assert_not_called()
    mock_sleep.assert_not_called()


def test_on_failure_callback_with_timeout_error(mock_sleep: Mock) -> None:
    """Test that on_failure callback is called when timeouts are
    exhausted."""
    on_failure_callback = Mock()
    mock_request_func = Mock(side_effect=httpx.TimeoutException("timeout"))

    with pytest.raises(HttpRequestError):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            max_retries=1,
            on_failure=on_failure_callback,
        )

    on_failure_callback.assert_called_once()
    call_args = on_failure_callback.call_args[0][0]
    assert isinstance(call_args["error"], HttpRequestError)
    assert call_args["status_code"] is None
    mock_sleep.assert_called_once_with(0.3)


##################################################
#     Tests for multiple callbacks               #
##################################################


def test_all_callbacks_together_on_success(mock_response: httpx.Response, mock_sleep: Mock) -> None:
    """Test that all callbacks work together correctly on successful
    retry."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()

    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(503,),
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_success=on_success_callback,
        on_failure=on_failure_callback,
    )

    assert response == mock_response
    assert on_request_callback.call_count == 2  # Two attempts
    on_retry_callback.assert_called_once()  # One retry
    on_success_callback.assert_called_once()  # One success
    on_failure_callback.assert_not_called()  # No failure
    mock_sleep.assert_called_once_with(0.3)


def test_all_callbacks_together_on_failure(mock_sleep: Mock) -> None:
    """Test that all callbacks work together correctly on failure."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()

    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(HttpRequestError):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            status_forcelist=(503,),
            max_retries=2,
            on_request=on_request_callback,
            on_retry=on_retry_callback,
            on_success=on_success_callback,
            on_failure=on_failure_callback,
        )

    assert on_request_callback.call_count == 3  # Three attempts
    assert on_retry_callback.call_count == 2  # Two retries
    on_success_callback.assert_not_called()  # No success
    on_failure_callback.assert_called_once()  # One failure
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


##################################################
#     Tests for callback exceptions              #
##################################################


def test_callback_exception_does_not_break_retry_logic(
    mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test that exceptions in callbacks do not break the retry
    logic."""
    on_request_callback = Mock(side_effect=ValueError("callback error"))

    # Should still succeed despite callback exception
    with pytest.raises(ValueError, match="callback error"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            on_request=on_request_callback,
        )

    mock_sleep.assert_not_called()


##################################################
#     Tests with custom retry parameters         #
##################################################


def test_callbacks_with_custom_max_retries(mock_response: httpx.Response, mock_sleep: Mock) -> None:
    """Test that callbacks receive correct max_retries value."""
    on_request_callback = Mock()
    on_retry_callback = Mock()

    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(503,),
        max_retries=5,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
    )

    assert response == mock_response

    # Check that max_retries is correctly passed
    request_call_args = on_request_callback.call_args_list[0][0][0]
    assert request_call_args["max_retries"] == 5

    retry_call_args = on_retry_callback.call_args[0][0]
    assert retry_call_args["max_retries"] == 5
    mock_sleep.assert_called_once_with(0.3)


def test_callbacks_with_custom_backoff_factor(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test that on_retry callback receives correct wait_time with
    custom backoff."""
    on_retry_callback = Mock()

    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(503,),
        backoff_factor=2.0,
        on_retry=on_retry_callback,
    )

    assert response == mock_response

    retry_call_args = on_retry_callback.call_args[0][0]
    assert retry_call_args["wait_time"] == 2.0  # 2.0 * (2 ** 0)
    mock_sleep.assert_called_once_with(2.0)
