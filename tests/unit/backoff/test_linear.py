r"""Unit tests for LinearBackoff strategy."""

from __future__ import annotations

import pytest

from aresilient.backoff.linear import LinearBackoff


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
