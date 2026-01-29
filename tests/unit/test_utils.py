from __future__ import annotations

import pytest

from aresnet.utils import validate_retry_params


def test_validate_retry_params_accepts_valid_values() -> None:
    """Test that validate_retry_params accepts valid parameters."""
    validate_retry_params(3, 0.3)
    validate_retry_params(0, 0.0)
    validate_retry_params(10, 1.5)


def test_validate_retry_params_rejects_negative_max_retries() -> None:
    """Test that validate_retry_params rejects negative max_retries."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0, got -1"):
        validate_retry_params(-1, 0.3)


def test_validate_retry_params_rejects_negative_backoff_factor() -> None:
    """Test that validate_retry_params rejects negative
    backoff_factor."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0, got -0.5"):
        validate_retry_params(3, -0.5)


def test_validate_retry_params_rejects_both_negative() -> None:
    """Test that validate_retry_params rejects both negative values."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        validate_retry_params(-1, -0.5)
