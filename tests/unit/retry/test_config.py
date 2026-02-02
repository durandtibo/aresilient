r"""Unit tests for retry configuration dataclasses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aresilient.retry.config import CallbackConfig, RetryConfig

if TYPE_CHECKING:
    import httpx


def test_retry_config_creation() -> None:
    """Test RetryConfig dataclass creation."""
    config = RetryConfig(
        max_retries=3,
        backoff_factor=0.5,
        status_forcelist=(500, 502, 503),
        jitter_factor=0.1,
    )

    assert config.max_retries == 3
    assert config.backoff_factor == 0.5
    assert config.status_forcelist == (500, 502, 503)
    assert config.jitter_factor == 0.1
    assert config.retry_if is None
    assert config.backoff_strategy is None
    assert config.max_total_time is None
    assert config.max_wait_time is None


def test_retry_config_with_custom_predicate() -> None:
    """Test RetryConfig with custom retry predicate."""

    def custom_retry(response: httpx.Response | None, exc: Exception | None) -> bool:
        return response is not None and response.status_code >= 500

    config = RetryConfig(
        max_retries=5,
        backoff_factor=1.0,
        status_forcelist=(500,),
        jitter_factor=0.0,
        retry_if=custom_retry,
    )

    assert config.retry_if is custom_retry
    assert config.retry_if is not None


def test_retry_config_with_time_limits() -> None:
    """Test RetryConfig with time constraints."""
    config = RetryConfig(
        max_retries=10,
        backoff_factor=2.0,
        status_forcelist=(429, 500, 502, 503, 504),
        jitter_factor=0.2,
        max_total_time=30.0,
        max_wait_time=5.0,
    )

    assert config.max_total_time == 30.0
    assert config.max_wait_time == 5.0


def test_callback_config_creation() -> None:
    """Test CallbackConfig dataclass creation."""
    config = CallbackConfig()

    assert config.on_request is None
    assert config.on_retry is None
    assert config.on_success is None
    assert config.on_failure is None


def test_callback_config_with_all_callbacks() -> None:
    """Test CallbackConfig with all callbacks defined."""

    def on_req(info) -> None:
        pass

    def on_ret(info) -> None:
        pass

    def on_succ(info) -> None:
        pass

    def on_fail(info) -> None:
        pass

    config = CallbackConfig(
        on_request=on_req,
        on_retry=on_ret,
        on_success=on_succ,
        on_failure=on_fail,
    )

    assert config.on_request is on_req
    assert config.on_retry is on_ret
    assert config.on_success is on_succ
    assert config.on_failure is on_fail


def test_callback_config_partial_callbacks() -> None:
    """Test CallbackConfig with only some callbacks defined."""

    def on_req(info) -> None:
        pass

    config = CallbackConfig(on_request=on_req)

    assert config.on_request is on_req
    assert config.on_retry is None
    assert config.on_success is None
    assert config.on_failure is None
