r"""Unit tests for request_with_automatic_retry function."""

from __future__ import annotations

from unittest.mock import Mock, call

import httpx
import pytest

from aresilient import HttpRequestError
from aresilient.core import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    RETRY_STATUS_CODES,
)
from aresilient.request import request_with_automatic_retry

TEST_URL = "https://api.example.com/data"


##################################################
#     Tests for request_with_automatic_retry     #
##################################################


def test_request_with_automatic_retry_successful_request(
    mock_response: httpx.Response, mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test successful request on first attempt."""
    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
    )

    assert response == mock_response
    mock_request_func.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_with_kwargs(
    mock_response: httpx.Response, mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test that additional kwargs are passed to request function.

    This test uses default values for max_retries, backoff_factor, and
    status_forcelist.
    """
    response = request_with_automatic_retry(
        url=TEST_URL,
        method="POST",
        request_func=mock_request_func,
        json={"key": "value"},
        headers={"Authorization": "Bearer token"},
    )

    assert response == mock_response
    mock_request_func.assert_called_once_with(
        url=TEST_URL,
        json={"key": "value"},
        headers={"Authorization": "Bearer token"},
    )
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_retry_on_retryable_status(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test retry logic when encountering retryable status code."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(503,),
    )

    assert response == mock_response
    assert mock_request_func.call_args_list == [call(url=TEST_URL), call(url=TEST_URL)]
    mock_sleep.assert_called_once_with(0.3)


def test_request_with_automatic_retry_multiple_retries_before_success(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test multiple retries before successful response."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=500)
    mock_request_func = Mock(
        side_effect=[mock_fail_response, mock_fail_response, mock_fail_response, mock_response]
    )

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="POST",
        request_func=mock_request_func,
        status_forcelist=(500,),
    )

    assert response == mock_response
    assert mock_request_func.call_args_list == [
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
    ]
    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_request_with_automatic_retry_max_retries_exceeded(mock_sleep: Mock) -> None:
    """Test that HttpRequestError is raised when max retries
    exceeded."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=502)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://api\.example\.com/data failed with status 502 after 3 attempts",
    ) as exc_info:
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            max_retries=2,
            status_forcelist=(502,),
        )

    assert exc_info.value.status_code == 502
    assert mock_request_func.call_args_list == [
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
    ]
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_request_with_automatic_retry_non_retryable_status_raises_immediately(
    mock_sleep: Mock,
) -> None:
    """Test that non-retryable status codes raise immediately.

    404 is not in the default RETRY_STATUS_CODES, so it should raise
    immediately. This test uses all default parameter values.
    """
    mock_fail_response = Mock(spec=httpx.Response, status_code=404)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://api\.example\.com/data failed with status 404",
    ):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
        )

    mock_request_func.assert_called_once()
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_timeout_exception(mock_sleep: Mock) -> None:
    """Test handling of timeout exception."""
    mock_request_func = Mock(side_effect=httpx.TimeoutException("Request timeout"))

    with pytest.raises(
        HttpRequestError,
        match=r"PUT request to https://api.example.com/data timed out \(1 attempts\)",
    ):
        request_with_automatic_retry(
            url=TEST_URL,
            method="PUT",
            request_func=mock_request_func,
            max_retries=0,
            status_forcelist=(500,),
        )

    mock_request_func.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_timeout_exception_with_retries(
    mock_sleep: Mock,
) -> None:
    """Test timeout exception with retries."""
    mock_request_func = Mock(side_effect=httpx.TimeoutException("Request timeout"))

    with pytest.raises(
        HttpRequestError,
        match=r"PUT request to https://api.example.com/data timed out \(3 attempts\)",
    ):
        request_with_automatic_retry(
            url=TEST_URL,
            method="PUT",
            request_func=mock_request_func,
            max_retries=2,
            status_forcelist=(500,),
        )

    assert mock_request_func.call_args_list == [
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
    ]
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_request_with_automatic_retry_request_error(mock_sleep: Mock) -> None:
    """Test handling of general request errors."""
    mock_request_func = Mock(side_effect=httpx.RequestError("Connection failed"))

    with pytest.raises(
        HttpRequestError,
        match=(
            r"DELETE request to https://api.example.com/data failed after 1 attempts: "
            r"Connection failed"
        ),
    ):
        request_with_automatic_retry(
            url=TEST_URL,
            method="DELETE",
            request_func=mock_request_func,
            max_retries=0,
            status_forcelist=(500,),
        )

    mock_request_func.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_request_error_with_retries(mock_sleep: Mock) -> None:
    """Test handling of general request errors with retries."""
    mock_request_func = Mock(side_effect=httpx.RequestError("Connection failed"))

    with pytest.raises(HttpRequestError, match=r"failed after 2 attempts"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="DELETE",
            request_func=mock_request_func,
            max_retries=1,
            status_forcelist=(500,),
        )

    assert mock_request_func.call_args_list == [call(url=TEST_URL), call(url=TEST_URL)]
    assert mock_sleep.call_args_list == [call(0.3)]


def test_request_with_automatic_retry_zero_max_retries(mock_sleep: Mock) -> None:
    """Test with zero max_retries - should only try once."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=500)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(HttpRequestError, match=r"after 1 attempts"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            max_retries=0,
            status_forcelist=(500,),
        )

    mock_request_func.assert_called_once()
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_zero_backoff_factor(mock_response: httpx.Response) -> None:
    """Test with zero backoff_factor - should not sleep."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        backoff_factor=0.0,
        status_forcelist=(503,),
    )

    assert response == mock_response


@pytest.mark.parametrize("status_code", [200, 201, 202, 204, 206])
def test_request_with_automatic_retry_success_status_2xx(
    mock_sleep: Mock, status_code: int
) -> None:
    """Test that various 2xx status codes are considered successful.

    This test uses default values for max_retries and backoff_factor,
    but specifies a custom status_forcelist.
    """
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_request_func = Mock(return_value=mock_response)

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(500,),
    )

    assert response.status_code == status_code
    mock_request_func.assert_called_once()
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("status_code", [301, 302, 303, 304, 307, 308])
def test_request_with_automatic_retry_success_status_3xx(
    mock_sleep: Mock, status_code: int
) -> None:
    """Test that 3xx redirect status codes are considered successful.

    This test uses default values for max_retries and backoff_factor,
    but specifies a custom status_forcelist.
    """
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_request_func = Mock(return_value=mock_response)

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(500,),
    )

    assert response.status_code == status_code
    mock_request_func.assert_called_once()
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
def test_request_with_automatic_retry_custom_method_names(
    mock_response: httpx.Response, mock_sleep: Mock, method: str
) -> None:
    """Test that different HTTP method names are handled correctly.

    This test uses all default parameter values.
    """
    mock_request_func = Mock(return_value=mock_response)
    request_with_automatic_retry(
        url=TEST_URL,
        method=method,
        request_func=mock_request_func,
    )
    mock_request_func.assert_called_once()
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_empty_status_forcelist(
    mock_sleep: Mock,
) -> None:
    """Test with empty status_forcelist - no status codes should trigger retry."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=500)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://api\.example\.com/data failed with status 500",
    ):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            status_forcelist=(),
        )

    mock_request_func.assert_called_once()
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_preserves_response_object(mock_sleep: Mock) -> None:
    """Test that the response object is preserved in
    HttpRequestError."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_fail_response.json.return_value = {"error": "Service unavailable"}
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(HttpRequestError) as exc_info:
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            max_retries=0,
            status_forcelist=(503,),
        )

    assert exc_info.value.response == mock_fail_response
    assert exc_info.value.response.json() == {"error": "Service unavailable"}
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_large_backoff_factor(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test with large backoff_factor values."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        max_retries=2,
        backoff_factor=10.0,
        status_forcelist=(503,),
    )

    assert response == mock_response
    mock_sleep.assert_called_once_with(10.0)


def test_request_with_automatic_retry_high_max_retries(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test with high max_retries value."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=500)
    # Fail 9 times, succeed on 10th attempt
    side_effects = [mock_fail_response] * 9 + [mock_response]
    mock_request_func = Mock(side_effect=side_effects)

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        max_retries=10,
        backoff_factor=1.0,
        status_forcelist=(500,),
    )

    assert response == mock_response
    assert mock_request_func.call_count == 10
    assert mock_request_func.call_args_list == [
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
        call(url=TEST_URL),
    ]
    assert mock_sleep.call_count == 9
    assert mock_sleep.call_args_list == [
        call(1.0),
        call(2.0),
        call(4.0),
        call(8.0),
        call(16.0),
        call(32.0),
        call(64.0),
        call(128.0),
        call(256.0),
    ]


def test_request_with_automatic_retry_uses_default_max_retries(mock_sleep: Mock) -> None:
    """Test that default max_retries (3) is used when not specified."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://api.example.com/data failed with status 503 after 4 attempts",
    ):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
        )

    # With default  should attempt 4 times total (1 initial + 3 retries)
    assert mock_request_func.call_count == DEFAULT_MAX_RETRIES + 1
    # Should have 3 sleep calls with exponential backoff using default backoff_factor (0.3)
    assert len(mock_sleep.call_args_list) == DEFAULT_MAX_RETRIES


def test_request_with_automatic_retry_uses_default_backoff_factor(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test that default backoff_factor (0.3) is used when not
    specified."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=500)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
    )

    assert response == mock_response
    # Should use default backoff_factor: 0.3 * 2^0 = 0.3
    mock_sleep.assert_called_once_with(DEFAULT_BACKOFF_FACTOR)


@pytest.mark.parametrize("status_code", RETRY_STATUS_CODES)
def test_request_with_automatic_retry_uses_default_status_forcelist(
    mock_response: httpx.Response, mock_sleep: Mock, status_code: int
) -> None:
    """Test that default RETRY_STATUS_CODES are used when not
    specified."""
    # Test each status code in the default RETRY_STATUS_CODES
    mock_fail_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
    )

    assert response == mock_response
    assert mock_request_func.call_args_list == [call(url=TEST_URL), call(url=TEST_URL)]
    mock_sleep.assert_called_once_with(0.3)


def test_request_with_automatic_retry_all_defaults_successful(
    mock_response: httpx.Response, mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test successful request using all default parameter values."""
    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
    )

    assert response == mock_response
    mock_request_func.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_mixed_error_and_status_failures(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test recovery from mix of errors and retryable status codes."""
    mock_request_func = Mock(
        side_effect=[
            httpx.RequestError("Network error"),
            Mock(spec=httpx.Response, status_code=502),
            httpx.TimeoutException("Timeout"),
            mock_response,
        ]
    )

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        max_retries=5,
        status_forcelist=(502,),
    )

    assert response == mock_response
    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.parametrize(
    ("exception", "method", "match_pattern"),
    [
        pytest.param(
            httpx.NetworkError("Network unreachable"),
            "GET",
            r"GET request to https://api\.example\.com/data failed after 4 attempts",
            id="network_error",
        ),
        pytest.param(
            httpx.ReadError("Connection broken"),
            "GET",
            r"GET request to https://api\.example\.com/data failed after 4 attempts",
            id="read_error",
        ),
        pytest.param(
            httpx.WriteError("Write failed"),
            "POST",
            r"POST request to https://api\.example\.com/data failed after 4 attempts",
            id="write_error",
        ),
        pytest.param(
            httpx.ConnectTimeout("Connection timeout"),
            "POST",
            r"POST request to https://api\.example\.com/data timed out \(4 attempts\)",
            id="connect_timeout",
        ),
        pytest.param(
            httpx.ReadTimeout("Read timeout"),
            "DELETE",
            r"DELETE request to https://api\.example\.com/data timed out \(4 attempts\)",
            id="read_timeout",
        ),
        pytest.param(
            httpx.PoolTimeout("Connection pool exhausted"),
            "PATCH",
            r"PATCH request to https://api\.example\.com/data timed out \(4 attempts\)",
            id="pool_timeout",
        ),
        pytest.param(
            httpx.ProxyError("Proxy connection failed"),
            "HEAD",
            r"HEAD request to https://api\.example\.com/data failed after 4 attempts",
            id="proxy_error",
        ),
    ],
)
def test_request_with_automatic_retry_error_types(
    exception: Exception,
    method: str,
    match_pattern: str,
    mock_sleep: Mock,
) -> None:
    """Test that various httpx errors are retried appropriately."""
    mock_request_func = Mock(side_effect=exception)

    with pytest.raises(HttpRequestError, match=match_pattern):
        request_with_automatic_retry(
            url=TEST_URL,
            method=method,
            request_func=mock_request_func,
            status_forcelist=(500,),
        )

    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_request_with_automatic_retry_recovery_after_multiple_failures(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test successful recovery after multiple transient failures."""
    mock_request_func = Mock(
        side_effect=[
            Mock(spec=httpx.Response, status_code=429),
            Mock(spec=httpx.Response, status_code=503),
            Mock(spec=httpx.Response, status_code=500),
            mock_response,
        ]
    )

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        max_retries=5,
        status_forcelist=(429, 500, 503),
    )

    assert response == mock_response
    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_request_with_automatic_retry_error_message_includes_url(mock_sleep: Mock) -> None:
    """Test that error message includes the URL."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(return_value=mock_response)

    with pytest.raises(
        HttpRequestError,
        match=(
            r"GET request to https://api.example.com/data failed with status 503 "
            r"after 1 attempts"
        ),
    ):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            max_retries=0,
            status_forcelist=(503,),
        )

    mock_sleep.assert_not_called()


##########################################################
#     Tests for request_with_automatic_retry retry_if   #
##########################################################


def test_request_with_automatic_retry_retry_if_returns_false_for_success(
    mock_response: httpx.Response, mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test retry_if that returns False for successful response (no
    retry)."""

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
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


def test_request_with_automatic_retry_retry_if_returns_true_for_success(
    mock_sleep: Mock,
) -> None:
    """Test retry_if that returns True even for successful response
    (triggers retry)."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=200, text="success")
    mock_request_func = Mock(return_value=mock_response_ok)

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        # Always retry - should exhaust retries
        return True

    with pytest.raises(HttpRequestError, match=r"failed with status 200 after 4 attempts"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
            max_retries=3,
        )

    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


def test_request_with_automatic_retry_retry_if_checks_response_content(
    mock_sleep: Mock,
) -> None:
    """Test retry_if that checks response content and retries on
    specific text."""
    mock_response_retry = Mock(spec=httpx.Response, status_code=200, text="please retry")
    mock_response_ok = Mock(spec=httpx.Response, status_code=200, text="success")
    mock_request_func = Mock(side_effect=[mock_response_retry, mock_response_ok])

    def retry_predicate(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        # Retry if response contains "retry"
        return bool(response and "retry" in response.text.lower())

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


def test_request_with_automatic_retry_retry_if_returns_false_for_error(
    mock_sleep: Mock,
) -> None:
    """Test retry_if that returns False for error response (no retry,
    immediate fail)."""
    mock_response_error = Mock(spec=httpx.Response, status_code=500)
    mock_request_func = Mock(return_value=mock_response_error)

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        return False  # Never retry

    with pytest.raises(HttpRequestError, match=r"failed with status 500"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
        )

    # Should only try once since retry_if returns False
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_retry_if_returns_true_for_error(
    mock_sleep: Mock,
) -> None:
    """Test retry_if that returns True for error response (triggers
    retry)."""
    mock_response_error = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(side_effect=[mock_response_error, mock_response_ok])

    def retry_predicate(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        return bool(response and response.status_code >= 500)

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


def test_request_with_automatic_retry_retry_if_with_custom_status_logic(
    mock_sleep: Mock,
) -> None:
    """Test retry_if that implements custom status code retry logic."""
    mock_response_429 = Mock(spec=httpx.Response, status_code=429)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(side_effect=[mock_response_429, mock_response_ok])

    def retry_predicate(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        # Only retry on 429
        return bool(response and response.status_code == 429)

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


def test_request_with_automatic_retry_retry_if_does_not_retry_client_error(
    mock_sleep: Mock,
) -> None:
    """Test retry_if that doesn't retry on 404 (client error)."""
    mock_response_404 = Mock(spec=httpx.Response, status_code=404)
    mock_request_func = Mock(return_value=mock_response_404)

    def retry_predicate(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        # Only retry on server errors (5xx)
        return bool(response and 500 <= response.status_code < 600)

    with pytest.raises(HttpRequestError, match=r"failed with status 404"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
        )

    # Should only try once
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_retry_if_returns_false_for_exception(
    mock_sleep: Mock,
) -> None:
    """Test retry_if that returns False for exceptions (no retry)."""
    mock_request_func = Mock(side_effect=httpx.TimeoutException("timeout"))

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        return False  # Never retry

    with pytest.raises(HttpRequestError, match=r"timed out"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
        )

    # Should only try once
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_retry_if_returns_true_for_exception(
    mock_sleep: Mock,
) -> None:
    """Test retry_if that returns True for exceptions (triggers
    retry)."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(side_effect=[httpx.TimeoutException("timeout"), mock_response_ok])

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,
    ) -> bool:
        # Retry on timeout exceptions
        return bool(isinstance(exception, httpx.TimeoutException))

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


def test_request_with_automatic_retry_retry_if_with_connection_error(
    mock_sleep: Mock,
) -> None:
    """Test retry_if that handles connection errors."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(
        side_effect=[httpx.ConnectError("connection failed"), mock_response_ok]
    )

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,
    ) -> bool:
        # Retry on connection errors
        return bool(isinstance(exception, httpx.ConnectError))

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


def test_request_with_automatic_retry_retry_if_exhausts_retries_with_exception(
    mock_sleep: Mock,
) -> None:
    """Test retry_if exhausts retries when exception keeps occurring."""
    mock_request_func = Mock(side_effect=httpx.TimeoutException("timeout"))

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,
    ) -> bool:
        # Always retry timeouts
        return bool(isinstance(exception, httpx.TimeoutException))

    with pytest.raises(HttpRequestError, match=r"timed out"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            retry_if=retry_predicate,
            max_retries=2,
        )

    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_request_with_automatic_retry_retry_if_complex_logic(mock_sleep: Mock) -> None:
    """Test retry_if with complex custom logic combining response and
    exception checks."""
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
        return bool(isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)))

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_request_with_automatic_retry_retry_if_none_uses_default_behavior(
    mock_sleep: Mock,
) -> None:
    """Test that when retry_if is None, default status_forcelist
    behavior is used."""
    mock_response_503 = Mock(spec=httpx.Response, status_code=503)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = Mock(side_effect=[mock_response_503, mock_response_ok])

    # No retry_if provided - should use default behavior
    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        status_forcelist=(503,),
        max_retries=3,
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)
