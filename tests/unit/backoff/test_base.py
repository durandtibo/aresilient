r"""Unit tests for BaseBackoffStrategy abstract base class."""

from __future__ import annotations

import pytest

from aresilient.backoff.base import BaseBackoffStrategy


def test_base_backoff_strategy_is_abstract() -> None:
    """Test that BaseBackoffStrategy cannot be instantiated directly."""
    with pytest.raises(TypeError, match=r"Can't instantiate abstract class"):
        BaseBackoffStrategy()  # type: ignore[abstract]


def test_custom_backoff_strategy() -> None:
    """Test creating a custom backoff strategy."""

    class CustomBackoff(BaseBackoffStrategy):
        def calculate(self, attempt: int) -> float:
            return 10 * attempt + 5

    backoff = CustomBackoff()
    assert backoff.calculate(0) == 5
    assert backoff.calculate(1) == 15
    assert backoff.calculate(2) == 25
