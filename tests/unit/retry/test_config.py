r"""Unit tests for retry configuration dataclasses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aresilient.retry import CallbackConfig, RetryConfig

if TYPE_CHECKING:
    import httpx

    from aresilient import FailureInfo, RequestInfo, ResponseInfo, RetryInfo


def custom_retry(
    response: httpx.Response | None,
    exc: Exception | None,  # noqa: ARG001
) -> bool:
    return response is not None and response.status_code >= 500


def on_request(info: RequestInfo) -> None:
    pass


def on_retry(info: RetryInfo) -> None:
    pass


def on_success(info: ResponseInfo) -> None:
    pass


def on_failure(info: FailureInfo) -> None:
    pass


def test_retry_config_creation() -> None:
    """Test RetryConfig dataclass creation."""
    config = RetryConfig(
        max_retries=3,
        status_forcelist=(500, 502, 503),
        jitter_factor=0.1,
    )

    assert config.max_retries == 3
    assert config.status_forcelist == (500, 502, 503)
    assert config.jitter_factor == 0.1
    assert config.retry_if is None
    assert config.backoff_strategy is None
    assert config.max_total_time is None
    assert config.max_wait_time is None


def test_retry_config_with_custom_predicate() -> None:
    """Test RetryConfig with custom retry predicate."""
    config = RetryConfig(
        max_retries=5,
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
    config = CallbackConfig(
        on_request=on_request,
        on_retry=on_retry,
        on_success=on_success,
        on_failure=on_failure,
    )

    assert config.on_request is on_request
    assert config.on_retry is on_retry
    assert config.on_success is on_success
    assert config.on_failure is on_failure


def test_callback_config_partial_callbacks() -> None:
    """Test CallbackConfig with only some callbacks defined."""
    config = CallbackConfig(on_request=on_request)

    assert config.on_request is on_request
    assert config.on_retry is None
    assert config.on_success is None
    assert config.on_failure is None
