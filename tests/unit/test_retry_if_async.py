r"""Unit tests for retry_if custom predicate functionality (async)."""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresilient import HttpRequestError
from aresilient.request_async import request_with_automatic_retry_async

TEST_URL = "https://api.example.com/data"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=200, text="success")


@pytest.fixture
def mock_async_request_func(mock_response: httpx.Response) -> Mock:
    async def _mock(**kwargs):
        return mock_response

    return Mock(side_effect=_mock)


########################################################
#     Tests for retry_if with successful responses     #
########################################################


@pytest.mark.asyncio
async def test_retry_if_returns_false_for_successful_response(
    mock_response: httpx.Response, mock_async_request_func: Mock, mock_asleep: Mock
) -> None:
    """Test retry_if that returns False for successful response (no retry)."""

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return False

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        retry_if=retry_predicate,
    )

    assert response == mock_response
    mock_async_request_func.assert_called_once_with(url=TEST_URL)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_retry_if_returns_true_for_successful_response(mock_asleep: Mock) -> None:
    """Test retry_if that returns True even for successful response (triggers retry)."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=200, text="success")

    async def _mock(**kwargs):
        return mock_response_ok

    mock_async_request_func = Mock(side_effect=_mock)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Always retry - should exhaust retries
        return True

    with pytest.raises(HttpRequestError, match="failed with status 200 after 4 attempts"):
        await request_with_automatic_retry_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_async_request_func,
            retry_if=retry_predicate,
            max_retries=3,
        )

    # Should have tried 4 times (initial + 3 retries)
    assert mock_async_request_func.call_count == 4
    # Should have slept 3 times between attempts
    assert mock_asleep.call_count == 3


@pytest.mark.asyncio
async def test_retry_if_checks_response_content(mock_asleep: Mock) -> None:
    """Test retry_if that checks response content and retries on specific text."""
    mock_response_retry = Mock(spec=httpx.Response, status_code=200, text="please retry")
    mock_response_ok = Mock(spec=httpx.Response, status_code=200, text="success")

    responses = [mock_response_retry, mock_response_ok]
    call_count = 0

    async def _mock(**kwargs):
        nonlocal call_count
        result = responses[call_count]
        call_count += 1
        return result

    mock_async_request_func = Mock(side_effect=_mock)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry if response contains "retry"
        if response and "retry" in response.text.lower():
            return True
        return False

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_async_request_func.call_count == 2
    mock_asleep.assert_called_once()


#####################################################
#     Tests for retry_if with error responses     #
#####################################################


@pytest.mark.asyncio
async def test_retry_if_returns_false_for_error_response(mock_asleep: Mock) -> None:
    """Test retry_if that returns False for error response (no retry, immediate fail)."""
    mock_response_error = Mock(spec=httpx.Response, status_code=500)

    async def _mock(**kwargs):
        return mock_response_error

    mock_async_request_func = Mock(side_effect=_mock)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return False  # Never retry

    with pytest.raises(HttpRequestError, match="failed with status 500"):
        await request_with_automatic_retry_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_async_request_func,
            retry_if=retry_predicate,
        )

    # Should only try once since retry_if returns False
    mock_async_request_func.assert_called_once_with(url=TEST_URL)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_retry_if_returns_true_for_error_response(mock_asleep: Mock) -> None:
    """Test retry_if that returns True for error response (triggers retry)."""
    mock_response_error = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)

    responses = [mock_response_error, mock_response_ok]
    call_count = 0

    async def _mock(**kwargs):
        nonlocal call_count
        result = responses[call_count]
        call_count += 1
        return result

    mock_async_request_func = Mock(side_effect=_mock)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        if response and response.status_code >= 500:
            return True
        return False

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_async_request_func.call_count == 2
    mock_asleep.assert_called_once()


###################################################
#     Tests for retry_if with exceptions     #
###################################################


@pytest.mark.asyncio
async def test_retry_if_returns_false_for_exception(mock_asleep: Mock) -> None:
    """Test retry_if that returns False for exceptions (no retry)."""

    async def _mock(**kwargs):
        raise httpx.TimeoutException("timeout")

    mock_async_request_func = Mock(side_effect=_mock)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        return False  # Never retry

    with pytest.raises(HttpRequestError, match="timed out"):
        await request_with_automatic_retry_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_async_request_func,
            retry_if=retry_predicate,
        )

    # Should only try once
    mock_async_request_func.assert_called_once()
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_retry_if_returns_true_for_exception(mock_asleep: Mock) -> None:
    """Test retry_if that returns True for exceptions (triggers retry)."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)

    call_count = 0

    async def _mock(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.TimeoutException("timeout")
        return mock_response_ok

    mock_async_request_func = Mock(side_effect=_mock)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry on timeout exceptions
        if isinstance(exception, httpx.TimeoutException):
            return True
        return False

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_async_request_func.call_count == 2
    mock_asleep.assert_called_once()


@pytest.mark.asyncio
async def test_retry_if_with_connection_error(mock_asleep: Mock) -> None:
    """Test retry_if that handles connection errors."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)

    call_count = 0

    async def _mock(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("connection failed")
        return mock_response_ok

    mock_async_request_func = Mock(side_effect=_mock)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry on connection errors
        if isinstance(exception, httpx.ConnectError):
            return True
        return False

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_async_request_func.call_count == 2


@pytest.mark.asyncio
async def test_retry_if_exhausts_retries_with_exception(mock_asleep: Mock) -> None:
    """Test retry_if exhausts retries when exception keeps occurring."""

    async def _mock(**kwargs):
        raise httpx.TimeoutException("timeout")

    mock_async_request_func = Mock(side_effect=_mock)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Always retry timeouts
        if isinstance(exception, httpx.TimeoutException):
            return True
        return False

    with pytest.raises(HttpRequestError, match="timed out"):
        await request_with_automatic_retry_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_async_request_func,
            retry_if=retry_predicate,
            max_retries=2,
        )

    # Should try 3 times (initial + 2 retries)
    assert mock_async_request_func.call_count == 3


#########################################################
#     Tests for retry_if with mixed scenarios     #
#########################################################


@pytest.mark.asyncio
async def test_retry_if_complex_logic(mock_asleep: Mock) -> None:
    """Test retry_if with complex custom logic combining response and exception checks."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500, text="server error")
    mock_response_200_retry = Mock(spec=httpx.Response, status_code=200, text="rate limit exceeded")
    mock_response_ok = Mock(spec=httpx.Response, status_code=200, text="success")

    responses = [mock_response_500, mock_response_200_retry, mock_response_ok]
    call_count = 0

    async def _mock(**kwargs):
        nonlocal call_count
        result = responses[call_count]
        call_count += 1
        return result

    mock_async_request_func = Mock(side_effect=_mock)

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        # Retry on server errors
        if response and response.status_code >= 500:
            return True
        # Retry if response contains rate limit message
        if response and "rate limit" in response.text.lower():
            return True
        # Retry on network errors
        if isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)):
            return True
        return False

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        retry_if=retry_predicate,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_async_request_func.call_count == 3
    assert mock_asleep.call_count == 2


@pytest.mark.asyncio
async def test_retry_if_none_uses_default_behavior(mock_asleep: Mock) -> None:
    """Test that when retry_if is None, default status_forcelist behavior is used."""
    mock_response_503 = Mock(spec=httpx.Response, status_code=503)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)

    responses = [mock_response_503, mock_response_ok]
    call_count = 0

    async def _mock(**kwargs):
        nonlocal call_count
        result = responses[call_count]
        call_count += 1
        return result

    mock_async_request_func = Mock(side_effect=_mock)

    # No retry_if provided - should use default behavior
    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        status_forcelist=(503,),
    )

    assert response == mock_response_ok
    assert mock_async_request_func.call_count == 2
    mock_asleep.assert_called_once()


############################################
#     Tests for retry_if with callbacks     #
############################################


@pytest.mark.asyncio
async def test_retry_if_with_on_retry_callback(mock_asleep: Mock) -> None:
    """Test retry_if works correctly with on_retry callback."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)

    responses = [mock_response_500, mock_response_ok]
    call_count = 0

    async def _mock(**kwargs):
        nonlocal call_count
        result = responses[call_count]
        call_count += 1
        return result

    mock_async_request_func = Mock(side_effect=_mock)
    retry_callback = Mock()

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        if response and response.status_code >= 500:
            return True
        return False

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        retry_if=retry_predicate,
        on_retry=retry_callback,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_async_request_func.call_count == 2
    retry_callback.assert_called_once()


@pytest.mark.asyncio
async def test_retry_if_with_on_failure_callback(mock_asleep: Mock) -> None:
    """Test retry_if triggers on_failure callback when retries exhausted."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)

    async def _mock(**kwargs):
        return mock_response_500

    mock_async_request_func = Mock(side_effect=_mock)
    failure_callback = Mock()

    def retry_predicate(response: httpx.Response | None, exception: Exception | None) -> bool:
        if response and response.status_code >= 500:
            return True
        return False

    with pytest.raises(HttpRequestError):
        await request_with_automatic_retry_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_async_request_func,
            retry_if=retry_predicate,
            on_failure=failure_callback,
            max_retries=2,
        )

    failure_callback.assert_called_once()
