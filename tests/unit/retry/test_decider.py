r"""Unit tests for retry decider."""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresilient.exceptions import HttpRequestError
from aresilient.retry.decider import RetryDecider


def test_retry_decider_creation() -> None:
    """Test RetryDecider initialization."""
    decider = RetryDecider(
        status_forcelist=(500, 502, 503),
        retry_if=None,
    )

    assert decider.status_forcelist == (500, 502, 503)
    assert decider.retry_if is None


def test_should_retry_response_success_no_retry() -> None:
    """Test successful response (2xx) does not retry."""
    decider = RetryDecider(
        status_forcelist=(500, 502, 503),
        retry_if=None,
    )

    mock_response = Mock(spec=httpx.Response, status_code=200)
    should_retry, reason = decider.should_retry_response(
        response=mock_response,
        attempt=0,
        max_retries=3,
        url="https://example.com",
        method="GET",
    )

    assert should_retry is False
    assert reason == "success"


def test_should_retry_response_retryable_status() -> None:
    """Test retryable status code triggers retry."""
    decider = RetryDecider(
        status_forcelist=(500, 502, 503),
        retry_if=None,
    )

    mock_response = Mock(spec=httpx.Response, status_code=500)
    should_retry, reason = decider.should_retry_response(
        response=mock_response,
        attempt=0,
        max_retries=3,
        url="https://example.com",
        method="GET",
    )

    assert should_retry is True
    assert "500" in reason


def test_should_retry_response_non_retryable_status_raises() -> None:
    """Test non-retryable status code raises HttpRequestError."""
    decider = RetryDecider(
        status_forcelist=(500, 502, 503),
        retry_if=None,
    )

    mock_response = Mock(spec=httpx.Response, status_code=404)

    with pytest.raises(HttpRequestError) as exc_info:
        decider.should_retry_response(
            response=mock_response,
            attempt=0,
            max_retries=3,
            url="https://example.com",
            method="GET",
        )

    assert exc_info.value.status_code == 404
    assert (
        "GET request to https://example.com failed with status 404"
        in str(exc_info.value)
    )


def test_should_retry_response_with_custom_predicate_success() -> None:
    """Test custom predicate allows retry on success."""

    def always_retry(response, exc) -> bool:
        return True

    decider = RetryDecider(
        status_forcelist=(500,),
        retry_if=always_retry,
    )

    mock_response = Mock(spec=httpx.Response, status_code=200)
    should_retry, reason = decider.should_retry_response(
        response=mock_response,
        attempt=0,
        max_retries=3,
        url="https://example.com",
        method="GET",
    )

    assert should_retry is True
    assert "retry_if" in reason


def test_should_retry_response_with_custom_predicate_error_true() -> None:
    """Test custom predicate returns True for error."""

    def retry_500(response, exc):
        return response is not None and response.status_code == 500

    decider = RetryDecider(
        status_forcelist=(),
        retry_if=retry_500,
    )

    mock_response = Mock(spec=httpx.Response, status_code=500)
    should_retry, reason = decider.should_retry_response(
        response=mock_response,
        attempt=0,
        max_retries=3,
        url="https://example.com",
        method="GET",
    )

    assert should_retry is True
    assert "retry_if" in reason


def test_should_retry_response_with_custom_predicate_error_false_raises() -> None:
    """Test custom predicate returns False for error raises."""

    def never_retry(response, exc) -> bool:
        return False

    decider = RetryDecider(
        status_forcelist=(),
        retry_if=never_retry,
    )

    mock_response = Mock(spec=httpx.Response, status_code=500)

    with pytest.raises(HttpRequestError) as exc_info:
        decider.should_retry_response(
            response=mock_response,
            attempt=0,
            max_retries=3,
            url="https://example.com",
            method="GET",
        )

    assert exc_info.value.status_code == 500


def test_should_retry_exception_with_predicate_true() -> None:
    """Test exception retry with custom predicate returning True."""

    def retry_timeout(response, exc):
        return isinstance(exc, httpx.TimeoutException)

    decider = RetryDecider(
        status_forcelist=(),
        retry_if=retry_timeout,
    )

    exc = httpx.TimeoutException("Timeout")
    should_retry, reason = decider.should_retry_exception(
        exception=exc,
        attempt=0,
        max_retries=3,
    )

    assert should_retry is True
    assert "retry_if" in reason


def test_should_retry_exception_with_predicate_false() -> None:
    """Test exception retry with custom predicate returning False."""

    def never_retry(response, exc) -> bool:
        return False

    decider = RetryDecider(
        status_forcelist=(),
        retry_if=never_retry,
    )

    exc = httpx.TimeoutException("Timeout")
    should_retry, _reason = decider.should_retry_exception(
        exception=exc,
        attempt=0,
        max_retries=3,
    )

    assert should_retry is False


def test_should_retry_exception_max_retries_reached() -> None:
    """Test exception retry when max retries reached with predicate."""

    def always_retry(response, exc) -> bool:
        return True

    decider = RetryDecider(
        status_forcelist=(),
        retry_if=always_retry,
    )

    exc = httpx.TimeoutException("Timeout")
    should_retry, _reason = decider.should_retry_exception(
        exception=exc,
        attempt=3,
        max_retries=3,
    )

    assert should_retry is False


def test_should_retry_exception_default_behavior() -> None:
    """Test default exception retry behavior without predicate."""
    decider = RetryDecider(
        status_forcelist=(500,),
        retry_if=None,
    )

    exc = httpx.TimeoutException("Timeout")

    # Should retry when under max_retries
    should_retry, reason = decider.should_retry_exception(
        exception=exc,
        attempt=0,
        max_retries=3,
    )
    assert should_retry is True
    assert "TimeoutException" in reason

    # Should not retry when at max_retries
    should_retry, reason = decider.should_retry_exception(
        exception=exc,
        attempt=3,
        max_retries=3,
    )
    assert should_retry is False
