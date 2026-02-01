from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from aresilient.utils import calculate_sleep_time


##########################################
#     Tests for calculate_sleep_time     #
##########################################


@pytest.mark.parametrize(("attempt", "sleep_time"), [(0, 0.3), (1, 0.6), (2, 1.2)])
def test_calculate_sleep_time_exponential_backoff(attempt: int, sleep_time: float) -> None:
    """Test exponential backoff calculation without jitter."""
    assert (
        calculate_sleep_time(attempt, backoff_factor=0.3, jitter_factor=0.0, response=None)
        == sleep_time
    )


def test_calculate_sleep_time_with_jitter() -> None:
    """Test that jitter is correctly added to sleep time."""
    with patch("aresilient.utils.backoff.random.uniform", return_value=0.05):
        # Base sleep: 1.0 * 2^0 = 1.0
        # Jitter: 0.05 * 1.0 = 0.05
        # Total: 1.05
        assert (
            calculate_sleep_time(attempt=0, backoff_factor=1.0, jitter_factor=1.0, response=None)
            == 1.05
        )


def test_calculate_sleep_time_zero_jitter() -> None:
    """Test that zero jitter factor results in no jitter."""
    assert (
        calculate_sleep_time(attempt=0, backoff_factor=1.0, jitter_factor=0.0, response=None) == 1.0
    )


def test_calculate_sleep_time_with_retry_after_header() -> None:
    """Test that Retry-After header takes precedence over exponential
    backoff."""
    mock_response = Mock(spec=httpx.Response, headers={"Retry-After": "120"})

    # Should use 120 from Retry-After instead of 0.3 from backoff
    assert (
        calculate_sleep_time(
            attempt=0, backoff_factor=0.3, jitter_factor=0.0, response=mock_response
        )
        == 120.0
    )


def test_calculate_sleep_time_with_retry_after_and_jitter() -> None:
    """Test that jitter is applied to Retry-After value."""
    mock_response = Mock(spec=httpx.Response, headers={"Retry-After": "100"})

    with patch("aresilient.utils.backoff.random.uniform", return_value=0.1):
        # Base sleep from Retry-After: 100
        # Jitter: 0.1 * 100 = 10
        # Total: 110
        assert (
            calculate_sleep_time(
                attempt=0, backoff_factor=0.3, jitter_factor=1.0, response=mock_response
            )
            == 110.0
        )


def test_calculate_sleep_time_response_without_headers() -> None:
    """Test handling of response without headers attribute."""
    mock_response = Mock(spec=httpx.Response)
    del mock_response.headers  # Remove headers attribute

    # Should fall back to exponential backoff
    assert (
        calculate_sleep_time(
            attempt=0, backoff_factor=0.3, jitter_factor=0.0, response=mock_response
        )
        == 0.3
    )


def test_calculate_sleep_time_invalid_retry_after() -> None:
    """Test that invalid Retry-After header falls back to exponential
    backoff."""
    mock_response = Mock(spec=httpx.Response, headers={"Retry-After": "invalid"})

    # Should fall back to exponential backoff
    assert (
        calculate_sleep_time(
            attempt=0, backoff_factor=0.3, jitter_factor=0.0, response=mock_response
        )
        == 0.3
    )
