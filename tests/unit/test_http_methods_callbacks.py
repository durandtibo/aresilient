r"""Parametrized unit tests for callback functionality in all HTTP method wrappers.

This test module uses pytest parametrization to test callback functionality
across all HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS) in a
consistent and maintainable way.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

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

TEST_URL = "https://api.example.com/data"


# Define test parameters for all HTTP methods
HTTP_METHODS = [
    pytest.param(
        "GET",
        get_with_automatic_retry,
        "get",
        200,
        id="GET",
    ),
    pytest.param(
        "POST",
        post_with_automatic_retry,
        "post",
        201,
        id="POST",
    ),
    pytest.param(
        "PUT",
        put_with_automatic_retry,
        "put",
        200,
        id="PUT",
    ),
    pytest.param(
        "DELETE",
        delete_with_automatic_retry,
        "delete",
        204,
        id="DELETE",
    ),
    pytest.param(
        "PATCH",
        patch_with_automatic_retry,
        "patch",
        200,
        id="PATCH",
    ),
    pytest.param(
        "HEAD",
        head_with_automatic_retry,
        "head",
        200,
        id="HEAD",
    ),
    pytest.param(
        "OPTIONS",
        options_with_automatic_retry,
        "options",
        200,
        id="OPTIONS",
    ),
]


##################################################
#     Parametrized Tests for HTTP Methods       #
#     with callback functionality               #
##################################################


@pytest.mark.parametrize("method_name,method_func,client_method,success_code", HTTP_METHODS)
def test_http_method_on_request_callback(
    method_name: str,
    method_func,
    client_method: str,
    success_code: int,
    mock_sleep: Mock,
) -> None:
    """Test that on_request callback is called for all HTTP methods."""
    on_request_callback = Mock()
    mock_response = Mock(spec=httpx.Response, status_code=success_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, client_method, Mock(return_value=mock_response))

    response = method_func(
        TEST_URL, client=mock_client, on_request=on_request_callback
    )

    assert response.status_code == success_code
    on_request_callback.assert_called_once()
    call_args = on_request_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == method_name
    assert call_args["attempt"] == 1


@pytest.mark.parametrize("method_name,method_func,client_method,success_code", HTTP_METHODS)
def test_http_method_on_success_callback(
    method_name: str,
    method_func,
    client_method: str,
    success_code: int,
    mock_sleep: Mock,
) -> None:
    """Test that on_success callback is called for successful HTTP requests."""
    on_success_callback = Mock()
    mock_response = Mock(spec=httpx.Response, status_code=success_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, client_method, Mock(return_value=mock_response))

    response = method_func(
        TEST_URL, client=mock_client, on_success=on_success_callback
    )

    assert response.status_code == success_code
    on_success_callback.assert_called_once()
    call_args = on_success_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == method_name
    assert call_args["response"].status_code == success_code


@pytest.mark.parametrize("method_name,method_func,client_method,success_code", HTTP_METHODS)
def test_http_method_on_retry_callback(
    method_name: str,
    method_func,
    client_method: str,
    success_code: int,
    mock_sleep: Mock,
) -> None:
    """Test that on_retry callback is called when HTTP request is retried."""
    on_retry_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_success_response = Mock(spec=httpx.Response, status_code=success_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        client_method,
        Mock(side_effect=[mock_fail_response, mock_success_response]),
    )

    response = method_func(
        TEST_URL, client=mock_client, on_retry=on_retry_callback
    )

    assert response.status_code == success_code
    on_retry_callback.assert_called_once()
    call_args = on_retry_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == method_name
    assert call_args["status_code"] == 503


@pytest.mark.parametrize("method_name,method_func,client_method,success_code", HTTP_METHODS)
def test_http_method_on_failure_callback(
    method_name: str,
    method_func,
    client_method: str,
    success_code: int,
    mock_sleep: Mock,
) -> None:
    """Test that on_failure callback is called when retries are exhausted."""
    on_failure_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, client_method, Mock(return_value=mock_fail_response))

    with pytest.raises(HttpRequestError):
        method_func(
            TEST_URL,
            client=mock_client,
            max_retries=2,
            on_failure=on_failure_callback,
        )

    on_failure_callback.assert_called_once()
    call_args = on_failure_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == method_name
    assert call_args["status_code"] == 503


@pytest.mark.parametrize("method_name,method_func,client_method,success_code", HTTP_METHODS)
def test_http_method_all_callbacks_together(
    method_name: str,
    method_func,
    client_method: str,
    success_code: int,
    mock_sleep: Mock,
) -> None:
    """Test that all callbacks work together for HTTP requests."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()

    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_success_response = Mock(spec=httpx.Response, status_code=success_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        client_method,
        Mock(side_effect=[mock_fail_response, mock_success_response]),
    )

    response = method_func(
        TEST_URL,
        client=mock_client,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_success=on_success_callback,
        on_failure=on_failure_callback,
    )

    assert response.status_code == success_code
    assert on_request_callback.call_count == 2  # Two attempts
    on_retry_callback.assert_called_once()  # One retry
    on_success_callback.assert_called_once()  # One success
    on_failure_callback.assert_not_called()  # No failure


@pytest.mark.parametrize("method_name,method_func,client_method,success_code", HTTP_METHODS)
def test_http_method_callbacks_with_timeout_error(
    method_name: str,
    method_func,
    client_method: str,
    success_code: int,
    mock_sleep: Mock,
) -> None:
    """Test that callbacks work when HTTP request times out."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_failure_callback = Mock()

    mock_success_response = Mock(spec=httpx.Response, status_code=success_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        client_method,
        Mock(side_effect=[httpx.TimeoutException("timeout"), mock_success_response]),
    )

    response = method_func(
        TEST_URL,
        client=mock_client,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_failure=on_failure_callback,
    )

    assert response.status_code == success_code
    assert on_request_callback.call_count == 2
    on_retry_callback.assert_called_once()

    # Check that retry callback received error info
    retry_call_args = on_retry_callback.call_args[0][0]
    assert isinstance(retry_call_args["error"], httpx.TimeoutException)


@pytest.mark.parametrize("method_name,method_func,client_method,success_code", HTTP_METHODS)
def test_http_method_callbacks_with_default_client(
    method_name: str,
    method_func,
    client_method: str,
    success_code: int,
    mock_sleep: Mock,
) -> None:
    """Test that callbacks work with default client (not provided)."""
    on_request_callback = Mock()
    on_success_callback = Mock()

    mock_response = Mock(spec=httpx.Response, status_code=success_code)
    with patch(f"httpx.Client.{client_method}", return_value=mock_response):
        response = method_func(
            TEST_URL,
            on_request=on_request_callback,
            on_success=on_success_callback,
        )

    assert response.status_code == success_code
    on_request_callback.assert_called_once()
    on_success_callback.assert_called_once()
