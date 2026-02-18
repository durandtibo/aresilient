r"""Unit tests for Retry-After header support and jitter functionality
(async version)."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, call, patch

import httpx
import pytest

from aresilient.request_async import request_async
from aresilient.core import ClientConfig

TEST_URL = "https://api.example.com/data"


################################################
#     Tests for Retry-After in async retry     #
################################################


@pytest.mark.asyncio
async def test_request_with_retry_after_header_integer_async(mock_asleep: Mock) -> None:
    """Test that Retry-After header with integer is used instead of
    exponential backoff."""
    # Create a mock response with Retry-After header
    mock_fail_response = Mock(spec=httpx.Response)
    mock_fail_response.status_code = 503
    mock_fail_response.headers = {"Retry-After": "120"}

    mock_success_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(side_effect=[mock_fail_response, mock_success_response])

    response = await request_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        config=ClientConfig(status_forcelist=(503,)),
    )

    assert response == mock_success_response
    # Should sleep for 120 seconds (from Retry-After header) instead of 0.3 (exponential backoff)
    # With jitter mocked to 0, the total should be exactly 120
    mock_asleep.assert_called_once_with(120.0)


@pytest.mark.asyncio
async def test_request_with_retry_after_header_multiple_retries_async(mock_asleep: Mock) -> None:
    """Test Retry-After header is used for each retry that has it."""
    # First retry has Retry-After: 60
    mock_fail_response_1 = Mock(spec=httpx.Response)
    mock_fail_response_1.status_code = 429
    mock_fail_response_1.headers = {"Retry-After": "60"}

    # Second retry has Retry-After: 30
    mock_fail_response_2 = Mock(spec=httpx.Response)
    mock_fail_response_2.status_code = 429
    mock_fail_response_2.headers = {"Retry-After": "30"}

    mock_success_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(
        side_effect=[mock_fail_response_1, mock_fail_response_2, mock_success_response]
    )

    response = await request_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        config=ClientConfig(status_forcelist=(429,)),
    )

    assert response == mock_success_response
    # Should sleep for 60 and 30 seconds respectively
    assert mock_asleep.call_args_list == [call(60.0), call(30.0)]


@pytest.mark.asyncio
async def test_request_without_retry_after_uses_exponential_backoff_async(
    mock_asleep: Mock,
) -> None:
    """Test that exponential backoff is used when Retry-After header is
    not present."""
    # Response without Retry-After header
    mock_fail_response = Mock(spec=httpx.Response)
    mock_fail_response.status_code = 503
    mock_fail_response.headers = {}

    mock_success_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(side_effect=[mock_fail_response, mock_success_response])

    response = await request_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        config=ClientConfig(status_forcelist=(503,)),
    )

    assert response == mock_success_response
    # Should use exponential backoff (0.3 seconds for first retry with jitter=0)
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
async def test_request_with_retry_after_mixed_with_backoff_async(mock_asleep: Mock) -> None:
    """Test mixing Retry-After header and exponential backoff in
    different retries."""
    # First retry has Retry-After
    mock_fail_response_1 = Mock(spec=httpx.Response)
    mock_fail_response_1.status_code = 429
    mock_fail_response_1.headers = {"Retry-After": "45"}

    # Second retry does not have Retry-After, should use exponential backoff
    mock_fail_response_2 = Mock(spec=httpx.Response)
    mock_fail_response_2.status_code = 503
    mock_fail_response_2.headers = {}

    mock_success_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(
        side_effect=[mock_fail_response_1, mock_fail_response_2, mock_success_response]
    )

    response = await request_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_request_func,
        config=ClientConfig(status_forcelist=(429, 503)),
    )

    assert response == mock_success_response
    # First sleep: 45 (from Retry-After)
    # Second sleep: 0.6 (exponential backoff for attempt 1, jitter=0)
    assert mock_asleep.call_args_list == [call(45.0), call(0.6)]


##########################################
#     Tests for jitter functionality     #
##########################################


@pytest.mark.asyncio
async def test_request_with_jitter_applied_async(mock_asleep: Mock) -> None:
    """Test that jitter is applied to backoff sleep time."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_fail_response.headers = {}
    mock_success_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(side_effect=[mock_fail_response, mock_success_response])

    # Mock random.uniform to return a specific jitter value
    with patch("aresilient.backoff.sleep.random.uniform", return_value=0.05):  # 5% jitter
        response = await request_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(status_forcelist=(503,), backoff_factor=1.0, jitter_factor=1.0),  # Jitter factor of 1.0
        )

    assert response == mock_success_response
    # Base sleep: 1.0 * (2^0) = 1.0
    # Jitter: 0.05 * 1.0 = 0.05
    # Total: 1.05
    mock_asleep.assert_called_once_with(1.05)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "jitter_multiplier",
    [
        pytest.param(0.0, id="no_jitter"),
        pytest.param(0.01, id="1%_jitter"),
        pytest.param(0.05, id="5%_jitter"),
        pytest.param(0.1, id="10%_jitter"),
    ],
)
async def test_request_jitter_range_async(
    jitter_multiplier: float,
    mock_asleep: Mock,
) -> None:
    """Test that jitter is within expected range (0-10% of base)."""
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_fail_response.headers = {}
    mock_success_response = Mock(spec=httpx.Response, status_code=200)

    mock_request_func = AsyncMock(side_effect=[mock_fail_response, mock_success_response])

    with patch("aresilient.backoff.sleep.random.uniform", return_value=jitter_multiplier):
        response = await request_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(status_forcelist=(503,), backoff_factor=2.0, jitter_factor=1.0),
        )

    assert response == mock_success_response
    # Base sleep: 2.0 * (2^0) = 2.0
    # Jitter: jitter_multiplier * 2.0
    expected_sleep = 2.0 * (1 + jitter_multiplier)
    mock_asleep.assert_called_once_with(expected_sleep)


@pytest.mark.asyncio
async def test_request_jitter_with_retry_after_async(mock_asleep: Mock) -> None:
    """Test that jitter is also applied when using Retry-After
    header."""
    mock_fail_response = Mock(spec=httpx.Response)
    mock_fail_response.status_code = 429
    mock_fail_response.headers = {"Retry-After": "100"}

    mock_success_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(side_effect=[mock_fail_response, mock_success_response])

    # Mock jitter to 10% (maximum)
    with patch("aresilient.backoff.sleep.random.uniform", return_value=0.1):
        response = await request_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_request_func,
            config=ClientConfig(status_forcelist=(429,), jitter_factor=1.0),  # Jitter factor of 1.0
        )

    assert response == mock_success_response
    # Base sleep: 100 (from Retry-After)
    # Jitter: 0.1 * 100 = 10
    # Total: 110
    mock_asleep.assert_called_once_with(110.0)
