from __future__ import annotations

import pytest

from aresilient.core import validate_retry_params, validate_timeout

#######################################
#     Tests for validate_timeout     #
#######################################


@pytest.mark.parametrize("timeout", [0.1, 1.0, 10.0, 30.0, 100])
def test_validate_timeout_accepts_valid_values(timeout: float) -> None:
    """Test that validate_timeout accepts valid timeout values."""
    validate_timeout(timeout)


def test_validate_timeout_rejects_zero() -> None:
    """Test that validate_timeout rejects zero timeout."""
    with pytest.raises(ValueError, match=r"timeout must be > 0, got 0"):
        validate_timeout(0)


def test_validate_timeout_rejects_negative() -> None:
    """Test that validate_timeout rejects negative timeout."""
    with pytest.raises(ValueError, match=r"timeout must be > 0, got -1.0"):
        validate_timeout(-1.0)


def test_validate_timeout_rejects_negative_int() -> None:
    """Test that validate_timeout rejects negative integer timeout."""
    with pytest.raises(ValueError, match=r"timeout must be > 0, got -10"):
        validate_timeout(-10)


###########################################
#     Tests for validate_retry_params     #
###########################################


@pytest.mark.parametrize(("max_retries", "backoff_factor"), [(0, 0.0), (3, 0.3), (10, 1.5)])
def test_validate_retry_params_accepts_valid_values(
    max_retries: int, backoff_factor: float
) -> None:
    """Test that validate_retry_params accepts valid parameters."""
    validate_retry_params(max_retries=max_retries, backoff_factor=backoff_factor)


def test_validate_retry_params_rejects_negative_max_retries() -> None:
    """Test that validate_retry_params rejects negative max_retries."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0, got -1"):
        validate_retry_params(max_retries=-1, backoff_factor=0.3)


def test_validate_retry_params_rejects_negative_backoff_factor() -> None:
    """Test that validate_retry_params rejects negative
    backoff_factor."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0, got -0.5"):
        validate_retry_params(max_retries=3, backoff_factor=-0.5)


def test_validate_retry_params_rejects_both_negative() -> None:
    """Test that validate_retry_params rejects both negative values."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        validate_retry_params(max_retries=-1, backoff_factor=-0.5)


@pytest.mark.parametrize("jitter_factor", [0.0, 0.1, 1.0])
def test_validate_retry_params_accepts_valid_jitter_factor(jitter_factor: float) -> None:
    """Test that validate_retry_params accepts valid jitter_factor."""
    validate_retry_params(max_retries=3, backoff_factor=0.5, jitter_factor=jitter_factor)


def test_validate_retry_params_rejects_negative_jitter_factor() -> None:
    """Test that validate_retry_params rejects negative
    jitter_factor."""
    with pytest.raises(ValueError, match=r"jitter_factor must be >= 0, got -0.1"):
        validate_retry_params(max_retries=3, backoff_factor=0.5, jitter_factor=-0.1)


def test_validate_retry_params_accepts_valid_timeout() -> None:
    """Test that validate_retry_params accepts valid timeout."""
    validate_retry_params(max_retries=3, backoff_factor=0.5, timeout=10.0)
    validate_retry_params(max_retries=3, backoff_factor=0.5, timeout=0.1)


def test_validate_retry_params_rejects_negative_timeout() -> None:
    """Test that validate_retry_params rejects negative timeout."""
    with pytest.raises(ValueError, match=r"timeout must be > 0, got -1.0"):
        validate_retry_params(max_retries=3, backoff_factor=0.5, timeout=-1.0)


def test_validate_retry_params_rejects_zero_timeout() -> None:
    """Test that validate_retry_params rejects zero timeout."""
    with pytest.raises(ValueError, match=r"timeout must be > 0, got 0"):
        validate_retry_params(max_retries=3, backoff_factor=0.5, timeout=0)
