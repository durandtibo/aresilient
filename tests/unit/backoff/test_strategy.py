r"""Unit tests for backoff strategy implementations."""

from __future__ import annotations

import pytest

from aresilient.backoff import (
    BackoffStrategy,
    ConstantBackoff,
    ExponentialBackoff,
    FibonacciBackoff,
    LinearBackoff,
)

########################################
#     Tests for ExponentialBackoff     #
########################################


def test_exponential_backoff_basic() -> None:
    """Test basic exponential backoff calculation."""
    backoff = ExponentialBackoff(base_delay=0.3)
    assert backoff.calculate(0) == 0.3  # 0.3 * 2^0
    assert backoff.calculate(1) == 0.6  # 0.3 * 2^1
    assert backoff.calculate(2) == 1.2  # 0.3 * 2^2
    assert backoff.calculate(3) == 2.4  # 0.3 * 2^3


def test_exponential_backoff_with_max_delay() -> None:
    """Test exponential backoff with max_delay cap."""
    backoff = ExponentialBackoff(base_delay=1.0, max_delay=5.0)
    assert backoff.calculate(0) == 1.0  # 1.0 * 2^0
    assert backoff.calculate(1) == 2.0  # 1.0 * 2^1
    assert backoff.calculate(2) == 4.0  # 1.0 * 2^2
    assert backoff.calculate(3) == 5.0  # Would be 8.0, but capped
    assert backoff.calculate(10) == 5.0  # Would be 1024.0, but capped


def test_exponential_backoff_default_values() -> None:
    """Test exponential backoff with default values."""
    backoff = ExponentialBackoff()
    assert backoff.base_delay == 0.3
    assert backoff.max_delay is None
    assert backoff.calculate(0) == 0.3


def test_exponential_backoff_invalid_base_delay() -> None:
    """Test that negative base_delay raises ValueError."""
    with pytest.raises(ValueError, match=r"base_delay must be non-negative"):
        ExponentialBackoff(base_delay=-1.0)


def test_exponential_backoff_invalid_max_delay() -> None:
    """Test that non-positive max_delay raises ValueError."""
    with pytest.raises(ValueError, match=r"max_delay must be positive"):
        ExponentialBackoff(base_delay=1.0, max_delay=0)
    with pytest.raises(ValueError, match=r"max_delay must be positive"):
        ExponentialBackoff(base_delay=1.0, max_delay=-5.0)


def test_exponential_backoff_zero_base_delay() -> None:
    """Test exponential backoff with zero base_delay."""
    backoff = ExponentialBackoff(base_delay=0.0)
    assert backoff.calculate(0) == 0.0
    assert backoff.calculate(5) == 0.0


###################################
#     Tests for LinearBackoff     #
###################################


def test_linear_backoff_basic() -> None:
    """Test basic linear backoff calculation."""
    backoff = LinearBackoff(base_delay=1.0)
    assert backoff.calculate(0) == 1.0  # 1.0 * 1
    assert backoff.calculate(1) == 2.0  # 1.0 * 2
    assert backoff.calculate(2) == 3.0  # 1.0 * 3
    assert backoff.calculate(3) == 4.0  # 1.0 * 4


def test_linear_backoff_with_max_delay() -> None:
    """Test linear backoff with max_delay cap."""
    backoff = LinearBackoff(base_delay=2.0, max_delay=5.0)
    assert backoff.calculate(0) == 2.0  # 2.0 * 1
    assert backoff.calculate(1) == 4.0  # 2.0 * 2
    assert backoff.calculate(2) == 5.0  # Would be 6.0, but capped
    assert backoff.calculate(5) == 5.0  # Would be 12.0, but capped


def test_linear_backoff_default_values() -> None:
    """Test linear backoff with default values."""
    backoff = LinearBackoff()
    assert backoff.base_delay == 1.0
    assert backoff.max_delay is None
    assert backoff.calculate(0) == 1.0


def test_linear_backoff_invalid_base_delay() -> None:
    """Test that negative base_delay raises ValueError."""
    with pytest.raises(ValueError, match=r"base_delay must be non-negative"):
        LinearBackoff(base_delay=-1.0)


def test_linear_backoff_invalid_max_delay() -> None:
    """Test that non-positive max_delay raises ValueError."""
    with pytest.raises(ValueError, match=r"max_delay must be positive"):
        LinearBackoff(base_delay=1.0, max_delay=0)
    with pytest.raises(ValueError, match=r"max_delay must be positive"):
        LinearBackoff(base_delay=1.0, max_delay=-5.0)


def test_linear_backoff_zero_base_delay() -> None:
    """Test linear backoff with zero base_delay."""
    backoff = LinearBackoff(base_delay=0.0)
    assert backoff.calculate(0) == 0.0
    assert backoff.calculate(5) == 0.0


######################################
#     Tests for FibonacciBackoff     #
######################################


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


#####################################
#     Tests for ConstantBackoff     #
#####################################


def test_constant_backoff_basic() -> None:
    """Test basic constant backoff calculation."""
    backoff = ConstantBackoff(delay=2.5)
    assert backoff.calculate(0) == 2.5
    assert backoff.calculate(1) == 2.5
    assert backoff.calculate(10) == 2.5
    assert backoff.calculate(100) == 2.5


def test_constant_backoff_default_values() -> None:
    """Test constant backoff with default values."""
    backoff = ConstantBackoff()
    assert backoff.delay == 1.0
    assert backoff.calculate(0) == 1.0
    assert backoff.calculate(5) == 1.0


def test_constant_backoff_invalid_delay() -> None:
    """Test that negative delay raises ValueError."""
    with pytest.raises(ValueError, match=r"delay must be non-negative"):
        ConstantBackoff(delay=-1.0)


def test_constant_backoff_zero_delay() -> None:
    """Test constant backoff with zero delay."""
    backoff = ConstantBackoff(delay=0.0)
    assert backoff.calculate(0) == 0.0
    assert backoff.calculate(5) == 0.0


#########################################
#     Tests for BackoffStrategy ABC     #
#########################################


def test_backoff_strategy_is_abstract() -> None:
    """Test that BackoffStrategy cannot be instantiated directly."""
    with pytest.raises(TypeError, match=r"Can't instantiate abstract class"):
        BackoffStrategy()  # type: ignore[abstract]


def test_custom_backoff_strategy() -> None:
    """Test creating a custom backoff strategy."""

    class CustomBackoff(BackoffStrategy):
        def calculate(self, attempt: int) -> float:
            # Custom strategy: 10 * attempt + 5
            return 10 * attempt + 5

    backoff = CustomBackoff()
    assert backoff.calculate(0) == 5
    assert backoff.calculate(1) == 15
    assert backoff.calculate(2) == 25


#############################
#     Integration Tests     #
#############################


def test_different_strategies_comparison() -> None:
    """Compare different strategies for the same attempts."""
    exponential = ExponentialBackoff(base_delay=1.0)
    linear = LinearBackoff(base_delay=1.0)
    fibonacci = FibonacciBackoff(base_delay=1.0)
    constant = ConstantBackoff(delay=3.0)

    # At attempt 0
    assert exponential.calculate(0) == 1.0  # 1 * 2^0
    assert linear.calculate(0) == 1.0  # 1 * 1
    assert fibonacci.calculate(0) == 1.0  # 1 * fib(1)
    assert constant.calculate(0) == 3.0  # constant

    # At attempt 3
    assert exponential.calculate(3) == 8.0  # 1 * 2^3
    assert linear.calculate(3) == 4.0  # 1 * 4
    assert fibonacci.calculate(3) == 3.0  # 1 * fib(4) = 3
    assert constant.calculate(3) == 3.0  # constant

    # At attempt 5
    assert exponential.calculate(5) == 32.0  # 1 * 2^5
    assert linear.calculate(5) == 6.0  # 1 * 6
    assert fibonacci.calculate(5) == 8.0  # 1 * fib(6) = 8
    assert constant.calculate(5) == 3.0  # constant


def test_strategy_with_fractional_base_delay() -> None:
    """Test strategies with fractional base delays."""
    exp = ExponentialBackoff(base_delay=0.5)
    lin = LinearBackoff(base_delay=0.5)
    fib = FibonacciBackoff(base_delay=0.5)

    assert exp.calculate(2) == 2.0  # 0.5 * 4
    assert lin.calculate(2) == 1.5  # 0.5 * 3
    assert fib.calculate(2) == 1.0  # 0.5 * 2
