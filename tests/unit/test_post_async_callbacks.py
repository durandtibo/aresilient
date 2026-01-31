r"""Unit tests for callback functionality in async HTTP method wrappers (POST)."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from aresilient import HttpRequestError, post_with_automatic_retry_async

TEST_URL = "https://api.example.com/data"


@pytest.fixture
def mock_response() -> httpx.Response:
    return Mock(spec=httpx.Response, status_code=201)


@pytest.fixture
def mock_async_client(mock_response: httpx.Response) -> httpx.AsyncClient:
    return Mock(spec=httpx.AsyncClient, post=AsyncMock(return_value=mock_response))


##################################################
#     Tests for post_with_automatic_retry_async  #
#     with callback functionality                #
##################################################


@pytest.mark.asyncio
async def test_post_async_on_request_callback(
    mock_async_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that on_request callback is called for async POST requests."""
    on_request_callback = Mock()

    response = await post_with_automatic_retry_async(
        TEST_URL, client=mock_async_client, on_request=on_request_callback
    )

    assert response.status_code == 201
    on_request_callback.assert_called_once()
    call_args = on_request_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "POST"
    assert call_args["attempt"] == 1


@pytest.mark.asyncio
async def test_post_async_on_success_callback(
    mock_async_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that on_success callback is called for successful async POST requests."""
    on_success_callback = Mock()

    response = await post_with_automatic_retry_async(
        TEST_URL, client=mock_async_client, on_success=on_success_callback
    )

    assert response.status_code == 201
    on_success_callback.assert_called_once()
    call_args = on_success_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "POST"
    assert call_args["response"].status_code == 201


@pytest.mark.asyncio
async def test_post_async_on_retry_callback(
    mock_response: httpx.Response, mock_asleep: Mock
) -> None:
    """Test that on_retry callback is called when async POST request is retried."""
    on_retry_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_async_client = Mock(
        spec=httpx.AsyncClient,
        post=AsyncMock(side_effect=[mock_fail_response, mock_response]),
    )

    response = await post_with_automatic_retry_async(
        TEST_URL, client=mock_async_client, on_retry=on_retry_callback
    )

    assert response.status_code == 201
    on_retry_callback.assert_called_once()
    call_args = on_retry_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "POST"
    assert call_args["status_code"] == 503


@pytest.mark.asyncio
async def test_post_async_on_failure_callback(mock_asleep: Mock) -> None:
    """Test that on_failure callback is called when async POST retries are exhausted."""
    on_failure_callback = Mock()
    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_async_client = Mock(
        spec=httpx.AsyncClient, post=AsyncMock(return_value=mock_fail_response)
    )

    with pytest.raises(HttpRequestError):
        await post_with_automatic_retry_async(
            TEST_URL,
            client=mock_async_client,
            max_retries=2,
            on_failure=on_failure_callback,
        )

    on_failure_callback.assert_called_once()
    call_args = on_failure_callback.call_args[0][0]
    assert call_args["url"] == TEST_URL
    assert call_args["method"] == "POST"
    assert call_args["status_code"] == 503


@pytest.mark.asyncio
async def test_post_async_all_callbacks_together(
    mock_response: httpx.Response, mock_asleep: Mock
) -> None:
    """Test that all callbacks work together for async POST requests."""
    on_request_callback = Mock()
    on_retry_callback = Mock()
    on_success_callback = Mock()
    on_failure_callback = Mock()

    mock_fail_response = Mock(spec=httpx.Response, status_code=503)
    mock_async_client = Mock(
        spec=httpx.AsyncClient,
        post=AsyncMock(side_effect=[mock_fail_response, mock_response]),
    )

    response = await post_with_automatic_retry_async(
        TEST_URL,
        client=mock_async_client,
        on_request=on_request_callback,
        on_retry=on_retry_callback,
        on_success=on_success_callback,
        on_failure=on_failure_callback,
    )

    assert response.status_code == 201
    assert on_request_callback.call_count == 2  # Two attempts
    on_retry_callback.assert_called_once()  # One retry
    on_success_callback.assert_called_once()  # One success
    on_failure_callback.assert_not_called()  # No failure


@pytest.mark.asyncio
async def test_post_async_callbacks_with_json_data(
    mock_async_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test that callbacks work when async POST has JSON data."""
    on_request_callback = Mock()
    on_success_callback = Mock()

    response = await post_with_automatic_retry_async(
        TEST_URL,
        json={"key": "value"},
        client=mock_async_client,
        on_request=on_request_callback,
        on_success=on_success_callback,
    )

    assert response.status_code == 201
    on_request_callback.assert_called_once()
    on_success_callback.assert_called_once()
