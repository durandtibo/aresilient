"""Unit tests for the CircuitBreaker pattern implementation."""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest

from aresilient import CircuitBreaker, CircuitBreakerError, CircuitState


########################################
#     Tests for CircuitBreaker class     #
########################################


def test_circuit_breaker_initial_state() -> None:
    """Test that circuit breaker starts in CLOSED state."""
    cb = CircuitBreaker()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.last_failure_time is None


def test_circuit_breaker_record_success() -> None:
    """Test that recording success keeps circuit closed."""
    cb = CircuitBreaker()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_record_failure_under_threshold() -> None:
    """Test that failures under threshold keep circuit closed."""
    cb = CircuitBreaker(failure_threshold=3)
    
    cb.record_failure(Exception("error 1"))
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1
    
    cb.record_failure(Exception("error 2"))
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 2


def test_circuit_breaker_opens_at_threshold() -> None:
    """Test that circuit opens when failure threshold is reached."""
    cb = CircuitBreaker(failure_threshold=3)
    
    cb.record_failure(Exception("error 1"))
    cb.record_failure(Exception("error 2"))
    assert cb.state == CircuitState.CLOSED
    
    cb.record_failure(Exception("error 3"))
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 3


def test_circuit_breaker_check_raises_when_open() -> None:
    """Test that check() raises CircuitBreakerError when circuit is open."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
    
    cb.record_failure(Exception("error"))
    assert cb.state == CircuitState.OPEN
    
    with pytest.raises(CircuitBreakerError, match="Circuit breaker is OPEN"):
        cb.check()


def test_circuit_breaker_transitions_to_half_open_after_timeout() -> None:
    """Test that circuit transitions to HALF_OPEN after recovery timeout."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    
    cb.record_failure(Exception("error"))
    assert cb.state == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(0.15)
    
    # Check should transition to HALF_OPEN
    cb.check()
    assert cb.state == CircuitState.HALF_OPEN


def test_circuit_breaker_half_open_success_closes_circuit() -> None:
    """Test that success in HALF_OPEN state closes the circuit."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    
    # Open the circuit
    cb.record_failure(Exception("error"))
    assert cb.state == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(0.15)
    cb.check()
    assert cb.state == CircuitState.HALF_OPEN
    
    # Success should close the circuit
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_half_open_failure_reopens_circuit() -> None:
    """Test that failure in HALF_OPEN state reopens the circuit."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    
    # Open the circuit
    cb.record_failure(Exception("error 1"))
    assert cb.state == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(0.15)
    cb.check()
    assert cb.state == CircuitState.HALF_OPEN
    
    # Failure should reopen the circuit
    cb.record_failure(Exception("error 2"))
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2


def test_circuit_breaker_call_success() -> None:
    """Test that call() executes function and records success."""
    cb = CircuitBreaker()
    
    def successful_func():
        return "success"
    
    result = cb.call(successful_func)
    assert result == "success"
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_call_failure() -> None:
    """Test that call() records failure when function raises exception."""
    cb = CircuitBreaker(failure_threshold=2)
    
    def failing_func():
        raise ValueError("test error")
    
    with pytest.raises(ValueError, match="test error"):
        cb.call(failing_func)
    
    assert cb.failure_count == 1
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_call_opens_on_threshold() -> None:
    """Test that call() opens circuit when threshold is reached."""
    cb = CircuitBreaker(failure_threshold=2)
    
    def failing_func():
        raise ValueError("test error")
    
    with pytest.raises(ValueError):
        cb.call(failing_func)
    assert cb.state == CircuitState.CLOSED
    
    with pytest.raises(ValueError):
        cb.call(failing_func)
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_call_raises_when_open() -> None:
    """Test that call() raises CircuitBreakerError when circuit is open."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
    
    def failing_func():
        raise ValueError("test error")
    
    with pytest.raises(ValueError):
        cb.call(failing_func)
    
    assert cb.state == CircuitState.OPEN
    
    # Next call should fail fast
    with pytest.raises(CircuitBreakerError, match="Circuit breaker is OPEN"):
        cb.call(lambda: "should not execute")


def test_circuit_breaker_reset() -> None:
    """Test that reset() closes the circuit and clears failures."""
    cb = CircuitBreaker(failure_threshold=1)
    
    cb.record_failure(Exception("error"))
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 1
    
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.last_failure_time is None


def test_circuit_breaker_expected_exception_filtering() -> None:
    """Test that only expected exception types count as failures."""
    cb = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)
    
    # TypeError should not count
    cb.record_failure(TypeError("not counted"))
    assert cb.failure_count == 0
    assert cb.state == CircuitState.CLOSED
    
    # ValueError should count
    cb.record_failure(ValueError("counted 1"))
    assert cb.failure_count == 1
    
    cb.record_failure(ValueError("counted 2"))
    assert cb.failure_count == 2
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_expected_exception_tuple() -> None:
    """Test that expected_exception works with tuple of exception types."""
    cb = CircuitBreaker(
        failure_threshold=2,
        expected_exception=(ValueError, TypeError),
    )
    
    cb.record_failure(ValueError("counted"))
    assert cb.failure_count == 1
    
    cb.record_failure(TypeError("also counted"))
    assert cb.failure_count == 2
    assert cb.state == CircuitState.OPEN
    
    # RuntimeError should not count
    cb.reset()
    cb.record_failure(RuntimeError("not counted"))
    assert cb.failure_count == 0


def test_circuit_breaker_state_change_callback() -> None:
    """Test that on_state_change callback is called on state transitions."""
    callback = Mock()
    cb = CircuitBreaker(failure_threshold=2, on_state_change=callback)
    
    # Should not call callback for staying in same state
    cb.record_success()
    callback.assert_not_called()
    
    # Should call callback when transitioning to OPEN
    cb.record_failure(Exception("error 1"))
    cb.record_failure(Exception("error 2"))
    callback.assert_called_once_with(CircuitState.CLOSED, CircuitState.OPEN)
    
    callback.reset_mock()
    
    # Should call callback when transitioning to CLOSED via reset
    cb.reset()
    callback.assert_called_once_with(CircuitState.OPEN, CircuitState.CLOSED)


def test_circuit_breaker_invalid_failure_threshold() -> None:
    """Test that invalid failure_threshold raises ValueError."""
    with pytest.raises(ValueError, match="failure_threshold must be > 0"):
        CircuitBreaker(failure_threshold=0)
    
    with pytest.raises(ValueError, match="failure_threshold must be > 0"):
        CircuitBreaker(failure_threshold=-1)


def test_circuit_breaker_invalid_recovery_timeout() -> None:
    """Test that invalid recovery_timeout raises ValueError."""
    with pytest.raises(ValueError, match="recovery_timeout must be > 0"):
        CircuitBreaker(recovery_timeout=0)
    
    with pytest.raises(ValueError, match="recovery_timeout must be > 0"):
        CircuitBreaker(recovery_timeout=-1.0)


def test_circuit_breaker_concurrent_failures() -> None:
    """Test that circuit breaker handles concurrent failures correctly."""
    cb = CircuitBreaker(failure_threshold=3)
    
    # Simulate multiple failures happening quickly
    exceptions = [Exception(f"error {i}") for i in range(3)]
    for exc in exceptions:
        cb.record_failure(exc)
    
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 3


def test_circuit_breaker_success_resets_failure_count() -> None:
    """Test that success resets the failure count."""
    cb = CircuitBreaker(failure_threshold=5)
    
    cb.record_failure(Exception("error 1"))
    cb.record_failure(Exception("error 2"))
    assert cb.failure_count == 2
    
    cb.record_success()
    assert cb.failure_count == 0
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_repr() -> None:
    """Test CircuitBreakerError repr."""
    error = CircuitBreakerError("test message")
    assert "test message" in str(error)


def test_circuit_breaker_multiple_recovery_cycles() -> None:
    """Test that circuit can go through multiple open/close cycles."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    
    # First cycle: open
    cb.record_failure(Exception("error 1"))
    cb.record_failure(Exception("error 2"))
    assert cb.state == CircuitState.OPEN
    
    # Recover
    time.sleep(0.15)
    cb.check()
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    
    # Second cycle: open again
    cb.record_failure(Exception("error 3"))
    cb.record_failure(Exception("error 4"))
    assert cb.state == CircuitState.OPEN
    
    # Recover again
    time.sleep(0.15)
    cb.check()
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
