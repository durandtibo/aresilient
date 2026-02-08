r"""Unit tests for asynchronous retry executor."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from aresilient.exceptions import HttpRequestError
from aresilient.retry import AsyncRetryExecutor, CallbackConfig, RetryConfig


def test_async_retry_executor_creation() -> None:
    """Test AsyncRetryExecutor initialization."""
    retry_config = RetryConfig(
        max_retries=3,
        backoff_factor=0.5,
        status_forcelist=(500, 502, 503),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()

    executor = AsyncRetryExecutor(retry_config, callback_config)

    assert executor.config is retry_config
    assert executor.strategy is not None
    assert executor.decider is not None
    assert executor.callbacks is not None
    assert executor.circuit_breaker is None


def test_async_retry_executor_with_circuit_breaker() -> None:
    """Test AsyncRetryExecutor with circuit breaker."""
    from aresilient.circuit_breaker import CircuitBreaker

    retry_config = RetryConfig(
        max_retries=3,
        backoff_factor=0.5,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=10.0)

    executor = AsyncRetryExecutor(retry_config, callback_config, circuit_breaker)

    assert executor.circuit_breaker is circuit_breaker


@pytest.mark.asyncio
async def test_async_retry_executor_successful_request() -> None:
    """Test successful async request without retries."""
    retry_config = RetryConfig(
        max_retries=3,
        backoff_factor=0.5,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(return_value=mock_response)

    response = await executor.execute(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
    )

    assert response is mock_response
    mock_request_func.assert_called_once()


@pytest.mark.asyncio
async def test_async_retry_executor_retry_on_retryable_status() -> None:
    """Test async retry on retryable status code."""
    retry_config = RetryConfig(
        max_retries=2,
        backoff_factor=0.01,  # Small backoff for test speed
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_response_fail = Mock(spec=httpx.Response, status_code=500)
    mock_response_success = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(side_effect=[mock_response_fail, mock_response_success])

    response = await executor.execute(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
    )

    assert response is mock_response_success
    assert mock_request_func.call_count == 2


@pytest.mark.asyncio
async def test_async_retry_executor_fails_on_non_retryable_status() -> None:
    """Test async failure on non-retryable status code."""
    retry_config = RetryConfig(
        max_retries=3,
        backoff_factor=0.5,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_response = Mock(spec=httpx.Response, status_code=404)
    mock_request_func = AsyncMock(return_value=mock_response)

    with pytest.raises(HttpRequestError) as exc_info:
        await executor.execute(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
        )

    assert exc_info.value.status_code == 404
    mock_request_func.assert_called_once()


@pytest.mark.asyncio
async def test_async_retry_executor_exhausts_retries() -> None:
    """Test all async retries are exhausted."""
    retry_config = RetryConfig(
        max_retries=2,
        backoff_factor=0.01,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_response = Mock(spec=httpx.Response, status_code=500)
    mock_request_func = AsyncMock(return_value=mock_response)

    with pytest.raises(HttpRequestError):
        await executor.execute(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
        )

    # Should be called max_retries + 1 times (initial + retries)
    assert mock_request_func.call_count == 3


@pytest.mark.asyncio
async def test_async_retry_executor_handles_timeout_exception() -> None:
    """Test async handling of timeout exception."""
    retry_config = RetryConfig(
        max_retries=2,
        backoff_factor=0.01,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(side_effect=[httpx.TimeoutException("Timeout"), mock_response])

    response = await executor.execute(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
    )

    assert response is mock_response
    assert mock_request_func.call_count == 2


@pytest.mark.asyncio
async def test_async_retry_executor_with_callbacks() -> None:
    """Test async executor invokes all callbacks."""
    on_request_mock = Mock()
    on_success_mock = Mock()

    retry_config = RetryConfig(
        max_retries=1,
        backoff_factor=0.01,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig(
        on_request=on_request_mock,
        on_success=on_success_mock,
    )
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(return_value=mock_response)

    await executor.execute(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
    )

    on_request_mock.assert_called_once()
    on_success_mock.assert_called_once()


@pytest.mark.asyncio
async def test_async_retry_executor_circuit_breaker_records_exception_failure() -> None:
    """Test circuit breaker records failure for retryable exception."""
    from aresilient.circuit_breaker import CircuitBreaker

    retry_config = RetryConfig(
        max_retries=2,
        backoff_factor=0.01,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=10.0)
    executor = AsyncRetryExecutor(retry_config, callback_config, circuit_breaker)

    # First attempt fails with timeout, second succeeds
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(side_effect=[httpx.TimeoutException("Timeout"), mock_response])

    response = await executor.execute(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
    )

    assert response is mock_response
    # Circuit breaker should be in CLOSED state after success
    assert circuit_breaker.state.name == "CLOSED"


@pytest.mark.asyncio
async def test_async_retry_executor_max_total_time_exceeded_with_response() -> None:
    """Test max_total_time exceeded with response available."""
    from unittest.mock import patch

    retry_config = RetryConfig(
        max_retries=5,
        backoff_factor=0.01,
        status_forcelist=(500,),
        jitter_factor=0.0,
        max_total_time=1.0,
    )
    callback_config = CallbackConfig()
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_response = Mock(spec=httpx.Response, status_code=500)
    mock_request_func = AsyncMock(return_value=mock_response)

    # Mock time to simulate exceeding max_total_time
    call_count = {"count": 0}

    def time_side_effect() -> float:
        call_count["count"] += 1
        return 0.0 if call_count["count"] == 1 else 2.0

    with patch("aresilient.retry.executor_async.time.time", side_effect=time_side_effect):
        with pytest.raises(HttpRequestError) as exc_info:
            await executor.execute(
                url="https://example.com",
                method="GET",
                request_func=mock_request_func,
            )

    # Should fail after first attempt due to time exceeded
    assert mock_request_func.call_count == 1
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_async_retry_executor_max_total_time_exceeded_with_exception_only() -> None:
    """Test max_total_time exceeded with exception but no response."""
    from unittest.mock import patch

    retry_config = RetryConfig(
        max_retries=5,
        backoff_factor=0.01,
        status_forcelist=(500,),
        jitter_factor=0.0,
        max_total_time=1.0,
    )
    callback_config = CallbackConfig()
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_request_func = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    # Mock time to simulate exceeding max_total_time
    call_count = {"count": 0}

    def time_side_effect() -> float:
        call_count["count"] += 1
        return 0.0 if call_count["count"] == 1 else 2.0

    with patch("aresilient.retry.executor_async.time.time", side_effect=time_side_effect):
        with pytest.raises(HttpRequestError) as exc_info:
            await executor.execute(
                url="https://example.com",
                method="GET",
                request_func=mock_request_func,
            )

    # Should fail after first attempt due to time exceeded
    assert mock_request_func.call_count == 1
    assert "max_total_time exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_retry_executor_handles_request_error() -> None:
    """Test handling of RequestError exception."""
    retry_config = RetryConfig(
        max_retries=2,
        backoff_factor=0.01,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(
        side_effect=[httpx.RequestError("Connection failed"), mock_response]
    )

    response = await executor.execute(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
    )

    assert response is mock_response
    assert mock_request_func.call_count == 2


@pytest.mark.asyncio
async def test_async_retry_executor_request_error_exhausts_retries() -> None:
    """Test RequestError exhausts all retries."""
    retry_config = RetryConfig(
        max_retries=2,
        backoff_factor=0.01,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_request_func = AsyncMock(side_effect=httpx.RequestError("Connection failed"))

    with pytest.raises(HttpRequestError) as exc_info:
        await executor.execute(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
        )

    # Should be called max_retries + 1 times
    assert mock_request_func.call_count == 3
    assert "failed after 3 attempts" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_retry_executor_timeout_exhausts_retries() -> None:
    """Test TimeoutException exhausts all retries."""
    retry_config = RetryConfig(
        max_retries=2,
        backoff_factor=0.01,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    executor = AsyncRetryExecutor(retry_config, callback_config)

    mock_request_func = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    with pytest.raises(HttpRequestError) as exc_info:
        await executor.execute(
            url="https://example.com",
            method="GET",
            request_func=mock_request_func,
        )

    # Should be called max_retries + 1 times
    assert mock_request_func.call_count == 3
    assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_retry_executor_circuit_breaker_records_status_code_failure() -> None:
    """Test circuit breaker records failure for retryable status
    code."""
    from aresilient.circuit_breaker import CircuitBreaker

    retry_config = RetryConfig(
        max_retries=2,
        backoff_factor=0.01,
        status_forcelist=(500,),
        jitter_factor=0.0,
    )
    callback_config = CallbackConfig()
    circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=10.0)
    executor = AsyncRetryExecutor(retry_config, callback_config, circuit_breaker)

    # First attempts fail with 500, last succeeds
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)
    mock_response_200 = Mock(spec=httpx.Response, status_code=200)
    mock_request_func = AsyncMock(
        side_effect=[mock_response_500, mock_response_500, mock_response_200]
    )

    response = await executor.execute(
        url="https://example.com",
        method="GET",
        request_func=mock_request_func,
    )

    assert response is mock_response_200
    # Circuit breaker should be in CLOSED state after success
    assert circuit_breaker.state.name == "CLOSED"
    # Should have recorded failures but then success reset the count
    assert circuit_breaker.failure_count == 0
