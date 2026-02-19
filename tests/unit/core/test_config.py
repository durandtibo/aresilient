r"""Unit tests for ClientConfig dataclass.

This file contains tests for the ClientConfig dataclass in
core/config.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from coola.equality import objects_are_equal

from aresilient.core import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
    ClientConfig,
)

if TYPE_CHECKING:
    import httpx

    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo

##################################
#     Tests for ClientConfig     #
##################################


def test_client_config_defaults() -> None:
    """Test that ClientConfig uses correct default values."""
    from aresilient.backoff.strategy import ExponentialBackoff

    config = ClientConfig()

    assert config.max_retries == DEFAULT_MAX_RETRIES
    assert isinstance(config.backoff_strategy, ExponentialBackoff)
    assert config.backoff_strategy.base_delay == 0.3
    assert config.status_forcelist == RETRY_STATUS_CODES
    assert config.jitter_factor == 0.0
    assert config.retry_if is None
    assert config.max_total_time is None
    assert config.max_wait_time is None
    assert config.circuit_breaker is None
    assert config.on_request is None
    assert config.on_retry is None
    assert config.on_success is None
    assert config.on_failure is None


@pytest.mark.parametrize("max_retries", [5, 0, 10])
def test_client_config_max_retries(max_retries: int) -> None:
    """Test that ClientConfig accepts custom max_retries values."""
    config = ClientConfig(max_retries=max_retries)
    assert config.max_retries == max_retries


@pytest.mark.parametrize("jitter_factor", [0.1, 0.0, 0.5])
def test_client_config_jitter_factor(jitter_factor: float) -> None:
    """Test that ClientConfig accepts custom jitter_factor values."""
    config = ClientConfig(jitter_factor=jitter_factor)
    assert config.jitter_factor == jitter_factor


@pytest.mark.parametrize("max_total_time", [30.0, 60.0, 120.0])
def test_client_config_max_total_time(max_total_time: float) -> None:
    """Test that ClientConfig accepts custom max_total_time values."""
    config = ClientConfig(max_total_time=max_total_time)
    assert config.max_total_time == max_total_time


@pytest.mark.parametrize("max_wait_time", [5.0, 10.0, 20.0])
def test_client_config_max_wait_time(max_wait_time: float) -> None:
    """Test that ClientConfig accepts custom max_wait_time values."""
    config = ClientConfig(max_wait_time=max_wait_time)
    assert config.max_wait_time == max_wait_time


@pytest.mark.parametrize("status_forcelist", [(500, 502, 503), (429, 500), (503,)])
def test_client_config_status_forcelist(status_forcelist: tuple[int, ...]) -> None:
    """Test that ClientConfig accepts custom status_forcelist values."""
    config = ClientConfig(status_forcelist=status_forcelist)
    assert config.status_forcelist == status_forcelist


def test_client_config_retry_if() -> None:
    """Test that ClientConfig accepts custom retry_if callback."""

    def custom_retry_if(
        response: httpx.Response | None,
        exception: Exception | None,  # noqa: ARG001
    ) -> bool:
        return response is not None and response.status_code == 503

    config = ClientConfig(retry_if=custom_retry_if)
    assert config.retry_if is custom_retry_if


def test_client_config_on_request() -> None:
    """Test that ClientConfig accepts on_request callback."""

    def on_request_callback(request_info: RequestInfo) -> None:
        pass

    config = ClientConfig(on_request=on_request_callback)
    assert config.on_request is on_request_callback


def test_client_config_on_retry() -> None:
    """Test that ClientConfig accepts on_retry callback."""

    def on_retry_callback(retry_info: RetryInfo) -> None:
        pass

    config = ClientConfig(on_retry=on_retry_callback)
    assert config.on_retry is on_retry_callback


def test_client_config_on_success() -> None:
    """Test that ClientConfig accepts on_success callback."""

    def on_success_callback(response_info: ResponseInfo) -> None:
        pass

    config = ClientConfig(on_success=on_success_callback)
    assert config.on_success is on_success_callback


def test_client_config_on_failure() -> None:
    """Test that ClientConfig accepts on_failure callback."""

    def on_failure_callback(failure_info: FailureInfo) -> None:
        pass

    config = ClientConfig(on_failure=on_failure_callback)
    assert config.on_failure is on_failure_callback


def test_client_config_validation_max_retries_negative() -> None:
    """Test that ClientConfig validates max_retries >= 0."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        ClientConfig(max_retries=-1)


def test_client_config_validation_jitter_factor_negative() -> None:
    """Test that ClientConfig validates jitter_factor >= 0."""
    with pytest.raises(ValueError, match=r"jitter_factor must be >= 0"):
        ClientConfig(jitter_factor=-0.1)


def test_client_config_validation_max_total_time_zero() -> None:
    """Test that ClientConfig validates max_total_time > 0."""
    with pytest.raises(ValueError, match=r"max_total_time must be > 0"):
        ClientConfig(max_total_time=0)


def test_client_config_validation_max_total_time_negative() -> None:
    """Test that ClientConfig validates max_total_time > 0
    (negative)."""
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
    config = ClientConfig(max_retries=3)
    merged = config.merge()

    assert merged.max_retries == 3
    assert merged is not config  # Should be a new instance


def test_client_config_merge_with_overrides() -> None:
    """Test that merge() applies non-None overrides."""
    from aresilient.backoff.strategy import ExponentialBackoff

    original_strategy = ExponentialBackoff(base_delay=0.5)
    config = ClientConfig(max_retries=3, backoff_strategy=original_strategy)
    merged = config.merge(max_retries=5)

    assert merged.max_retries == 5
    assert merged.backoff_strategy is original_strategy  # Unchanged
    assert config.max_retries == 3  # Original unchanged


def test_client_config_merge_with_none_values() -> None:
    """Test that merge() ignores None values."""
    from aresilient.backoff.strategy import LinearBackoff

    new_strategy = LinearBackoff(base_delay=1.0)
    config = ClientConfig(max_retries=3)
    merged = config.merge(max_retries=None, backoff_strategy=new_strategy)

    assert merged.max_retries == 3  # Not overridden (was None)
    assert merged.backoff_strategy is new_strategy  # Overridden


def test_client_config_merge_preserves_original() -> None:
    """Test that merge() does not modify original config."""
    config = ClientConfig(max_retries=3)
    merged = config.merge(max_retries=5)

    assert config.max_retries == 3  # Original unchanged
    assert merged.max_retries == 5  # New config has override


def test_client_config_to_dict() -> None:
    """Test that to_dict() returns all configuration parameters."""
    from aresilient.backoff.strategy import ExponentialBackoff

    strategy = ExponentialBackoff(base_delay=0.5)
    config = ClientConfig(
        max_retries=5,
        backoff_strategy=strategy,
        jitter_factor=0.1,
        max_total_time=60.0,
        max_wait_time=10.0,
    )
    assert objects_are_equal(
        config.to_dict(),
        {
            "max_retries": 5,
            "jitter_factor": 0.1,
            "max_total_time": 60.0,
            "max_wait_time": 10.0,
            "status_forcelist": RETRY_STATUS_CODES,
            "retry_if": None,
            "backoff_strategy": strategy,
            "circuit_breaker": None,
            "on_request": None,
            "on_retry": None,
            "on_success": None,
            "on_failure": None,
        },
    )


def test_client_config_to_dict_with_callbacks() -> None:
    """Test that to_dict() includes callback functions."""

    def on_request_callback(request_info: RequestInfo) -> None:
        pass

    def on_retry_callback(retry_info: RetryInfo) -> None:
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
    assert config.status_forcelist == RETRY_STATUS_CODES


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


###################################
#     Tests for Configuration     #
###################################


def test_default_timeout_value() -> None:
    """Test the DEFAULT_TIMEOUT value."""
    assert DEFAULT_TIMEOUT == 10.0


def test_default_max_retries_value() -> None:
    """Test the DEFAULT_MAX_RETRIES value."""
    assert DEFAULT_MAX_RETRIES == 3


def test_retry_status_codes_is_tuple() -> None:
    """Test that RETRY_STATUS_CODES is a tuple."""
    assert isinstance(RETRY_STATUS_CODES, tuple)


def test_retry_status_codes_contains_integers() -> None:
    """Test that all elements in RETRY_STATUS_CODES are integers."""
    assert all(isinstance(code, int) for code in RETRY_STATUS_CODES)


def test_retry_status_codes_length() -> None:
    """Test that RETRY_STATUS_CODES has the expected length."""
    assert len(RETRY_STATUS_CODES) == 5


def test_retry_status_codes_exact_value() -> None:
    """Test the exact value of RETRY_STATUS_CODES."""
    assert RETRY_STATUS_CODES == (429, 500, 502, 503, 504)


def test_retry_status_codes_are_sorted() -> None:
    """Test that RETRY_STATUS_CODES are in ascending order."""
    assert tuple(sorted(RETRY_STATUS_CODES)) == RETRY_STATUS_CODES


def test_retry_status_codes_has_no_duplicates() -> None:
    """Test that RETRY_STATUS_CODES has no duplicate values."""
    assert len(RETRY_STATUS_CODES) == len(set(RETRY_STATUS_CODES))


def test_constants_are_immutable_types() -> None:
    """Test that configuration constants are immutable types."""
    # These should be int, float, or tuple (immutable)
    assert isinstance(DEFAULT_MAX_RETRIES, int)
    assert isinstance(DEFAULT_TIMEOUT, float)
    assert isinstance(RETRY_STATUS_CODES, tuple)
