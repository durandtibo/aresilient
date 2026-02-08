r"""Unit tests for retry_if_handler module."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx
import pytest

from aresilient.exceptions import HttpRequestError
from aresilient.utils.retry_if_handler import (
    handle_exception_with_retry_if,
    handle_response_with_retry_if,
)

if TYPE_CHECKING:
    from aresilient.callbacks import FailureInfo


def retry_if_false(
    resp: httpx.Response | None,  # noqa: ARG001
    exc: Exception | None,  # noqa: ARG001
) -> bool:
    """Do not retry if exception occurs."""
    return False


def retry_if_true(
    resp: httpx.Response | None,  # noqa: ARG001
    exc: Exception | None,  # noqa: ARG001
) -> bool:
    """Retry if exception occurs."""
    return False


def test_handle_response_success_retry_if_returns_false() -> None:
    """Test successful response when retry_if returns False."""
    response = httpx.Response(200, content=b"OK")

    result = handle_response_with_retry_if(
        response,
        retry_if=retry_if_false,
        url="https://example.com",
        method="GET",
    )

    assert result is False


def test_handle_response_success_retry_if_returns_true() -> None:
    """Test successful response when retry_if returns True (retry even
    on success)."""
    response = httpx.Response(200, content=b"OK")

    result = handle_response_with_retry_if(
        response,
        retry_if=retry_if_true,
        url="https://example.com",
        method="GET",
    )

    assert result is True


def test_handle_response_error_retry_if_returns_true() -> None:
    """Test error response when retry_if returns True (should retry)."""
    response = httpx.Response(500, content=b"Server Error")

    result = handle_response_with_retry_if(
        response,
        retry_if=retry_if_true,
        url="https://example.com",
        method="GET",
    )

    assert result is True


def test_handle_response_error_retry_if_returns_false() -> None:
    """Test error response when retry_if returns False (raise error)."""
    response = httpx.Response(400, content=b"Bad Request")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_response_with_retry_if(
            response,
            retry_if=retry_if_false,
            url="https://example.com",
            method="GET",
        )

    error = exc_info.value
    assert error.method == "GET"
    assert error.url == "https://example.com"
    assert error.status_code == 400
    assert error.response is response
    assert "failed with status 400" in str(error)


def test_handle_response_different_status_codes() -> None:
    """Test with various status codes."""
    # Test 3xx success
    response = httpx.Response(301, content=b"Moved")

    result = handle_response_with_retry_if(
        response,
        retry_if=retry_if_false,
        url="https://example.com",
        method="GET",
    )
    assert result is False

    # Test 5xx error
    response_500 = httpx.Response(503, content=b"Service Unavailable")

    result = handle_response_with_retry_if(
        response_500,
        retry_if=retry_if_true,
        url="https://example.com",
        method="POST",
    )
    assert result is True


def test_handle_exception_timeout_retry_if_returns_true_with_attempts_remaining() -> None:
    """Test TimeoutException when retry_if returns True and attempts
    remain."""
    exc = httpx.TimeoutException("Request timed out")

    result = handle_exception_with_retry_if(
        exc,
        retry_if=retry_if_true,
        url="https://example.com",
        method="GET",
        attempt=0,
        max_retries=3,
        on_failure=None,
        start_time=time.time(),
    )

    assert result is True


def test_handle_exception_timeout_retry_if_returns_false() -> None:
    """Test TimeoutException when retry_if returns False."""
    exc = httpx.TimeoutException("Request timed out")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_exception_with_retry_if(
            exc,
            retry_if=retry_if_false,
            url="https://example.com",
            method="POST",
            attempt=0,
            max_retries=3,
            on_failure=None,
            start_time=time.time(),
        )

    error = exc_info.value
    assert error.method == "POST"
    assert error.url == "https://example.com"
    assert "timed out" in str(error)
    assert error.__cause__ is exc


def test_handle_exception_timeout_max_retries_reached() -> None:
    """Test TimeoutException when max retries is reached."""
    exc = httpx.TimeoutException("Request timed out")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_exception_with_retry_if(
            exc,
            retry_if=retry_if_true,
            url="https://example.com",
            method="GET",
            attempt=3,
            max_retries=3,
            on_failure=None,
            start_time=time.time(),
        )

    error = exc_info.value
    assert error.method == "GET"
    assert "timed out" in str(error)
    assert "(4 attempts)" in str(error)


def test_handle_exception_request_error_retry_if_returns_true() -> None:
    """Test RequestError when retry_if returns True."""
    exc = httpx.ConnectError("Connection failed")

    result = handle_exception_with_retry_if(
        exc,
        retry_if=retry_if_true,
        url="https://example.com",
        method="GET",
        attempt=1,
        max_retries=5,
        on_failure=None,
        start_time=time.time(),
    )

    assert result is True


def test_handle_exception_request_error_retry_if_returns_false() -> None:
    """Test RequestError when retry_if returns False."""
    exc = httpx.ConnectError("Connection failed")

    with pytest.raises(HttpRequestError) as exc_info:
        handle_exception_with_retry_if(
            exc,
            retry_if=retry_if_false,
            url="https://api.example.com",
            method="PUT",
            attempt=2,
            max_retries=5,
            on_failure=None,
            start_time=time.time(),
        )

    error = exc_info.value
    assert error.method == "PUT"
    assert error.url == "https://api.example.com"
    assert "failed after 3 attempts" in str(error)
    assert error.__cause__ is exc


def test_handle_exception_with_on_failure_callback() -> None:
    """Test that on_failure callback is invoked when exception is
    raised."""
    exc = httpx.TimeoutException("Request timed out")
    callback_data = {"info": None}

    def on_failure(info: FailureInfo) -> None:
        callback_data["info"] = info

    start = time.time()

    with pytest.raises(
        HttpRequestError, match=r"DELETE request to https://example.com timed out \(3 attempts\)"
    ):
        handle_exception_with_retry_if(
            exc,
            retry_if=retry_if_false,
            url="https://example.com",
            method="DELETE",
            attempt=2,
            max_retries=5,
            on_failure=on_failure,
            start_time=start,
        )

    callback_info = callback_data["info"]
    assert callback_info is not None
    assert callback_info.url == "https://example.com"
    assert callback_info.method == "DELETE"
    assert callback_info.attempt == 3
    assert callback_info.max_retries == 5
    assert callback_info.status_code is None
    assert isinstance(callback_info.error, HttpRequestError)
    assert callback_info.total_time >= 0


def test_handle_exception_connect_error() -> None:
    """Test with ConnectError exception."""
    exc = httpx.ConnectError("Failed to connect")
    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://example.com failed after 1 attempts: Failed to connect",
    ):
        handle_exception_with_retry_if(
            exc,
            retry_if=retry_if_false,
            url="https://example.com",
            method="GET",
            attempt=0,
            max_retries=3,
            on_failure=None,
            start_time=time.time(),
        )


def test_handle_exception_read_timeout() -> None:
    """Test with ReadTimeout exception."""
    exc = httpx.ReadTimeout("Read timed out")
    with pytest.raises(
        HttpRequestError, match=r"POST request to https://example.com timed out \(2 attempts\)"
    ):
        handle_exception_with_retry_if(
            exc,
            retry_if=retry_if_false,
            url="https://example.com",
            method="POST",
            attempt=1,
            max_retries=3,
            on_failure=None,
            start_time=time.time(),
        )
