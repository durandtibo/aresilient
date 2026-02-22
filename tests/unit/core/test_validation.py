r"""Unit tests for validation functions."""

from __future__ import annotations

import httpx
import pytest

from aresilient.core import validate_retry_params, validate_timeout

######################################
#     Tests for validate_timeout     #
######################################


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


def test_validate_timeout_accepts_httpx_timeout_object() -> None:
    """Test that validate_timeout accepts httpx.Timeout objects."""
    validate_timeout(httpx.Timeout(10.0))


def test_validate_timeout_accepts_httpx_timeout_with_connect() -> None:
    """Test that validate_timeout accepts httpx.Timeout with connect
    timeout."""
    validate_timeout(httpx.Timeout(10.0, connect=5.0))


###########################################
#     Tests for validate_retry_params     #
###########################################


@pytest.mark.parametrize("max_retries", [0, 3, 10])
def test_validate_retry_params_accepts_valid_values(
    max_retries: int,
) -> None:
    """Test that validate_retry_params accepts valid parameters."""
    validate_retry_params(max_retries=max_retries)


def test_validate_retry_params_rejects_negative_max_retries() -> None:
    """Test that validate_retry_params rejects negative max_retries."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0, got -1"):
        validate_retry_params(max_retries=-1)


@pytest.mark.parametrize("jitter_factor", [0.0, 0.1, 1.0])
def test_validate_retry_params_accepts_valid_jitter_factor(jitter_factor: float) -> None:
    """Test that validate_retry_params accepts valid jitter_factor."""
    validate_retry_params(max_retries=3, jitter_factor=jitter_factor)


def test_validate_retry_params_rejects_negative_jitter_factor() -> None:
    """Test that validate_retry_params rejects negative
    jitter_factor."""
    with pytest.raises(ValueError, match=r"jitter_factor must be >= 0, got -0.1"):
        validate_retry_params(max_retries=3, jitter_factor=-0.1)


@pytest.mark.parametrize("max_total_time", [0.1, 30.0, 60.0])
def test_validate_retry_params_accepts_valid_max_total_time(max_total_time: float) -> None:
    """Test that validate_retry_params accepts valid max_total_time."""
    validate_retry_params(max_retries=3, max_total_time=max_total_time)


def test_validate_retry_params_rejects_zero_max_total_time() -> None:
    """Test that validate_retry_params rejects max_total_time of
    zero."""
    with pytest.raises(ValueError, match=r"max_total_time must be > 0, got 0"):
        validate_retry_params(max_retries=3, max_total_time=0)


def test_validate_retry_params_rejects_negative_max_total_time() -> None:
    """Test that validate_retry_params rejects negative
    max_total_time."""
    with pytest.raises(ValueError, match=r"max_total_time must be > 0, got -30.0"):
        validate_retry_params(max_retries=3, max_total_time=-30.0)


@pytest.mark.parametrize("max_wait_time", [0.1, 5.0, 10.0])
def test_validate_retry_params_accepts_valid_max_wait_time(max_wait_time: float) -> None:
    """Test that validate_retry_params accepts valid max_wait_time."""
    validate_retry_params(max_retries=3, max_wait_time=max_wait_time)


def test_validate_retry_params_rejects_zero_max_wait_time() -> None:
    """Test that validate_retry_params rejects max_wait_time of zero."""
    with pytest.raises(ValueError, match=r"max_wait_time must be > 0, got 0"):
        validate_retry_params(max_retries=3, max_wait_time=0)


def test_validate_retry_params_rejects_negative_max_wait_time() -> None:
    """Test that validate_retry_params rejects negative max_wait_time."""
    with pytest.raises(ValueError, match=r"max_wait_time must be > 0, got -5.0"):
        validate_retry_params(max_retries=3, max_wait_time=-5.0)
