r"""Unit tests for request_with_automatic_retry function."""

from __future__ import annotations

from unittest.mock import Mock, call

import httpx
import pytest

from aresnet import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    RETRY_STATUS_CODES,
    HttpRequestError,
)
from aresnet.request import request_with_automatic_retry

TEST_URL = "https://api.example.com/data"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200)


@pytest.fixture
def mock_request_func(mock_response: httpx.Response) -> Mock:
    return Mock(return_value=mock_response)


#######################################################
#     Tests for request_with_automatic_retry         #
#######################################################


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
    
    This test uses default values for max_retries, backoff_factor, and status_forcelist.
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
        max_retries=3,
        backoff_factor=0.5,
        status_forcelist=(503,),
    )

    assert response == mock_response
    assert mock_request_func.call_count == 2
    mock_sleep.assert_called_once_with(0.5)


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
        max_retries=5,
        backoff_factor=1.0,
        status_forcelist=(500,),
    )

    assert response == mock_response
    assert mock_request_func.call_count == 4
    # Exponential backoff: 1.0 * 2^0, 1.0 * 2^1, 1.0 * 2^2
    assert mock_sleep.call_args_list == [call(1.0), call(2.0), call(4.0)]


def test_request_with_automatic_retry_max_retries_exceeded(mock_sleep: Mock) -> None:
    """Test that HttpRequestError is raised when max retries
    exceeded."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=502)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(HttpRequestError) as exc_info:
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            max_retries=2,
            backoff_factor=0.2,
            status_forcelist=(502,),
        )

    assert exc_info.value.status_code == 502
    assert "failed with status 502 after 3 attempts" in str(exc_info.value)
    assert mock_request_func.call_count == 3
    assert mock_sleep.call_args_list == [call(0.2), call(0.4)]


def test_request_with_automatic_retry_non_retryable_status_raises_immediately(
    mock_sleep: Mock,
) -> None:
    """Test that non-retryable status codes raise immediately.
    
    404 is not in the default RETRY_STATUS_CODES, so it should raise immediately.
    This test uses all default parameter values.
    """
    mock_fail_response = Mock(spec=httpx.Response, status_code=404)
    mock_fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=Mock(), response=mock_fail_response
    )
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(httpx.HTTPStatusError, match="Not Found"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
        )

    mock_request_func.assert_called_once()
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_timeout_exception(mock_sleep: Mock) -> None:
    """Test handling of timeout exception."""
    mock_request_func = Mock(side_effect=httpx.TimeoutException("Timeout"))

    with pytest.raises(HttpRequestError, match="timed out") as exc_info:
        request_with_automatic_retry(
            url=TEST_URL,
            method="PUT",
            request_func=mock_request_func,
            max_retries=2,
            backoff_factor=0.5,
            status_forcelist=(500,),
        )

    assert exc_info.value.status_code is None
    assert mock_request_func.call_count == 3
    assert mock_sleep.call_args_list == [call(0.5), call(1.0)]


def test_request_with_automatic_retry_request_error(mock_sleep: Mock) -> None:
    """Test handling of general request errors."""
    mock_request_func = Mock(side_effect=httpx.RequestError("Network error"))

    with pytest.raises(HttpRequestError, match="failed after") as exc_info:
        request_with_automatic_retry(
            url=TEST_URL,
            method="DELETE",
            request_func=mock_request_func,
            max_retries=1,
            backoff_factor=0.1,
            status_forcelist=(500,),
        )

    assert exc_info.value.status_code is None
    assert mock_request_func.call_count == 2
    assert mock_sleep.call_args_list == [call(0.1)]


def test_request_with_automatic_retry_zero_max_retries(mock_sleep: Mock) -> None:
    """Test with zero max_retries - should only try once."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=500)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(HttpRequestError, match="after 1 attempts"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            max_retries=0,
            backoff_factor=0.3,
            status_forcelist=(500,),
        )

    mock_request_func.assert_called_once()
    mock_sleep.assert_not_called()


def test_request_with_automatic_retry_zero_backoff_factor(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test with zero backoff_factor - should not sleep."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])

    response = request_with_automatic_retry(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        max_retries=3,
        backoff_factor=0.0,
        status_forcelist=(503,),
    )

    assert response == mock_response
    mock_sleep.assert_called_once_with(0.0)


def test_request_with_automatic_retry_success_status_2xx(
    mock_sleep: Mock,
) -> None:
    """Test that various 2xx status codes are considered successful.
    
    This test uses default values for max_retries and backoff_factor,
    but specifies a custom status_forcelist.
    """
    for status_code in [200, 201, 202, 204]:
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


def test_request_with_automatic_retry_success_status_3xx(
    mock_sleep: Mock,
) -> None:
    """Test that 3xx redirect status codes are considered successful.
    
    This test uses default values for max_retries and backoff_factor,
    but specifies a custom status_forcelist.
    """
    for status_code in [301, 302, 304]:
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


def test_request_with_automatic_retry_custom_method_names(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test that different HTTP method names are handled correctly.
    
    This test uses all default parameter values.
    """
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]:
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
    mock_fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=Mock(), response=mock_fail_response
    )
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(httpx.HTTPStatusError, match="Server Error"):
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            max_retries=3,
            backoff_factor=0.3,
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
            backoff_factor=0.3,
            status_forcelist=(503,),
        )

    assert exc_info.value.response == mock_fail_response
    assert exc_info.value.response.json() == {"error": "Service unavailable"}


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
        backoff_factor=0.1,
        status_forcelist=(500,),
    )

    assert response == mock_response
    assert mock_request_func.call_count == 10
    assert len(mock_sleep.call_args_list) == 9


def test_request_with_automatic_retry_uses_default_max_retries(mock_sleep: Mock) -> None:
    """Test that default max_retries (3) is used when not specified."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_request_func = Mock(return_value=mock_fail_response)

    with pytest.raises(HttpRequestError) as exc_info:
        request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
        )

    # With default max_retries=3, should attempt 4 times total (1 initial + 3 retries)
    assert mock_request_func.call_count == DEFAULT_MAX_RETRIES + 1
    assert f"after {DEFAULT_MAX_RETRIES + 1} attempts" in str(exc_info.value)
    # Should have 3 sleep calls with exponential backoff using default backoff_factor (0.3)
    assert len(mock_sleep.call_args_list) == DEFAULT_MAX_RETRIES


def test_request_with_automatic_retry_uses_default_backoff_factor(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test that default backoff_factor (0.3) is used when not specified."""
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


def test_request_with_automatic_retry_uses_default_status_forcelist(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test that default RETRY_STATUS_CODES are used when not specified."""
    # Test each status code in the default RETRY_STATUS_CODES
    for status_code in RETRY_STATUS_CODES:
        mock_fail_response = Mock(spec=httpx.Response, status_code=status_code)
        mock_request_func = Mock(side_effect=[mock_fail_response, mock_response])
        
        response = request_with_automatic_retry(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
        )
        
        assert response == mock_response
        # Should retry since status_code is in default RETRY_STATUS_CODES
        assert mock_request_func.call_count == 2
        mock_request_func.reset_mock()
    
    # Verify that we tested all expected status codes
    assert len(mock_sleep.call_args_list) == len(RETRY_STATUS_CODES)


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
