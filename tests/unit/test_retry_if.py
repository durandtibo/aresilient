r"""Parametrized unit tests for retry_if custom predicate functionality.

This test module uses pytest parametrization to test retry_if
functionality across all HTTP methods (GET, POST, PUT, DELETE, PATCH,
HEAD, OPTIONS) in a consistent and maintainable way.
"""

from __future__ import annotations

from unittest.mock import Mock, call

import httpx
import pytest

from aresilient import HttpRequestError
from tests.helpers import (
    HTTP_METHODS,
    HttpMethodTestCase,
    create_mock_client_with_side_effect,
    setup_mock_client_for_method,
)

TEST_URL = "https://api.example.com/data"


########################################################
#     Tests for retry_if with successful responses     #
########################################################


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_returns_false_for_successful_response(
    test_case: HttpMethodTestCase, mock_sleep: Mock
) -> None:
    """Test retry_if that returns False for successful response (no
    retry)."""
    mock_client, mock_response = setup_mock_client_for_method(
        test_case.client_method, test_case.status_code, {"text": "success"}
    )

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        return False

    response = test_case.method_func(TEST_URL, client=mock_client, retry_if=retry_predicate)

    assert response == mock_response
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_returns_true_for_successful_response(
    test_case: HttpMethodTestCase, mock_sleep: Mock
) -> None:
    """Test retry_if that returns True even for successful response
    (triggers retry)."""
    mock_client, mock_response_ok = setup_mock_client_for_method(
        test_case.client_method, test_case.status_code, {"text": "success"}
    )

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        # Always retry - should exhaust retries
        return True

    with pytest.raises(
        HttpRequestError, match=f"failed with status {test_case.status_code} after 4 attempts"
    ):
        test_case.method_func(TEST_URL, client=mock_client, retry_if=retry_predicate, max_retries=3)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6), call(1.2)]


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_checks_response_content(test_case: HttpMethodTestCase, mock_sleep: Mock) -> None:
    """Test retry_if that checks response content and retries on
    specific text."""
    mock_response_retry = Mock(
        spec=httpx.Response, status_code=test_case.status_code, text="please retry"
    )
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.status_code, text="success")
    mock_client, _ = create_mock_client_with_side_effect(
        test_case.client_method, [mock_response_retry, mock_response_ok]
    )

    def retry_predicate(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        # Retry if response contains "retry"
        return bool(response and "retry" in response.text.lower())

    response = test_case.method_func(
        TEST_URL, client=mock_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


#####################################################
#     Tests for retry_if with error responses       #
#####################################################


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_returns_false_for_error_response(
    test_case: HttpMethodTestCase, mock_sleep: Mock
) -> None:
    """Test retry_if that returns False for error response (no retry,
    immediate fail)."""
    mock_client, mock_response_error = setup_mock_client_for_method(test_case.client_method, 500)

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        return False  # Never retry

    with pytest.raises(HttpRequestError, match=r"failed with status 500"):
        test_case.method_func(TEST_URL, client=mock_client, retry_if=retry_predicate)

    # Should only try once since retry_if returns False
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_returns_true_for_error_response(
    test_case: HttpMethodTestCase, mock_sleep: Mock
) -> None:
    """Test retry_if that returns True for error response (triggers
    retry)."""
    mock_response_error = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client, _ = create_mock_client_with_side_effect(
        test_case.client_method, [mock_response_error, mock_response_ok]
    )

    def retry_predicate(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        return bool(response and response.status_code >= 500)

    response = test_case.method_func(
        TEST_URL, client=mock_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_with_status_code_logic(test_case: HttpMethodTestCase, mock_sleep: Mock) -> None:
    """Test retry_if that implements custom status code retry logic."""
    mock_response_429 = Mock(spec=httpx.Response, status_code=429)
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client, _ = create_mock_client_with_side_effect(
        test_case.client_method, [mock_response_429, mock_response_ok]
    )

    def retry_predicate(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        # Only retry on 429
        return bool(response and response.status_code == 429)

    response = test_case.method_func(
        TEST_URL, client=mock_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_does_not_retry_non_retryable_status(
    test_case: HttpMethodTestCase, mock_sleep: Mock
) -> None:
    """Test retry_if that doesn't retry on 404 (client error)."""
    mock_client, mock_response_404 = setup_mock_client_for_method(test_case.client_method, 404)

    def retry_predicate(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        # Only retry on server errors (5xx)
        return bool(response and 500 <= response.status_code < 600)

    with pytest.raises(HttpRequestError, match=r"failed with status 404"):
        test_case.method_func(TEST_URL, client=mock_client, retry_if=retry_predicate)

    # Should only try once
    mock_sleep.assert_not_called()


###################################################
#     Tests for retry_if with exceptions          #
###################################################


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_returns_false_for_exception(
    test_case: HttpMethodTestCase, mock_sleep: Mock
) -> None:
    """Test retry_if that returns False for exceptions (no retry)."""
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client, test_case.client_method, Mock(side_effect=httpx.TimeoutException("timeout"))
    )

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        return False  # Never retry

    with pytest.raises(HttpRequestError, match=r"timed out"):
        test_case.method_func(TEST_URL, client=mock_client, retry_if=retry_predicate)

    # Should only try once
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_returns_true_for_exception(
    test_case: HttpMethodTestCase, mock_sleep: Mock
) -> None:
    """Test retry_if that returns True for exceptions (triggers
    retry)."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client, _ = create_mock_client_with_side_effect(
        test_case.client_method, [httpx.TimeoutException("timeout"), mock_response_ok]
    )

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,
    ) -> bool:
        # Retry on timeout exceptions
        return bool(isinstance(exception, httpx.TimeoutException))

    response = test_case.method_func(
        TEST_URL, client=mock_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_with_connection_error(test_case: HttpMethodTestCase, mock_sleep: Mock) -> None:
    """Test retry_if that handles connection errors."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        test_case.client_method,
        Mock(side_effect=[httpx.ConnectError("connection failed"), mock_response_ok]),
    )

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,
    ) -> bool:
        # Retry on connection errors
        return bool(isinstance(exception, httpx.ConnectError))

    response = test_case.method_func(
        TEST_URL, client=mock_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_exhausts_retries_with_exception(
    test_case: HttpMethodTestCase, mock_sleep: Mock
) -> None:
    """Test retry_if exhausts retries when exception keeps occurring."""
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client, test_case.client_method, Mock(side_effect=httpx.TimeoutException("timeout"))
    )

    def retry_predicate(
        response: httpx.Response | None,  # noqa: ARG001
        exception: Exception | None,
    ) -> bool:
        # Always retry timeouts
        return bool(isinstance(exception, httpx.TimeoutException))

    with pytest.raises(HttpRequestError, match=r"timed out"):
        test_case.method_func(TEST_URL, client=mock_client, retry_if=retry_predicate, max_retries=2)

    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


#########################################################
#     Tests for retry_if with mixed scenarios           #
#########################################################


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_complex_logic(test_case: HttpMethodTestCase, mock_sleep: Mock) -> None:
    """Test retry_if with complex custom logic combining response and
    exception checks."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500, text="server error")
    mock_response_200_retry = Mock(spec=httpx.Response, status_code=200, text="rate limit exceeded")
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.status_code, text="success")

    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        test_case.client_method,
        Mock(side_effect=[mock_response_500, mock_response_200_retry, mock_response_ok]),
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

    response = test_case.method_func(
        TEST_URL, client=mock_client, retry_if=retry_predicate, max_retries=3
    )

    assert response == mock_response_ok
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_none_uses_default_behavior(
    test_case: HttpMethodTestCase, mock_sleep: Mock
) -> None:
    """Test that when retry_if is None, default status_forcelist
    behavior is used."""
    mock_response_503 = Mock(spec=httpx.Response, status_code=503)
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        test_case.client_method,
        Mock(side_effect=[mock_response_503, mock_response_ok]),
    )

    # No retry_if provided - should use default behavior
    response = test_case.method_func(
        TEST_URL, client=mock_client, status_forcelist=(503,), max_retries=3
    )

    assert response == mock_response_ok
    mock_sleep.assert_called_once_with(0.3)


############################################
#     Tests for retry_if with callbacks    #
############################################


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_with_on_retry_callback(test_case: HttpMethodTestCase, mock_sleep: Mock) -> None:
    """Test retry_if works correctly with on_retry callback."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        test_case.client_method,
        Mock(side_effect=[mock_response_500, mock_response_ok]),
    )

    retry_callback = Mock()

    def retry_predicate(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        return bool(response and response.status_code >= 500)

    response = test_case.method_func(
        TEST_URL,
        client=mock_client,
        retry_if=retry_predicate,
        on_retry=retry_callback,
        max_retries=3,
    )

    assert response == mock_response_ok
    retry_callback.assert_called_once()
    mock_sleep.assert_called_once_with(0.3)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_retry_if_with_on_failure_callback(test_case: HttpMethodTestCase, mock_sleep: Mock) -> None:
    """Test retry_if triggers on_failure callback when retries
    exhausted."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response_500))

    failure_callback = Mock()

    def retry_predicate(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        return bool(response and response.status_code >= 500)

    with pytest.raises(HttpRequestError):
        test_case.method_func(
            TEST_URL,
            client=mock_client,
            retry_if=retry_predicate,
            on_failure=failure_callback,
            max_retries=2,
        )

    failure_callback.assert_called_once()
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]
