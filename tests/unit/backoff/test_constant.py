r"""Unit tests for ConstantBackoff strategy."""

from __future__ import annotations

import pytest

from aresilient.backoff.constant import ConstantBackoff


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
