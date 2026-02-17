r"""Unit tests for ClientConfig dataclass.

This file contains tests for the ClientConfig dataclass in core/client_logic.py.
"""

from __future__ import annotations

import pytest

from aresilient.config import DEFAULT_BACKOFF_FACTOR, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from aresilient.core.client_logic import ClientConfig


#######################################
#     Tests for ClientConfig         #
#######################################


def test_client_config_defaults() -> None:
    """Test that ClientConfig uses correct default values."""
    config = ClientConfig()

    assert config.timeout == DEFAULT_TIMEOUT
    assert config.max_retries == DEFAULT_MAX_RETRIES
    assert config.backoff_factor == DEFAULT_BACKOFF_FACTOR
    assert config.jitter_factor == 0.0
    assert config.retry_if is None
    assert config.backoff_strategy is None
    assert config.max_total_time is None
    assert config.max_wait_time is None
    assert config.circuit_breaker is None
    assert config.on_request is None
    assert config.on_retry is None
    assert config.on_success is None
    assert config.on_failure is None


def test_client_config_custom_values() -> None:
    """Test that ClientConfig accepts custom values."""
    config = ClientConfig(
        timeout=30.0,
        max_retries=5,
        backoff_factor=1.0,
        jitter_factor=0.1,
        max_total_time=60.0,
        max_wait_time=10.0,
    )

    assert config.timeout == 30.0
    assert config.max_retries == 5
    assert config.backoff_factor == 1.0
    assert config.jitter_factor == 0.1
    assert config.max_total_time == 60.0
    assert config.max_wait_time == 10.0


def test_client_config_validation_max_retries_negative() -> None:
    """Test that ClientConfig validates max_retries >= 0."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        ClientConfig(max_retries=-1)


def test_client_config_validation_backoff_factor_negative() -> None:
    """Test that ClientConfig validates backoff_factor >= 0."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0"):
        ClientConfig(backoff_factor=-0.5)


def test_client_config_validation_jitter_factor_negative() -> None:
    """Test that ClientConfig validates jitter_factor >= 0."""
    with pytest.raises(ValueError, match=r"jitter_factor must be >= 0"):
        ClientConfig(jitter_factor=-0.1)


def test_client_config_validation_timeout_zero() -> None:
    """Test that ClientConfig validates timeout > 0."""
    with pytest.raises(ValueError, match=r"timeout must be > 0"):
        ClientConfig(timeout=0)


def test_client_config_validation_timeout_negative() -> None:
    """Test that ClientConfig validates timeout > 0 (negative)."""
    with pytest.raises(ValueError, match=r"timeout must be > 0"):
        ClientConfig(timeout=-10.0)


def test_client_config_validation_max_total_time_zero() -> None:
    """Test that ClientConfig validates max_total_time > 0."""
    with pytest.raises(ValueError, match=r"max_total_time must be > 0"):
        ClientConfig(max_total_time=0)


def test_client_config_validation_max_total_time_negative() -> None:
    """Test that ClientConfig validates max_total_time > 0 (negative)."""
    with pytest.raises(ValueError, match=r"max_total_time must be > 0"):
        ClientConfig(max_total_time=-30.0)


def test_client_config_validation_max_wait_time_zero() -> None:
    """Test that ClientConfig validates max_wait_time > 0."""
    with pytest.raises(ValueError, match=r"max_wait_time must be > 0"):
        ClientConfig(max_wait_time=0)


def test_client_config_validation_max_wait_time_negative() -> None:
    """Test that ClientConfig validates max_wait_time > 0 (negative)."""
    with pytest.raises(ValueError, match=r"max_wait_time must be > 0"):
        ClientConfig(max_wait_time=-5.0)


def test_client_config_merge_no_overrides() -> None:
    """Test that merge() with no overrides returns equivalent config."""
    config = ClientConfig(max_retries=3, timeout=10.0)
    merged = config.merge()

    assert merged.max_retries == 3
    assert merged.timeout == 10.0
    assert merged is not config  # Should be a new instance


def test_client_config_merge_with_overrides() -> None:
    """Test that merge() applies non-None overrides."""
    config = ClientConfig(max_retries=3, timeout=10.0, backoff_factor=0.5)
    merged = config.merge(max_retries=5, timeout=30.0)

    assert merged.max_retries == 5
    assert merged.timeout == 30.0
    assert merged.backoff_factor == 0.5  # Unchanged
    assert config.max_retries == 3  # Original unchanged
    assert config.timeout == 10.0  # Original unchanged


def test_client_config_merge_with_none_values() -> None:
    """Test that merge() ignores None values."""
    config = ClientConfig(max_retries=3, timeout=10.0)
    merged = config.merge(max_retries=None, timeout=30.0)

    assert merged.max_retries == 3  # Not overridden (was None)
    assert merged.timeout == 30.0  # Overridden


def test_client_config_merge_preserves_original() -> None:
    """Test that merge() does not modify original config."""
    config = ClientConfig(max_retries=3, timeout=10.0)
    merged = config.merge(max_retries=5)

    assert config.max_retries == 3  # Original unchanged
    assert merged.max_retries == 5  # New config has override


def test_client_config_to_dict() -> None:
    """Test that to_dict() returns all configuration parameters."""
    config = ClientConfig(
        max_retries=5,
        timeout=30.0,
        backoff_factor=1.0,
        jitter_factor=0.1,
        max_total_time=60.0,
        max_wait_time=10.0,
    )
    params = config.to_dict()

    # Note: timeout is not included in to_dict() because it's not passed to retry functions
    # It's only used when creating the httpx client
    assert params["max_retries"] == 5
    assert params["backoff_factor"] == 1.0
    assert params["jitter_factor"] == 0.1
    assert params["max_total_time"] == 60.0
    assert params["max_wait_time"] == 10.0
    assert params["retry_if"] is None
    assert params["backoff_strategy"] is None
    assert params["circuit_breaker"] is None
    assert params["on_request"] is None
    assert params["on_retry"] is None
    assert params["on_success"] is None
    assert params["on_failure"] is None
    assert "timeout" not in params  # timeout is used separately for httpx client creation


def test_client_config_to_dict_with_callbacks() -> None:
    """Test that to_dict() includes callback functions."""

    def on_request_callback(info):
        pass

    def on_retry_callback(info):
        pass

    config = ClientConfig(
        on_request=on_request_callback,
        on_retry=on_retry_callback,
    )
    params = config.to_dict()

    assert params["on_request"] is on_request_callback
    assert params["on_retry"] is on_retry_callback


def test_client_config_status_forcelist_default() -> None:
    """Test that status_forcelist has correct default value."""
    config = ClientConfig()
    # Default from RETRY_STATUS_CODES
    assert isinstance(config.status_forcelist, tuple)
    assert len(config.status_forcelist) > 0


def test_client_config_status_forcelist_custom() -> None:
    """Test that custom status_forcelist can be set."""
    custom_codes = (500, 502, 503)
    config = ClientConfig(status_forcelist=custom_codes)

    assert config.status_forcelist == custom_codes


def test_client_config_merge_validation() -> None:
    """Test that merge() validates the merged config."""
    config = ClientConfig(max_retries=3)

    # This should raise ValueError because max_retries=-1 is invalid
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        config.merge(max_retries=-1)


def test_client_config_immutability_after_merge() -> None:
    """Test that merging creates independent configs."""
    config1 = ClientConfig(max_retries=3)
    config2 = config1.merge(max_retries=5)
    config3 = config1.merge(max_retries=7)

    assert config1.max_retries == 3
    assert config2.max_retries == 5
    assert config3.max_retries == 7
