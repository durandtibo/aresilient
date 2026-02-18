r"""Unit tests for callback functionality."""

from __future__ import annotations

from unittest.mock import Mock, call, patch

import httpx
import pytest

from aresilient.callbacks import (
    RequestInfo,
    RetryInfo,
    invoke_on_request,
    invoke_on_retry,
    invoke_on_success,
)
from aresilient.core import DEFAULT_BACKOFF_FACTOR, DEFAULT_MAX_RETRIES
from aresilient.exceptions import HttpRequestError
from aresilient.request import request_with_automatic_retry

TEST_URL = "https://api.example.com/data"


#########################################
#     Tests for on_request callback     #
#########################################


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
    on_request_callback.assert_called_once_with(
        RequestInfo(url=TEST_URL, method="GET", attempt=1, max_retries=DEFAULT_MAX_RETRIES)
    )
    mock_sleep.assert_not_called()


def test_on_request_callback_called_on_each_retry(
    mock_response: httpx.Response, mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_request callback is called before each retry
    attempt."""
    on_request_callback = Mock()
    mock_request_func = Mock(side_effect=[mock_response_fail, mock_response_fail, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(500,),
        on_request=on_request_callback,
    )

    assert response == mock_response
    assert on_request_callback.call_args_list == [
        call(RequestInfo(url=TEST_URL, method="GET", attempt=1, max_retries=DEFAULT_MAX_RETRIES)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=2, max_retries=DEFAULT_MAX_RETRIES)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=3, max_retries=DEFAULT_MAX_RETRIES)),
    ]

    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


#######################################
#     Tests for on_retry callback     #
#######################################


def test_on_retry_callback_called_before_retry(
    mock_response: httpx.Response, mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_retry callback is called before each retry."""
    on_retry_callback = Mock()
    mock_request_func = Mock(side_effect=[mock_response_fail, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(500,),
        on_retry=on_retry_callback,
    )

    assert response == mock_response
    on_retry_callback.assert_called_once_with(
        RetryInfo(
            url=TEST_URL,
            method="GET",
            attempt=2,
            max_retries=DEFAULT_MAX_RETRIES,
            wait_time=DEFAULT_BACKOFF_FACTOR,
            error=None,
            status_code=500,
        )
    )
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


def test_on_retry_callback_with_timeout_exception(
    mock_sleep: Mock, mock_response: httpx.Response
) -> None:
    """Test that on_retry callback receives error information on
    timeout."""
    on_retry_callback = Mock()
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
    assert call_args.url == TEST_URL
    assert call_args.method == "GET"
    assert call_args.attempt == 2  # Next attempt
    assert call_args.max_retries == DEFAULT_MAX_RETRIES
    assert call_args.wait_time == DEFAULT_BACKOFF_FACTOR
    assert isinstance(call_args.error, httpx.TimeoutException)
    assert call_args.status_code is None
    mock_sleep.assert_called_once_with(0.3)


def test_on_retry_callback_with_request_error(
    mock_sleep: Mock, mock_response: httpx.Response
) -> None:
    """Test that on_retry callback receives error information on request
    error."""
    on_retry_callback = Mock()
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
    assert call_args.url == TEST_URL
    assert call_args.method == "GET"
    assert call_args.attempt == 2  # Next attempt
    assert call_args.max_retries == DEFAULT_MAX_RETRIES
    assert call_args.wait_time == DEFAULT_BACKOFF_FACTOR
    assert isinstance(call_args.error, httpx.ConnectError)
    assert call_args.status_code is None
    mock_sleep.assert_called_once_with(0.3)


#########################################
#     Tests for on_success callback     #
#########################################


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
    assert call_args.url == TEST_URL
    assert call_args.method == "GET"
    assert call_args.attempt == 1
    assert call_args.max_retries == DEFAULT_MAX_RETRIES
    assert call_args.response == mock_response
    assert call_args.total_time >= 0
    mock_sleep.assert_not_called()


def test_on_success_callback_after_retries(
    mock_response: httpx.Response, mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_success callback is called after successful
    retry."""
    on_success_callback = Mock()
    mock_request_func = Mock(side_effect=[mock_response_fail, mock_response_fail, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(500,),
        on_success=on_success_callback,
    )

    assert response == mock_response
    on_success_callback.assert_called_once()
    call_args = on_success_callback.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "GET"
    assert call_args.attempt == 3  # Succeeded on third attempt
    assert call_args.max_retries == DEFAULT_MAX_RETRIES
    assert call_args.response == mock_response
    assert call_args.total_time >= 0
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_on_success_callback_not_called_on_failure(
    mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_success callback is not called when request
    fails."""
    on_success_callback = Mock()
    mock_request_func = Mock(return_value=mock_response_fail)

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://api.example.com/data failed with status 500 after 3 attempts",
    ):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            status_forcelist=(500,),
            max_retries=2,
            on_success=on_success_callback,
        )

    on_success_callback.assert_not_called()
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


#########################################
#     Tests for on_failure callback     #
#########################################


def test_on_failure_callback_called_on_retryable_status_failure(
    mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_failure callback is called when retries are
    exhausted."""
    on_failure_callback = Mock()
    mock_request_func = Mock(return_value=mock_response_fail)

    with pytest.raises(HttpRequestError, match=r"GET request to https://api.example.com/data"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            status_forcelist=(500,),
            max_retries=2,
            on_failure=on_failure_callback,
        )

    on_failure_callback.assert_called_once()
    call_args = on_failure_callback.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "GET"
    assert call_args.attempt == 3  # max_retries + 1
    assert call_args.max_retries == 2
    assert isinstance(call_args.error, HttpRequestError)
    assert call_args.status_code == 500
    assert call_args.total_time >= 0
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
    assert isinstance(call_args.error, HttpRequestError)
    assert call_args.status_code is None
    mock_sleep.assert_called_once_with(0.3)


########################################
#     Tests for multiple callbacks     #
########################################


def test_all_callbacks_together_on_success(
    mock_response: httpx.Response, mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that all callbacks work together correctly on successful
    retry."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()

    mock_request_func = Mock(side_effect=[mock_response_fail, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(500,),
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_success=on_success_callback,
        on_failure=on_failure_callback,
    )

    assert response == mock_response
    assert on_request_callback.call_args_list == [
        call(RequestInfo(url=TEST_URL, method="GET", attempt=1, max_retries=DEFAULT_MAX_RETRIES)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=2, max_retries=DEFAULT_MAX_RETRIES)),
    ]
    on_retry_callback.assert_called_once_with(
        RetryInfo(
            url=TEST_URL,
            method="GET",
            attempt=2,
            max_retries=DEFAULT_MAX_RETRIES,
            wait_time=0.3,
            error=None,
            status_code=500,
        )
    )  # One retry
    on_success_callback.assert_called_once()  # One success
    on_failure_callback.assert_not_called()  # No failure
    mock_sleep.assert_called_once_with(0.3)


def test_all_callbacks_together_on_failure(
    mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that all callbacks work together correctly on failure."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()
    mock_request_func = Mock(return_value=mock_response_fail)

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://api.example.com/data failed with status 500 after 3 attempts",
    ):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            status_forcelist=(500,),
            max_retries=2,
            on_request=on_request_callback,
            on_retry=on_retry_callback,
            on_success=on_success_callback,
            on_failure=on_failure_callback,
        )

    assert on_request_callback.call_args_list == [
        call(RequestInfo(url=TEST_URL, method="GET", attempt=1, max_retries=2)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=2, max_retries=2)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=3, max_retries=2)),
    ]
    assert on_retry_callback.call_args_list == [
        call(
            RetryInfo(
                url=TEST_URL,
                method="GET",
                attempt=2,
                max_retries=2,
                wait_time=0.3,
                error=None,
                status_code=500,
            )
        ),
        call(
            RetryInfo(
                url=TEST_URL,
                method="GET",
                attempt=3,
                max_retries=2,
                wait_time=0.6,
                error=None,
                status_code=500,
            )
        ),
    ]
    on_success_callback.assert_not_called()  # No success
    on_failure_callback.assert_called_once()  # One failure
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


#########################################
#     Tests for callback exceptions     #
#########################################


def test_callback_exception_does_not_break_retry_logic(
    mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test that exceptions in callbacks do not break the retry
    logic."""
    on_request_callback = Mock(side_effect=ValueError("callback error"))

    # Should still succeed despite callback exception
    with pytest.raises(ValueError, match=r"callback error"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            on_request=on_request_callback,
        )

    mock_sleep.assert_not_called()


##############################################
#     Tests with custom retry parameters     #
##############################################


def test_callbacks_with_custom_max_retries(
    mock_response: httpx.Response, mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that callbacks receive correct max_retries value."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    mock_request_func = Mock(side_effect=[mock_response_fail, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(500,),
        max_retries=5,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
    )

    assert response == mock_response

    # Check that max_retries is correctly passed
    assert on_request_callback.call_args_list == [
        call(RequestInfo(url=TEST_URL, method="GET", attempt=1, max_retries=5)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=2, max_retries=5)),
    ]
    on_retry_callback.assert_called_once_with(
        RetryInfo(
            url=TEST_URL,
            method="GET",
            attempt=2,
            max_retries=5,
            wait_time=0.3,
            error=None,
            status_code=500,
        )
    )
    mock_sleep.assert_called_once_with(0.3)


def test_callbacks_with_custom_backoff_factor(
    mock_response: httpx.Response, mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_retry callback receives correct wait_time with
    custom backoff."""
    on_retry_callback = Mock()
    mock_request_func = Mock(side_effect=[mock_response_fail, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(500,),
        backoff_factor=2.0,
        on_retry=on_retry_callback,
    )

    assert response == mock_response

    on_retry_callback.assert_called_once_with(
        RetryInfo(
            url=TEST_URL,
            method="GET",
            attempt=2,
            max_retries=DEFAULT_MAX_RETRIES,
            wait_time=2.0,
            error=None,
            status_code=500,
        )
    )
    mock_sleep.assert_called_once_with(2.0)


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

    with patch("aresilient.callbacks.time.time", return_value=105.5):
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

    with patch("aresilient.callbacks.time.time", return_value=110.0):
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
