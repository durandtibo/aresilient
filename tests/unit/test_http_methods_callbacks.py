r"""Parametrized unit tests for callback functionality in all HTTP method
wrappers.

This test module uses pytest parametrization to test callback
functionality across all HTTP methods (GET, POST, PUT, DELETE, PATCH,
HEAD, OPTIONS) in a consistent and maintainable way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import Mock, call, patch

import httpx
import pytest

from aresilient import (
    HttpRequestError,
    delete_with_automatic_retry,
    get_with_automatic_retry,
    head_with_automatic_retry,
    options_with_automatic_retry,
    patch_with_automatic_retry,
    post_with_automatic_retry,
    put_with_automatic_retry,
)

if TYPE_CHECKING:
    from collections.abc import Callable

TEST_URL = "https://api.example.com/data"


@dataclass
class HttpMethodTestCase:
    """Test case definition for HTTP method testing.

    Attributes:
        method_name: The HTTP method name (e.g., "GET", "POST").
        method_func: The function to test (e.g., get_with_automatic_retry).
        client_method: The httpx.Client method name (e.g., "get", "post").
        status_code: Expected success status code. Optional, not used in all tests.
    """

    method_name: str
    method_func: Callable[..., httpx.Response]
    client_method: str
    status_code: int | None = None


# Define test parameters for all HTTP methods
HTTP_METHODS = [
    pytest.param(
        HttpMethodTestCase("GET", get_with_automatic_retry, "get", 200),
        id="GET",
    ),
    pytest.param(
        HttpMethodTestCase("POST", post_with_automatic_retry, "post", 201),
        id="POST",
    ),
    pytest.param(
        HttpMethodTestCase("PUT", put_with_automatic_retry, "put", 200),
        id="PUT",
    ),
    pytest.param(
        HttpMethodTestCase("DELETE", delete_with_automatic_retry, "delete", 204),
        id="DELETE",
    ),
    pytest.param(
        HttpMethodTestCase("PATCH", patch_with_automatic_retry, "patch", 200),
        id="PATCH",
    ),
    pytest.param(
        HttpMethodTestCase("HEAD", head_with_automatic_retry, "head", 200),
        id="HEAD",
    ),
    pytest.param(
        HttpMethodTestCase("OPTIONS", options_with_automatic_retry, "options", 200),
        id="OPTIONS",
    ),
]


##################################################
#     Parametrized Tests for HTTP Methods       #
#     with callback functionality               #
##################################################


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_http_method_on_request_callback(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that on_request callback is called for all HTTP methods."""
    on_request_callback = Mock()
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    response = test_case.method_func(TEST_URL, client=mock_client, on_request=on_request_callback)

    assert response.status_code == test_case.status_code
    on_request_callback.assert_called_once()
    call_args = on_request_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == test_case.method_name
    assert call_args["attempt"] == 1
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_http_method_on_success_callback(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that on_success callback is called for successful HTTP
    requests."""
    on_success_callback = Mock()
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    response = test_case.method_func(TEST_URL, client=mock_client, on_success=on_success_callback)

    assert response.status_code == test_case.status_code
    on_success_callback.assert_called_once()
    call_args = on_success_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == test_case.method_name
    assert call_args["response"].status_code == test_case.status_code
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_http_method_on_retry_callback(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that on_retry callback is called when HTTP request is
    retried."""
    on_retry_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_success_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        test_case.client_method,
        Mock(side_effect=[mock_fail_response, mock_success_response]),
    )

    response = test_case.method_func(TEST_URL, client=mock_client, on_retry=on_retry_callback)

    assert response.status_code == test_case.status_code
    on_retry_callback.assert_called_once()
    call_args = on_retry_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == test_case.method_name
    assert call_args["status_code"] == 503
    mock_sleep.assert_called_once_with(0.3)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_http_method_on_failure_callback(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that on_failure callback is called when retries are
    exhausted."""
    on_failure_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_fail_response))

    with pytest.raises(HttpRequestError):
        test_case.method_func(
            TEST_URL,
            client=mock_client,
            max_retries=2,
            on_failure=on_failure_callback,
        )

    on_failure_callback.assert_called_once()
    call_args = on_failure_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == test_case.method_name
    assert call_args["status_code"] == 503
    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_http_method_all_callbacks_together(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that all callbacks work together for HTTP requests."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()

    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_success_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        test_case.client_method,
        Mock(side_effect=[mock_fail_response, mock_success_response]),
    )

    response = test_case.method_func(
        TEST_URL,
        client=mock_client,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_success=on_success_callback,
        on_failure=on_failure_callback,
    )

    assert response.status_code == test_case.status_code
    assert on_request_callback.call_count == 2  # Two attempts
    on_retry_callback.assert_called_once()  # One retry
    on_success_callback.assert_called_once()  # One success
    on_failure_callback.assert_not_called()  # No failure
    mock_sleep.assert_called_once_with(0.3)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_http_method_callbacks_with_timeout_error(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that callbacks work when HTTP request times out."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_failure_callback = Mock()

    mock_success_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        test_case.client_method,
        Mock(side_effect=[httpx.TimeoutException("timeout"), mock_success_response]),
    )

    response = test_case.method_func(
        TEST_URL,
        client=mock_client,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_failure=on_failure_callback,
    )

    assert response.status_code == test_case.status_code
    assert on_request_callback.call_count == 2
    on_retry_callback.assert_called_once()

    # Check that retry callback received error info
    retry_call_args = on_retry_callback.call_args[0][0]
    assert isinstance(retry_call_args["error"], httpx.TimeoutException)
    mock_sleep.assert_called_once_with(0.3)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_http_method_callbacks_with_default_client(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that callbacks work with default client (not provided)."""
    on_request_callback = Mock()
    on_success_callback = Mock()

    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    with patch(f"httpx.Client.{test_case.client_method}", return_value=mock_response):
        response = test_case.method_func(
            TEST_URL,
            on_request=on_request_callback,
            on_success=on_success_callback,
        )

    assert response.status_code == test_case.status_code
    on_request_callback.assert_called_once()
    on_success_callback.assert_called_once()
    mock_sleep.assert_not_called()
