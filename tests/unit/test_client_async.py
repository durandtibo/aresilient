r"""Unit tests for AsyncResilientClient context manager.

This file contains tests for the asynchronous context manager client.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from aresilient import AsyncResilientClient
from aresilient.core.config import DEFAULT_TIMEOUT, ClientConfig
from tests.helpers import create_mock_response

if TYPE_CHECKING:
    import httpx

TEST_URL = "https://api.example.com/data"


##########################################
#     Tests for AsyncResilientClient     #
##########################################


@pytest.mark.asyncio
async def test_async_client_context_manager_basic(
    mock_asleep: Mock, mock_response: httpx.Response
) -> None:
    """Test that AsyncResilientClient works as an async context
    manager."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            get=AsyncMock(return_value=mock_response), __aenter__=AsyncMock(), __aexit__=AsyncMock()
        )
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.get(TEST_URL)

        assert response.status_code == 200
        mock_client.get.assert_called_once_with(url=TEST_URL)
        mock_client.__aexit__.assert_called_once_with(None, None, None)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_closes_on_exception(mock_asleep: Mock) -> None:
    """Test that AsyncResilientClient closes properly even when
    exception occurs."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(__aenter__=AsyncMock(), __aexit__=AsyncMock())
        mock_client_class.return_value = mock_client
        msg = "test error"

        with pytest.raises(ValueError, match=r"test error"):
            async with AsyncResilientClient():
                raise ValueError(msg)

        mock_client.__aexit__.assert_called_once()

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_multiple_requests(mock_asleep: Mock) -> None:
    """Test that AsyncResilientClient can handle multiple requests."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            get=AsyncMock(return_value=create_mock_response(status_code=200)),
            post=AsyncMock(return_value=create_mock_response(status_code=201)),
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(),
        )
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient(config=ClientConfig(max_retries=5)) as client:
            response1 = await client.get("https://api.example.com/data1")
            response2 = await client.post("https://api.example.com/data2", json={"key": "value"})

        assert response1.status_code == 200
        assert response2.status_code == 201
        mock_client.get.assert_called_once_with(url="https://api.example.com/data1")
        mock_client.post.assert_called_once_with(
            url="https://api.example.com/data2", json={"key": "value"}
        )
        mock_client.__aexit__.assert_called_once_with(None, None, None)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_uses_custom_client(
    mock_asleep: Mock, mock_response: httpx.Response
) -> None:
    """Test that AsyncResilientClient enters and exits a provided httpx.AsyncClient (Scenario 2)."""
    mock_client = Mock(
        get=AsyncMock(return_value=mock_response), __aenter__=AsyncMock(), __aexit__=AsyncMock()
    )

    async with AsyncResilientClient(client=mock_client) as client:
        response = await client.get(TEST_URL)

    assert response.status_code == 200
    mock_client.get.assert_called_once_with(url=TEST_URL)
    mock_client.__aexit__.assert_called_once_with(None, None, None)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_scenario1_externally_managed_client(
    mock_asleep: Mock, mock_response: httpx.Response
) -> None:
    """Test Scenario 1: client whose lifecycle is managed by an outer async context manager.

    When the provided httpx.AsyncClient is already open (its __aenter__ raises RuntimeError
    and is_closed returns False), AsyncResilientClient uses it without managing its lifecycle.
    """
    mock_client = Mock(
        get=AsyncMock(return_value=mock_response),
        __aenter__=AsyncMock(
            side_effect=RuntimeError("Cannot open a client instance more than once.")
        ),
        __aexit__=AsyncMock(),
        is_closed=False,
    )

    async with AsyncResilientClient(client=mock_client) as client:
        response = await client.get(TEST_URL)

    assert response.status_code == 200
    mock_client.get.assert_called_once_with(url=TEST_URL)
    mock_client.__aexit__.assert_not_called()
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_get_method(mock_asleep: Mock, mock_response: httpx.Response) -> None:
    """Test client.get() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            get=AsyncMock(return_value=mock_response), __aenter__=AsyncMock(), __aexit__=AsyncMock()
        )
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.get(TEST_URL, params={"page": 1})

        assert response.status_code == 200
        mock_client.get.assert_called_once_with(url=TEST_URL, params={"page": 1})

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_post_method(mock_asleep: Mock) -> None:
    """Test client.post() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            post=AsyncMock(return_value=create_mock_response(status_code=201)),
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(),
        )
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.post(TEST_URL, json={"key": "value"})

        assert response.status_code == 201
        mock_client.post.assert_called_once_with(url=TEST_URL, json={"key": "value"})

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_put_method(mock_asleep: Mock, mock_response: httpx.Response) -> None:
    """Test client.put() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            put=AsyncMock(return_value=mock_response), __aenter__=AsyncMock(), __aexit__=AsyncMock()
        )
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.put(TEST_URL, json={"key": "value"})

        assert response.status_code == 200
        mock_client.put.assert_called_once_with(url=TEST_URL, json={"key": "value"})

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_delete_method(mock_asleep: Mock) -> None:
    """Test client.delete() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            delete=AsyncMock(return_value=create_mock_response(status_code=204)),
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(),
        )
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.delete(TEST_URL)

        assert response.status_code == 204
        mock_client.delete.assert_called_once_with(url=TEST_URL)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_patch_method(mock_asleep: Mock, mock_response: httpx.Response) -> None:
    """Test client.patch() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            patch=AsyncMock(return_value=mock_response),
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(),
        )
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.patch(TEST_URL, json={"key": "value"})

        assert response.status_code == 200
        mock_client.patch.assert_called_once_with(url=TEST_URL, json={"key": "value"})

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_head_method(mock_asleep: Mock, mock_response: httpx.Response) -> None:
    """Test client.head() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            head=AsyncMock(return_value=mock_response),
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(),
        )
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.head(TEST_URL)

        assert response.status_code == 200
        mock_client.head.assert_called_once_with(url=TEST_URL)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_options_method(
    mock_asleep: Mock, mock_response: httpx.Response
) -> None:
    """Test client.options() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            options=AsyncMock(return_value=mock_response),
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(),
        )
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.options(TEST_URL)

        assert response.status_code == 200
        mock_client.options.assert_called_once_with(url=TEST_URL)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_request_method(
    mock_asleep: Mock, mock_response: httpx.Response
) -> None:
    """Test client.request() method with custom HTTP method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            trace=AsyncMock(return_value=mock_response),
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(),
        )
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.request(method="TRACE", url=TEST_URL)

        assert response.status_code == 200

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_default_max_retries(
    mock_asleep: Mock, mock_response: httpx.Response, mock_response_fail: httpx.Response
) -> None:
    """Test that client's default max_retries is used when not
    overridden."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            get=AsyncMock(side_effect=[mock_response_fail, mock_response]),
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(),
        )
        mock_client_class.return_value = mock_client

        # Client configured with max_retries=2
        async with AsyncResilientClient(config=ClientConfig(max_retries=2)) as client:
            response = await client.get(TEST_URL)

        # Should have retried using client's default
        assert response.status_code == 200
        assert mock_client.get.call_args_list == [call(url=TEST_URL), call(url=TEST_URL)]

    mock_asleep.assert_called_once_with(0.3)


@pytest.mark.asyncio
async def test_async_client_validation_max_retries_negative(mock_asleep: Mock) -> None:
    """Test that client validates max_retries parameter must be >= 0."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0, got -1"):
        AsyncResilientClient(config=ClientConfig(max_retries=-1))
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_default_timeout(mock_asleep: Mock) -> None:
    """Test that AsyncResilientClient creates a default client with
    DEFAULT_TIMEOUT."""
    with patch("httpx.AsyncClient") as mock_client_class:
        AsyncResilientClient()

        mock_client_class.assert_called_once_with(timeout=DEFAULT_TIMEOUT)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_shares_configuration_across_requests(
    mock_asleep: Mock, mock_response: httpx.Response
) -> None:
    """Test that all requests share the same configuration."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock(
            get=AsyncMock(return_value=mock_response),
            post=AsyncMock(return_value=mock_response),
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(),
        )
        mock_client_class.return_value = mock_client

        # Create client with specific configuration
        async with AsyncResilientClient(
            config=ClientConfig(max_retries=5, jitter_factor=0.5)
        ) as client:
            await client.get(TEST_URL)
            await client.post(TEST_URL)

        # Both requests should use the same client
        mock_client.get.assert_called_once_with(url=TEST_URL)
        mock_client.post.assert_called_once_with(url=TEST_URL)

    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_async_client_exit_without_enter() -> None:
    """Test that __aexit__ can be called without __aenter__.

    This tests that calling __aexit__ before entering the context
    manager does not raise an error. Since the client was never entered,
    its lifecycle is not managed and __aexit__ is not delegated to it.
    """
    with patch("httpx.AsyncClient") as mock_client_class:
        client = AsyncResilientClient()

        # Manually trigger __aexit__ without calling __aenter__
        await client.__aexit__(None, None, None)

        # Since __aenter__ was never called, _owns_client is False and
        # the underlying client's __aexit__ should not be called.
        mock_client_class.return_value.__aexit__.assert_not_called()
        assert client._owns_client is False
