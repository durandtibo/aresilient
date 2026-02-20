r"""Unit tests for ExponentialBackoff strategy."""

from __future__ import annotations

import pytest

from aresilient.backoff.exponential import ExponentialBackoff


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
