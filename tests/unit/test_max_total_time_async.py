r"""Parametrized unit tests for max_total_time functionality (async).

This test module tests max_total_time behavior across all async HTTP
methods using pytest parametrization.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from aresilient import HttpRequestError
from tests.helpers import HTTP_METHODS_ASYNC, HttpMethodTestCase

TEST_URL = "https://api.example.com/data"


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_max_total_time_exceeded_async(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that max_total_time stops retries when time budget is
    exceeded."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(return_value=mock_response_fail)
    setattr(mock_client, test_case.client_method, client_method)

    # Mock time.time() to simulate elapsed time exceeding budget
    call_count = {"count": 0}

    def time_side_effect() -> float:
        # First call: start_time = 0.0
        # Subsequent calls: return 2.0 to simulate 2 seconds elapsed (exceeds 1.0s budget)
        call_count["count"] += 1
        return 0.0 if call_count["count"] == 1 else 2.0

    with patch("aresilient.retry_executor.time.time", side_effect=time_side_effect):
        with pytest.raises(HttpRequestError) as exc_info:
            await test_case.method_func(
                TEST_URL,
                client=mock_client,
                max_retries=10,  # High retry count
                max_total_time=1.0,  # Low time budget
            )

        # Should fail without retrying due to max_total_time
        assert exc_info.value.status_code == 503
        # Should only be called once (initial attempt)
        assert client_method.call_count == 1
        # Should not have slept
        mock_asleep.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_max_total_time_not_exceeded_async(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that retries continue when max_total_time is not
    exceeded."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=[mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    # Mock time.time() - elapsed time stays within budget
    call_count = {"count": 0}

    def time_side_effect():
        # Always return times within budget
        call_count["count"] += 1
        return 0.5 * call_count["count"]  # 0.5, 1.0, 1.5, etc

    with patch("aresilient.retry_executor.time.time", side_effect=time_side_effect):
        response = await test_case.method_func(
            TEST_URL,
            client=mock_client,
            max_retries=3,
            max_total_time=10.0,  # High time budget
            backoff_factor=0.3,
        )

    assert response.status_code == test_case.status_code
    # Should have retried once
    assert client_method.call_count == 2
    mock_asleep.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_negative_max_total_time_async(test_case: HttpMethodTestCase) -> None:
    """Test that negative max_total_time raises ValueError."""
    with pytest.raises(ValueError, match=r"max_total_time must be > 0"):
        await test_case.method_func(TEST_URL, max_total_time=-1.0)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_zero_max_total_time_async(test_case: HttpMethodTestCase) -> None:
    """Test that zero max_total_time raises ValueError."""
    with pytest.raises(ValueError, match=r"max_total_time must be > 0"):
        await test_case.method_func(TEST_URL, max_total_time=0.0)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_max_total_time_none_async(
    test_case: HttpMethodTestCase,
    mock_asleep: Mock,
) -> None:
    """Test that max_total_time=None allows normal retry behavior."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.AsyncClient)
    client_method = AsyncMock(side_effect=[mock_response_fail, mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    response = await test_case.method_func(
        TEST_URL,
        client=mock_client,
        max_retries=3,
        max_total_time=None,  # No time budget
        backoff_factor=0.3,
    )

    assert response.status_code == test_case.status_code
    # Should have retried twice
    assert client_method.call_count == 3
    assert mock_asleep.call_count == 2
