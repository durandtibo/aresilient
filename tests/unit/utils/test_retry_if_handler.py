r"""Unit tests for retry_if_handler module."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx
import pytest

from aresilient.callbacks import FailureInfo
from aresilient.exceptions import HttpRequestError
from aresilient.utils.retry_if_handler import (
    handle_exception_with_retry_if,
    handle_response_with_retry_if,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class TestHandleResponseWithRetryIf:
    """Tests for handle_response_with_retry_if function."""

    def test_success_response_retry_if_returns_false(self) -> None:
        """Test successful response when retry_if returns False."""
        response = httpx.Response(200, content=b"OK")

        def retry_if(resp: httpx.Response | None, exc: Exception | None) -> bool:
            return False

        result = handle_response_with_retry_if(
            response,
            retry_if=retry_if,
            url="https://example.com",
            method="GET",
        )

        assert result is False

    def test_success_response_retry_if_returns_true(self) -> None:
        """Test successful response when retry_if returns True (retry even on success)."""
        response = httpx.Response(200, content=b"OK")

        def retry_if(resp: httpx.Response | None, exc: Exception | None) -> bool:
            return True

        result = handle_response_with_retry_if(
            response,
            retry_if=retry_if,
            url="https://example.com",
            method="GET",
        )

        assert result is True

    def test_error_response_retry_if_returns_true(self) -> None:
        """Test error response when retry_if returns True (should retry)."""
        response = httpx.Response(500, content=b"Server Error")

        def retry_if(resp: httpx.Response | None, exc: Exception | None) -> bool:
            return True

        result = handle_response_with_retry_if(
            response,
            retry_if=retry_if,
            url="https://example.com",
            method="GET",
        )

        assert result is True

    def test_error_response_retry_if_returns_false(self) -> None:
        """Test error response when retry_if returns False (raise error)."""
        response = httpx.Response(400, content=b"Bad Request")

        def retry_if(resp: httpx.Response | None, exc: Exception | None) -> bool:
            return False

        with pytest.raises(HttpRequestError) as exc_info:
            handle_response_with_retry_if(
                response,
                retry_if=retry_if,
                url="https://example.com",
                method="GET",
            )

        error = exc_info.value
        assert error.method == "GET"
        assert error.url == "https://example.com"
        assert error.status_code == 400
        assert error.response is response
        assert "failed with status 400" in str(error)

    def test_different_status_codes(self) -> None:
        """Test with various status codes."""
        # Test 3xx success
        response = httpx.Response(301, content=b"Moved")

        def retry_if_false(resp: httpx.Response | None, exc: Exception | None) -> bool:
            return False

        result = handle_response_with_retry_if(
            response,
            retry_if=retry_if_false,
            url="https://example.com",
            method="GET",
        )
        assert result is False

        # Test 5xx error
        response_500 = httpx.Response(503, content=b"Service Unavailable")

        def retry_if_true(resp: httpx.Response | None, exc: Exception | None) -> bool:
            return True

        result = handle_response_with_retry_if(
            response_500,
            retry_if=retry_if_true,
            url="https://example.com",
            method="POST",
        )
        assert result is True


class TestHandleExceptionWithRetryIf:
    """Tests for handle_exception_with_retry_if function."""

    def test_timeout_exception_retry_if_returns_true_with_attempts_remaining(self) -> None:
        """Test TimeoutException when retry_if returns True and attempts remain."""
        exc = httpx.TimeoutException("Request timed out")

        def retry_if(resp: httpx.Response | None, exc_arg: Exception | None) -> bool:
            return True

        result = handle_exception_with_retry_if(
            exc,
            retry_if=retry_if,
            url="https://example.com",
            method="GET",
            attempt=0,
            max_retries=3,
            on_failure=None,
            start_time=time.time(),
        )

        assert result is True

    def test_timeout_exception_retry_if_returns_false(self) -> None:
        """Test TimeoutException when retry_if returns False."""
        exc = httpx.TimeoutException("Request timed out")

        def retry_if(resp: httpx.Response | None, exc_arg: Exception | None) -> bool:
            return False

        with pytest.raises(HttpRequestError) as exc_info:
            handle_exception_with_retry_if(
                exc,
                retry_if=retry_if,
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

    def test_timeout_exception_max_retries_reached(self) -> None:
        """Test TimeoutException when max retries is reached."""
        exc = httpx.TimeoutException("Request timed out")

        def retry_if(resp: httpx.Response | None, exc_arg: Exception | None) -> bool:
            return True  # Even though True, should still raise due to max retries

        with pytest.raises(HttpRequestError) as exc_info:
            handle_exception_with_retry_if(
                exc,
                retry_if=retry_if,
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

    def test_request_error_retry_if_returns_true(self) -> None:
        """Test RequestError when retry_if returns True."""
        exc = httpx.ConnectError("Connection failed")

        def retry_if(resp: httpx.Response | None, exc_arg: Exception | None) -> bool:
            return True

        result = handle_exception_with_retry_if(
            exc,
            retry_if=retry_if,
            url="https://example.com",
            method="GET",
            attempt=1,
            max_retries=5,
            on_failure=None,
            start_time=time.time(),
        )

        assert result is True

    def test_request_error_retry_if_returns_false(self) -> None:
        """Test RequestError when retry_if returns False."""
        exc = httpx.ConnectError("Connection failed")

        def retry_if(resp: httpx.Response | None, exc_arg: Exception | None) -> bool:
            return False

        with pytest.raises(HttpRequestError) as exc_info:
            handle_exception_with_retry_if(
                exc,
                retry_if=retry_if,
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

    def test_with_on_failure_callback(self) -> None:
        """Test that on_failure callback is invoked when exception is raised."""
        exc = httpx.TimeoutException("Request timed out")
        callback_invoked = False
        callback_info: FailureInfo | None = None

        def on_failure(info: FailureInfo) -> None:
            nonlocal callback_invoked, callback_info
            callback_invoked = True
            callback_info = info

        def retry_if(resp: httpx.Response | None, exc_arg: Exception | None) -> bool:
            return False

        start = time.time()

        with pytest.raises(HttpRequestError):
            handle_exception_with_retry_if(
                exc,
                retry_if=retry_if,
                url="https://example.com",
                method="DELETE",
                attempt=2,
                max_retries=5,
                on_failure=on_failure,
                start_time=start,
            )

        assert callback_invoked
        assert callback_info is not None
        assert callback_info.url == "https://example.com"
        assert callback_info.method == "DELETE"
        assert callback_info.attempt == 3
        assert callback_info.max_retries == 5
        assert callback_info.status_code is None
        assert isinstance(callback_info.error, HttpRequestError)
        assert callback_info.total_time >= 0

    def test_different_exception_types(self) -> None:
        """Test with different exception types."""
        # ConnectError
        exc1 = httpx.ConnectError("Failed to connect")

        def retry_if(resp: httpx.Response | None, exc_arg: Exception | None) -> bool:
            return False

        with pytest.raises(HttpRequestError) as exc_info:
            handle_exception_with_retry_if(
                exc1,
                retry_if=retry_if,
                url="https://example.com",
                method="GET",
                attempt=0,
                max_retries=3,
                on_failure=None,
                start_time=time.time(),
            )

        assert "failed after 1 attempts" in str(exc_info.value)

        # ReadTimeout
        exc2 = httpx.ReadTimeout("Read timed out")

        with pytest.raises(HttpRequestError) as exc_info:
            handle_exception_with_retry_if(
                exc2,
                retry_if=retry_if,
                url="https://example.com",
                method="POST",
                attempt=1,
                max_retries=3,
                on_failure=None,
                start_time=time.time(),
            )

        assert "timed out (2 attempts)" in str(exc_info.value)
