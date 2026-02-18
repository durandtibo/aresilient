"""Integration tests for CircuitBreaker with HTTP requests."""

from __future__ import annotations

import time as real_time
from unittest.mock import Mock, call, patch

import httpx
import pytest

from aresilient import HttpRequestError, request
from aresilient.core import ClientConfig
from aresilient.circuit_breaker import CircuitBreaker, CircuitBreakerError

##############################################
#     Tests for CircuitBreaker with HTTP     #
##############################################


def test_circuit_breaker_with_http_request_success(
    mock_response: httpx.Response, mock_request_func: Mock, mock_sleep: Mock
) -> None:
    """Test that circuit breaker works with successful HTTP requests."""
    cb = CircuitBreaker(failure_threshold=3)

    result = request(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
        config=ClientConfig(max_retries=3, circuit_breaker=cb),
    )

    assert result == mock_response
    assert cb.state.value == "closed"
    assert cb.failure_count == 0

    mock_sleep.assert_not_called()


def test_circuit_breaker_opens_after_http_failures(
    mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that circuit breaker opens after consecutive HTTP
    failures."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

    # Create mock that fails with 500 three times, then exhausts retries
    mock_request_func = Mock(return_value=mock_response_fail)

    # Request should exhaust retries and record failures
    with pytest.raises(HttpRequestError):  # HttpRequestError
        request(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(max_retries=2, circuit_breaker=cb),
        )

    # Circuit should be open now (3 attempts x 1 failure each = 3 failures)
    assert cb.state.value == "open"
    assert cb.failure_count == 3

    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_circuit_breaker_fails_fast_when_open(mock_sleep: Mock) -> None:
    """Test that circuit breaker fails fast when open."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)

    # Open the circuit manually
    cb.record_failure(Exception("error 1"))
    cb.record_failure(Exception("error 2"))
    assert cb.state.value == "open"

    # Mock request func should not be called because circuit is open
    mock_request_func = Mock()

    # Should fail fast with CircuitBreakerError
    with pytest.raises(CircuitBreakerError, match=r"Circuit breaker is OPEN"):
        request(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(max_retries=3, circuit_breaker=cb),
        )

    # Request func should not have been called
    mock_request_func.assert_not_called()

    mock_sleep.assert_not_called()


def test_circuit_breaker_recovers_after_timeout(
    mock_response: httpx.Response, mock_sleep: Mock
) -> None:
    """Test that circuit breaker recovers after timeout and successful
    request."""

    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    # Open the circuit
    start_time = real_time.time()
    cb.record_failure(Exception("error 1"))
    cb.record_failure(Exception("error 2"))
    assert cb.state.value == "open"

    # Mock successful request
    mock_request_func = Mock(return_value=mock_response)

    # Mock time.time() to simulate time passing
    with patch("time.time") as mock_time:
        # First call in check() - simulate time has passed
        mock_time.return_value = start_time + 0.15

        # Should succeed and close the circuit
        result = request(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(max_retries=3, circuit_breaker=cb),
        )

    assert result == mock_response
    assert cb.state.value == "closed"
    assert cb.failure_count == 0

    mock_sleep.assert_not_called()


def test_circuit_breaker_with_retry_if_predicate(mock_sleep: Mock) -> None:
    """Test that circuit breaker works with custom retry_if
    predicate."""
    cb = CircuitBreaker(failure_threshold=3)

    # Custom predicate that triggers retry on specific condition
    def should_retry(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        if response and response.status_code == 200:
            # Retry even on success if response is empty
            return not response.text
        return response is None or response.status_code >= 500

    # Mock response with empty text
    mock_response_empty = Mock(spec=httpx.Response, status_code=200, text="")
    mock_request_func = Mock(return_value=mock_response_empty)

    # Should retry and record failures
    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://example.com failed with status 200 after 3 attempts",
    ):
        request(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(max_retries=2, retry_if=should_retry, circuit_breaker=cb),
        )

    # Circuit breaker should have recorded failures (3 attempts = 3 failures)
    assert cb.failure_count >= 3
    assert cb.state.value == "open"

    assert mock_sleep.call_args_list == [call(0.3), call(0.6)]


def test_circuit_breaker_shared_across_requests(
    mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that circuit breaker state is shared across multiple
    requests."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

    mock_request_func = Mock(return_value=mock_response_fail)

    # Make first request - should fail and increment counter
    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://example.com failed with status 500 after 1 attempts",
    ):
        request(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(max_retries=0, circuit_breaker=cb),
        )

    assert cb.failure_count == 1

    # Make second request - should fail and increment counter
    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://example.com failed with status 500 after 1 attempts",
    ):
        request(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(max_retries=0, circuit_breaker=cb),
        )

    assert cb.failure_count == 2

    # Make third request - should open the circuit
    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://example.com failed with status 500 after 1 attempts",
    ):
        request(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(max_retries=0, circuit_breaker=cb),
        )

    assert cb.failure_count == 3
    assert cb.state.value == "open"

    # Fourth request should fail fast
    with pytest.raises(
        CircuitBreakerError, match=r"Circuit breaker is OPEN \(failed 3 times\). Retry after 60.0s"
    ):
        request(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(max_retries=0, circuit_breaker=cb),
        )

    mock_sleep.assert_not_called()
