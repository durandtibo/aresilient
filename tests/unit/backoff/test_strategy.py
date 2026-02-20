r"""Unit tests for backward compatibility of backoff strategy module.

Tests that imports from ``aresilient.backoff.strategy`` and
``aresilient.backoff`` continue to work as expected, and that
``BackoffStrategy`` remains available as an alias for
``BaseBackoffStrategy``.
"""

from __future__ import annotations

import pytest

from aresilient.backoff import (
    BaseBackoffStrategy,
    ConstantBackoff,
    ExponentialBackoff,
    FibonacciBackoff,
    LinearBackoff,
)
from aresilient.backoff.strategy import (
    BackoffStrategy,
    ConstantBackoff as StrategyConstantBackoff,
    ExponentialBackoff as StrategyExponentialBackoff,
    FibonacciBackoff as StrategyFibonacciBackoff,
    LinearBackoff as StrategyLinearBackoff,
)


def test_backoff_strategy_alias() -> None:
    """Test that BackoffStrategy is an alias for BaseBackoffStrategy."""
    assert BackoffStrategy is BaseBackoffStrategy


def test_strategy_module_exports() -> None:
    """Test that strategy module re-exports all classes correctly."""
    assert StrategyExponentialBackoff is ExponentialBackoff
    assert StrategyLinearBackoff is LinearBackoff
    assert StrategyFibonacciBackoff is FibonacciBackoff
    assert StrategyConstantBackoff is ConstantBackoff


def test_base_backoff_strategy_is_abstract() -> None:
    """Test that BaseBackoffStrategy cannot be instantiated directly."""
    with pytest.raises(TypeError, match=r"Can't instantiate abstract class"):
        BaseBackoffStrategy()  # type: ignore[abstract]


def test_custom_backoff_strategy_via_base() -> None:
    """Test creating a custom backoff strategy using BackoffStrategy alias."""

    class CustomBackoff(BackoffStrategy):
        def calculate(self, attempt: int) -> float:
            # Custom strategy: 10 * attempt + 5
            return 10 * attempt + 5

    backoff = CustomBackoff()
    assert backoff.calculate(0) == 5
    assert backoff.calculate(1) == 15
    assert backoff.calculate(2) == 25


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
