r"""Unit tests for async callback functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, call

import httpx
import pytest

from aresilient import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    HttpRequestError,
    RequestInfo,
    RetryInfo,
)
from aresilient.request_async import request_with_automatic_retry_async

TEST_URL = "https://api.example.com/data"


#########################################
#     Tests for on_request callback     #
#########################################


@pytest.mark.asyncio
async def test_on_request_callback_called_on_first_attempt_async(
    mock_response: httpx.Response, mock_async_request_func: AsyncMock, mock_asleep: Mock
) -> None:
    """Test that on_request callback is called before the first attempt
    (async)."""
    on_request_callback = Mock()

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        on_request=on_request_callback,
    )

    assert response == mock_response
    on_request_callback.assert_called_once_with(
        RequestInfo(url=TEST_URL, method="GET", attempt=1, max_retries=DEFAULT_MAX_RETRIES)
    )
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_on_request_callback_called_on_each_retry_async(
    mock_response: httpx.Response, mock_asleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_request callback is called before each retry attempt
    (async)."""
    on_request_callback = Mock()
    mock_async_request_func = AsyncMock(
        side_effect=[mock_response_fail, mock_response_fail, mock_response]
    )

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        status_forcelist=(500,),
        on_request=on_request_callback,
    )

    assert response == mock_response
    assert on_request_callback.call_args_list == [
        call(RequestInfo(url=TEST_URL, method="GET", attempt=1, max_retries=DEFAULT_MAX_RETRIES)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=2, max_retries=DEFAULT_MAX_RETRIES)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=3, max_retries=DEFAULT_MAX_RETRIES)),
    ]
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


#######################################
#     Tests for on_retry callback     #
#######################################


@pytest.mark.asyncio
async def test_on_retry_callback_called_before_retry_async(
    mock_response: httpx.Response, mock_asleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_retry callback is called before each retry
    (async)."""
    on_retry_callback = Mock()
    mock_async_request_func = AsyncMock(side_effect=[mock_response_fail, mock_response])

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        status_forcelist=(500,),
        on_retry=on_retry_callback,
    )

    assert response == mock_response
    on_retry_callback.assert_called_once_with(
        RetryInfo(
            url=TEST_URL,
            method="GET",
            attempt=2,
            max_retries=DEFAULT_MAX_RETRIES,
            wait_time=DEFAULT_BACKOFF_FACTOR,
            error=None,
            status_code=500,
        )
    )
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
async def test_on_retry_callback_not_called_on_first_success_async(
    mock_response: httpx.Response, mock_async_request_func: AsyncMock, mock_asleep: Mock
) -> None:
    """Test that on_retry callback is not called when request succeeds
    on first attempt (async)."""
    on_retry_callback = Mock()

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        on_retry=on_retry_callback,
    )

    assert response == mock_response
    on_retry_callback.assert_not_called()
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_on_retry_callback_with_timeout_exception_async(
    mock_asleep: Mock,
) -> None:
    """Test that on_retry callback receives error information on timeout
    (async)."""
    on_retry_callback = Mock()
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_async_request_func = AsyncMock(
        side_effect=[httpx.TimeoutException("timeout"), mock_response]
    )

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        on_retry=on_retry_callback,
    )

    assert response == mock_response
    on_retry_callback.assert_called_once()
    call_args = on_retry_callback.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "GET"
    assert call_args.attempt == 2  # Next attempt
    assert call_args.max_retries == DEFAULT_MAX_RETRIES
    assert call_args.wait_time == DEFAULT_BACKOFF_FACTOR
    assert isinstance(call_args.error, httpx.TimeoutException)
    assert call_args.status_code is None
    mock_asleep.assert_called_once_with(0.3)


#########################################
#     Tests for on_success callback     #
#########################################


@pytest.mark.asyncio
async def test_on_success_callback_called_on_success_async(
    mock_response: httpx.Response, mock_async_request_func: AsyncMock, mock_asleep: Mock
) -> None:
    """Test that on_success callback is called when request succeeds
    (async)."""
    on_success_callback = Mock()

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        on_success=on_success_callback,
    )

    assert response == mock_response
    on_success_callback.assert_called_once()
    call_args = on_success_callback.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "GET"
    assert call_args.attempt == 1
    assert call_args.max_retries == DEFAULT_MAX_RETRIES
    assert call_args.response == mock_response
    assert call_args.total_time >= 0
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_on_success_callback_after_retries_async(
    mock_response: httpx.Response, mock_asleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_success callback is called after successful retry
    (async)."""
    on_success_callback = Mock()

    mock_async_request_func = AsyncMock(
        side_effect=[mock_response_fail, mock_response_fail, mock_response]
    )

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        status_forcelist=(500,),
        on_success=on_success_callback,
    )

    assert response == mock_response
    on_success_callback.assert_called_once()
    call_args = on_success_callback.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "GET"
    assert call_args.attempt == 3  # Succeeded on third attempt
    assert call_args.max_retries == DEFAULT_MAX_RETRIES
    assert call_args.response == mock_response
    assert call_args.total_time >= 0
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
async def test_on_success_callback_not_called_on_failure_async(
    mock_asleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_success callback is not called when request fails
    (async)."""
    on_success_callback = Mock()

    mock_async_request_func = AsyncMock(return_value=mock_response_fail)

    with pytest.raises(
        HttpRequestError,
        match=r"GET request to https://api.example.com/data failed with status 500 after 3 attempts",
    ):
        await request_with_automatic_retry_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_async_request_func,
            status_forcelist=(500,),
            max_retries=2,
            on_success=on_success_callback,
        )

    on_success_callback.assert_not_called()
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


#########################################
#     Tests for on_failure callback     #
#########################################


@pytest.mark.asyncio
async def test_on_failure_callback_called_on_retryable_status_failure_async(
    mock_asleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_failure callback is called when retries are
    exhausted (async)."""
    on_failure_callback = Mock()

    mock_async_request_func = AsyncMock(return_value=mock_response_fail)

    with pytest.raises(HttpRequestError, match=r"GET request to https://api.example.com/data"):
        await request_with_automatic_retry_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_async_request_func,
            status_forcelist=(500,),
            max_retries=2,
            on_failure=on_failure_callback,
        )

    on_failure_callback.assert_called_once()
    call_args = on_failure_callback.call_args[0][0]
    assert call_args.url == TEST_URL
    assert call_args.method == "GET"
    assert call_args.attempt == 3  # max_retries + 1
    assert call_args.max_retries == 2
    assert isinstance(call_args.error, HttpRequestError)
    assert call_args.status_code == 500
    assert call_args.total_time >= 0
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


@pytest.mark.asyncio
async def test_on_failure_callback_not_called_on_success_async(
    mock_response: httpx.Response, mock_async_request_func: AsyncMock, mock_asleep: Mock
) -> None:
    """Test that on_failure callback is not called when request succeeds
    (async)."""
    on_failure_callback = Mock()

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        on_failure=on_failure_callback,
    )

    assert response == mock_response
    on_failure_callback.assert_not_called()
    mock_asleep.assert_not_called()


########################################
#     Tests for multiple callbacks     #
########################################


@pytest.mark.asyncio
async def test_all_callbacks_together_on_success_async(
    mock_response: httpx.Response, mock_asleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that all callbacks work together correctly on successful
    retry (async)."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()

    mock_async_request_func = AsyncMock(side_effect=[mock_response_fail, mock_response])

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        status_forcelist=(500,),
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_success=on_success_callback,
        on_failure=on_failure_callback,
    )

    assert response == mock_response
    assert on_request_callback.call_args_list == [
        call(RequestInfo(url=TEST_URL, method="GET", attempt=1, max_retries=DEFAULT_MAX_RETRIES)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=2, max_retries=DEFAULT_MAX_RETRIES)),
    ]
    on_retry_callback.assert_called_once_with(
        RetryInfo(
            url=TEST_URL,
            method="GET",
            attempt=2,
            max_retries=DEFAULT_MAX_RETRIES,
            wait_time=0.3,
            error=None,
            status_code=500,
        )
    )  # One retry
    on_success_callback.assert_called_once()  # One success
    on_failure_callback.assert_not_called()  # No failure
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
async def test_all_callbacks_together_on_failure_async(
    mock_asleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that all callbacks work together correctly on failure
    (async)."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()

    mock_async_request_func = AsyncMock(return_value=mock_response_fail)

    with pytest.raises(HttpRequestError):
        await request_with_automatic_retry_async(
            url=TEST_URL,
            method="GET",
            request_func=mock_async_request_func,
            status_forcelist=(500,),
            max_retries=2,
            on_request=on_request_callback,
            on_retry=on_retry_callback,
            on_success=on_success_callback,
            on_failure=on_failure_callback,
        )

    assert on_request_callback.call_args_list == [
        call(RequestInfo(url=TEST_URL, method="GET", attempt=1, max_retries=2)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=2, max_retries=2)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=3, max_retries=2)),
    ]
    assert on_retry_callback.call_args_list == [
        call(
            RetryInfo(
                url=TEST_URL,
                method="GET",
                attempt=2,
                max_retries=2,
                wait_time=0.3,
                error=None,
                status_code=500,
            )
        ),
        call(
            RetryInfo(
                url=TEST_URL,
                method="GET",
                attempt=3,
                max_retries=2,
                wait_time=0.6,
                error=None,
                status_code=500,
            )
        ),
    ]
    on_success_callback.assert_not_called()  # No success
    on_failure_callback.assert_called_once()  # One failure
    assert mock_asleep.call_args_list == [call(0.3), call(0.6)]


##############################################
#     Tests with custom retry parameters     #
##############################################


@pytest.mark.asyncio
async def test_callbacks_with_custom_max_retries_async(
    mock_response: httpx.Response, mock_asleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that callbacks receive correct max_retries value (async)."""
    on_request_callback = Mock()
    on_retry_callback = Mock()

    mock_async_request_func = AsyncMock(side_effect=[mock_response_fail, mock_response])

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        status_forcelist=(500,),
        max_retries=5,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
    )

    assert response == mock_response

    # Check that max_retries is correctly passed
    assert on_request_callback.call_args_list == [
        call(RequestInfo(url=TEST_URL, method="GET", attempt=1, max_retries=5)),
        call(RequestInfo(url=TEST_URL, method="GET", attempt=2, max_retries=5)),
    ]
    on_retry_callback.assert_called_once_with(
        RetryInfo(
            url=TEST_URL,
            method="GET",
            attempt=2,
            max_retries=5,
            wait_time=0.3,
            error=None,
            status_code=500,
        )
    )
    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
async def test_callbacks_with_custom_backoff_factor_async(
    mock_response: httpx.Response, mock_asleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that on_retry callback receives correct wait_time with
    custom backoff (async)."""
    on_retry_callback = Mock()

    mock_async_request_func = AsyncMock(side_effect=[mock_response_fail, mock_response])

    response = await request_with_automatic_retry_async(
        url=TEST_URL,
        method="GET",
        request_func=mock_async_request_func,
        status_forcelist=(500,),
        backoff_factor=2.0,
        on_retry=on_retry_callback,
    )

    assert response == mock_response
    on_retry_callback.assert_called_once_with(
        RetryInfo(
            url=TEST_URL,
            method="GET",
            attempt=2,
            max_retries=DEFAULT_MAX_RETRIES,
            wait_time=2.0,
            error=None,
            status_code=500,
        )
    )
    mock_asleep.assert_called_once_with(2.0)
