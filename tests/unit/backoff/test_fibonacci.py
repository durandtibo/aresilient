r"""Unit tests for FibonacciBackoff strategy."""

from __future__ import annotations

import pytest

from aresilient.backoff.fibonacci import FibonacciBackoff


def test_fibonacci_backoff_basic() -> None:
    """Test basic Fibonacci backoff calculation."""
    backoff = FibonacciBackoff(base_delay=1.0)
    assert backoff.calculate(0) == 1.0  # 1.0 * fib(1) = 1.0 * 1
    assert backoff.calculate(1) == 1.0  # 1.0 * fib(2) = 1.0 * 1
    assert backoff.calculate(2) == 2.0  # 1.0 * fib(3) = 1.0 * 2
    assert backoff.calculate(3) == 3.0  # 1.0 * fib(4) = 1.0 * 3
    assert backoff.calculate(4) == 5.0  # 1.0 * fib(5) = 1.0 * 5
    assert backoff.calculate(5) == 8.0  # 1.0 * fib(6) = 1.0 * 8
    assert backoff.calculate(6) == 13.0  # 1.0 * fib(7) = 1.0 * 13


def test_fibonacci_backoff_with_max_delay() -> None:
    """Test Fibonacci backoff with max_delay cap."""
    backoff = FibonacciBackoff(base_delay=1.0, max_delay=10.0)
    assert backoff.calculate(0) == 1.0  # fib(1) = 1
    assert backoff.calculate(5) == 8.0  # fib(6) = 8
    assert backoff.calculate(6) == 10.0  # fib(7) = 13, but capped
    assert backoff.calculate(10) == 10.0  # fib(11) = 89, but capped


def test_fibonacci_backoff_default_values() -> None:
    """Test Fibonacci backoff with default values."""
    backoff = FibonacciBackoff()
    assert backoff.base_delay == 1.0
    assert backoff.max_delay is None
    assert backoff.calculate(0) == 1.0


def test_fibonacci_backoff_invalid_base_delay() -> None:
    """Test that negative base_delay raises ValueError."""
    with pytest.raises(ValueError, match=r"base_delay must be non-negative"):
        FibonacciBackoff(base_delay=-1.0)


def test_fibonacci_backoff_invalid_max_delay() -> None:
    """Test that non-positive max_delay raises ValueError."""
    with pytest.raises(ValueError, match=r"max_delay must be positive"):
        FibonacciBackoff(base_delay=1.0, max_delay=0)
    with pytest.raises(ValueError, match=r"max_delay must be positive"):
        FibonacciBackoff(base_delay=1.0, max_delay=-5.0)


def test_fibonacci_number_calculation() -> None:
    """Test the internal Fibonacci number calculation."""
    backoff = FibonacciBackoff(base_delay=1.0)
    # Test Fibonacci sequence: 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89
    assert backoff._fibonacci(0) == 0
    assert backoff._fibonacci(1) == 1
    assert backoff._fibonacci(2) == 1
    assert backoff._fibonacci(3) == 2
    assert backoff._fibonacci(4) == 3
    assert backoff._fibonacci(5) == 5
    assert backoff._fibonacci(6) == 8
    assert backoff._fibonacci(7) == 13
    assert backoff._fibonacci(11) == 89


def test_fibonacci_backoff_zero_base_delay() -> None:
    """Test Fibonacci backoff with zero base_delay."""
    backoff = FibonacciBackoff(base_delay=0.0)
    assert backoff.calculate(0) == 0.0
    assert backoff.calculate(5) == 0.0
