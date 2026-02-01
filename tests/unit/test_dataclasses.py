r"""Unit tests for callback dataclasses."""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresilient.callbacks import (
    CallbackInfo,
    FailureInfo,
    RequestInfo,
    ResponseInfo,
    RetryInfo,
)


class TestRequestInfo:
    """Tests for RequestInfo dataclass."""

    def test_create_request_info(self) -> None:
        """Test creating a RequestInfo instance."""
        request_info = RequestInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
        )
        assert request_info.url == "https://api.example.com/data"
        assert request_info.method == "GET"
        assert request_info.attempt == 1
        assert request_info.max_retries == 3

    def test_request_info_equality(self) -> None:
        """Test RequestInfo instances equality."""
        request_info1 = RequestInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
        )
        request_info2 = RequestInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
        )
        assert request_info1 == request_info2

    def test_request_info_inequality(self) -> None:
        """Test RequestInfo instances inequality."""
        request_info1 = RequestInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
        )
        request_info2 = RequestInfo(
            url="https://api.example.com/data",
            method="POST",
            attempt=1,
            max_retries=3,
        )
        assert request_info1 != request_info2

    def test_request_info_repr(self) -> None:
        """Test RequestInfo repr."""
        request_info = RequestInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
        )
        repr_str = repr(request_info)
        assert "RequestInfo" in repr_str
        assert "url='https://api.example.com/data'" in repr_str
        assert "method='GET'" in repr_str
        assert "attempt=1" in repr_str
        assert "max_retries=3" in repr_str


class TestRetryInfo:
    """Tests for RetryInfo dataclass."""

    def test_create_retry_info(self) -> None:
        """Test creating a RetryInfo instance."""
        error = ValueError("Test error")
        retry_info = RetryInfo(
            url="https://api.example.com/data",
            method="POST",
            attempt=2,
            max_retries=3,
            wait_time=0.6,
            error=error,
            status_code=503,
        )
        assert retry_info.url == "https://api.example.com/data"
        assert retry_info.method == "POST"
        assert retry_info.attempt == 2
        assert retry_info.max_retries == 3
        assert retry_info.wait_time == 0.6
        assert retry_info.error == error
        assert retry_info.status_code == 503

    def test_retry_info_with_none_values(self) -> None:
        """Test RetryInfo with None for error and status_code."""
        retry_info = RetryInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=2,
            max_retries=3,
            wait_time=0.3,
            error=None,
            status_code=None,
        )
        assert retry_info.error is None
        assert retry_info.status_code is None

    def test_retry_info_equality(self) -> None:
        """Test RetryInfo instances equality."""
        retry_info1 = RetryInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=2,
            max_retries=3,
            wait_time=0.3,
            error=None,
            status_code=None,
        )
        retry_info2 = RetryInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=2,
            max_retries=3,
            wait_time=0.3,
            error=None,
            status_code=None,
        )
        assert retry_info1 == retry_info2


class TestResponseInfo:
    """Tests for ResponseInfo dataclass."""

    def test_create_response_info(self) -> None:
        """Test creating a ResponseInfo instance."""
        mock_response = Mock(spec=httpx.Response, status_code=200)
        response_info = ResponseInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
            response=mock_response,
            total_time=0.123,
        )
        assert response_info.url == "https://api.example.com/data"
        assert response_info.method == "GET"
        assert response_info.attempt == 1
        assert response_info.max_retries == 3
        assert response_info.response == mock_response
        assert response_info.total_time == 0.123

    def test_response_info_equality(self) -> None:
        """Test ResponseInfo instances equality."""
        mock_response = Mock(spec=httpx.Response, status_code=200)
        response_info1 = ResponseInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
            response=mock_response,
            total_time=0.123,
        )
        response_info2 = ResponseInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
            response=mock_response,
            total_time=0.123,
        )
        assert response_info1 == response_info2


class TestFailureInfo:
    """Tests for FailureInfo dataclass."""

    def test_create_failure_info(self) -> None:
        """Test creating a FailureInfo instance."""
        error = ValueError("Test error")
        failure_info = FailureInfo(
            url="https://api.example.com/data",
            method="POST",
            attempt=4,
            max_retries=3,
            error=error,
            status_code=500,
            total_time=1.5,
        )
        assert failure_info.url == "https://api.example.com/data"
        assert failure_info.method == "POST"
        assert failure_info.attempt == 4
        assert failure_info.max_retries == 3
        assert failure_info.error == error
        assert failure_info.status_code == 500
        assert failure_info.total_time == 1.5

    def test_failure_info_with_none_status_code(self) -> None:
        """Test FailureInfo with None status_code."""
        error = ValueError("Test error")
        failure_info = FailureInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=4,
            max_retries=3,
            error=error,
            status_code=None,
            total_time=1.5,
        )
        assert failure_info.status_code is None

    def test_failure_info_equality(self) -> None:
        """Test FailureInfo instances equality."""
        error = ValueError("Test error")
        failure_info1 = FailureInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=4,
            max_retries=3,
            error=error,
            status_code=None,
            total_time=1.5,
        )
        failure_info2 = FailureInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=4,
            max_retries=3,
            error=error,
            status_code=None,
            total_time=1.5,
        )
        assert failure_info1 == failure_info2


class TestCallbackInfo:
    """Tests for CallbackInfo dataclass."""

    def test_create_callback_info(self) -> None:
        """Test creating a CallbackInfo instance."""
        error = ValueError("Test error")
        mock_response = Mock(spec=httpx.Response, status_code=200)
        callback_info = CallbackInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=2,
            max_retries=3,
            wait_time=0.6,
            error=error,
            status_code=503,
            response=mock_response,
            total_time=1.2,
        )
        assert callback_info.url == "https://api.example.com/data"
        assert callback_info.method == "GET"
        assert callback_info.attempt == 2
        assert callback_info.max_retries == 3
        assert callback_info.wait_time == 0.6
        assert callback_info.error == error
        assert callback_info.status_code == 503
        assert callback_info.response == mock_response
        assert callback_info.total_time == 1.2

    def test_callback_info_with_none_values(self) -> None:
        """Test CallbackInfo with None values."""
        callback_info = CallbackInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
            wait_time=0.0,
            error=None,
            status_code=None,
            response=None,
            total_time=0.1,
        )
        assert callback_info.error is None
        assert callback_info.status_code is None
        assert callback_info.response is None

    def test_callback_info_equality(self) -> None:
        """Test CallbackInfo instances equality."""
        callback_info1 = CallbackInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
            wait_time=0.0,
            error=None,
            status_code=None,
            response=None,
            total_time=0.1,
        )
        callback_info2 = CallbackInfo(
            url="https://api.example.com/data",
            method="GET",
            attempt=1,
            max_retries=3,
            wait_time=0.0,
            error=None,
            status_code=None,
            response=None,
            total_time=0.1,
        )
        assert callback_info1 == callback_info2
