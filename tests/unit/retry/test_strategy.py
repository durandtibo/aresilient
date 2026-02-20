r"""Unit tests for retry strategy."""

from __future__ import annotations

from unittest.mock import Mock

import httpx

from aresilient.backoff.constant import ConstantBackoff
from aresilient.backoff.linear import LinearBackoff
from aresilient.retry.strategy import RetryStrategy


def test_retry_strategy_creation() -> None:
    """Test RetryStrategy initialization."""
    from aresilient.backoff.exponential import ExponentialBackoff

    strategy = RetryStrategy(
        jitter_factor=0.1,
    )

    assert strategy.jitter_factor == 0.1
    assert isinstance(strategy.backoff_strategy, ExponentialBackoff)
    assert strategy.max_wait_time is None


def test_retry_strategy_with_custom_backoff() -> None:
    """Test RetryStrategy with custom backoff strategy."""
    custom_backoff = LinearBackoff(base_delay=1.0)
    strategy = RetryStrategy(
        jitter_factor=0.0,
        backoff_strategy=custom_backoff,
    )

    assert strategy.backoff_strategy is custom_backoff


def test_retry_strategy_with_max_wait_time() -> None:
    """Test RetryStrategy with max wait time."""
    strategy = RetryStrategy(
        jitter_factor=0.0,
        max_wait_time=10.0,
    )

    assert strategy.max_wait_time == 10.0


def test_calculate_delay_exponential_default() -> None:
    """Test delay calculation with default exponential backoff."""
    strategy = RetryStrategy(
        jitter_factor=0.0,
    )

    # First retry (attempt=0): ExponentialBackoff default base_delay=0.3
    delay_0 = strategy.calculate_delay(attempt=0)
    assert delay_0 == 0.3  # 0.3 * (2^0) = 0.3

    # Second retry (attempt=1)
    delay_1 = strategy.calculate_delay(attempt=1)
    assert delay_1 == 0.6  # 0.3 * (2^1) = 0.6

    # Third retry (attempt=2)
    delay_2 = strategy.calculate_delay(attempt=2)
    assert delay_2 == 1.2  # 0.3 * (2^2) = 1.2


def test_calculate_delay_with_linear_backoff() -> None:
    """Test delay calculation with linear backoff."""
    linear_backoff = LinearBackoff(base_delay=1.0)
    strategy = RetryStrategy(
        jitter_factor=0.0,
        backoff_strategy=linear_backoff,
    )

    delay_0 = strategy.calculate_delay(attempt=0)
    assert delay_0 == 1.0  # 1.0 * (0 + 1) = 1.0

    delay_1 = strategy.calculate_delay(attempt=1)
    assert delay_1 == 2.0  # 1.0 * (1 + 1) = 2.0

    delay_2 = strategy.calculate_delay(attempt=2)
    assert delay_2 == 3.0  # 1.0 * (2 + 1) = 3.0


def test_calculate_delay_with_constant_backoff() -> None:
    """Test delay calculation with constant backoff."""
    constant_backoff = ConstantBackoff(delay=2.0)
    strategy = RetryStrategy(
        jitter_factor=0.0,
        backoff_strategy=constant_backoff,
    )

    delay_0 = strategy.calculate_delay(attempt=0)
    assert delay_0 == 2.0

    delay_1 = strategy.calculate_delay(attempt=1)
    assert delay_1 == 2.0


def test_calculate_delay_with_max_wait_time() -> None:
    """Test delay calculation with max wait time cap."""
    strategy = RetryStrategy(
        jitter_factor=0.0,
        max_wait_time=1.0,
    )

    # Without cap: would be 1.2, but capped to 1.0
    delay_2 = strategy.calculate_delay(attempt=2)
    assert delay_2 == 1.0


def test_calculate_delay_with_retry_after_header() -> None:
    """Test delay calculation respecting Retry-After header."""
    strategy = RetryStrategy(
        jitter_factor=0.0,
    )

    # Mock response with Retry-After header
    mock_response = Mock(spec=httpx.Response)
    mock_response.headers = {"Retry-After": "5"}

    delay = strategy.calculate_delay(attempt=0, response=mock_response)
    assert delay == 5.0


def test_calculate_delay_with_jitter() -> None:
    """Test delay calculation with jitter."""
    strategy = RetryStrategy(
        jitter_factor=0.5,
        backoff_strategy=ConstantBackoff(delay=1.0),
    )

    # With jitter, delay should be in range [base, base + jitter*base]
    # For attempt=0: base=1.0, jitter range=[0, 0.5], total=[1.0, 1.5]
    delay = strategy.calculate_delay(attempt=0)
    assert 1.0 <= delay <= 1.5
