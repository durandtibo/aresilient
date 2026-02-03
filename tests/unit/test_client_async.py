r"""Unit tests for AsyncResilientClient context manager.

This file contains tests for the asynchronous context manager client.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from aresilient import AsyncResilientClient, HttpRequestError

if TYPE_CHECKING:
    from unittest.mock import Mock

TEST_URL = "https://api.example.com/data"


##############################################
#     Tests for AsyncResilientClient         #
##############################################


@pytest.mark.asyncio
async def test_async_client_context_manager_basic(mock_asleep: Mock) -> None:
    """Test that AsyncResilientClient works as an async context manager."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.get(TEST_URL)

        assert response.status_code == 200
        mock_client.get.assert_called_once()
        mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_async_client_closes_on_exception(mock_asleep: Mock) -> None:
    """Test that AsyncResilientClient closes properly even when exception occurs."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        with pytest.raises(ValueError, match="test error"):
            async with AsyncResilientClient() as client:
                raise ValueError("test error")

        mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_async_client_outside_context_manager_raises(mock_asleep: Mock) -> None:
    """Test that using client outside context manager raises RuntimeError."""
    client = AsyncResilientClient()

    with pytest.raises(RuntimeError, match="must be used within an async context manager"):
        await client.get(TEST_URL)


@pytest.mark.asyncio
async def test_async_client_multiple_requests(mock_asleep: Mock) -> None:
    """Test that AsyncResilientClient can handle multiple requests."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response1 = Mock(spec=httpx.Response)
        mock_response1.status_code = 200
        mock_response2 = Mock(spec=httpx.Response)
        mock_response2.status_code = 201
        mock_client.get = AsyncMock(return_value=mock_response1)
        mock_client.post = AsyncMock(return_value=mock_response2)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient(max_retries=5) as client:
            response1 = await client.get("https://api.example.com/data1")
            response2 = await client.post("https://api.example.com/data2", json={"key": "value"})

        assert response1.status_code == 200
        assert response2.status_code == 201
        mock_client.get.assert_called_once()
        mock_client.post.assert_called_once()
        mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_async_client_uses_configured_timeout(mock_asleep: Mock) -> None:
    """Test that AsyncResilientClient uses configured timeout."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient(timeout=30.0):
            pass

        mock_client_class.assert_called_once_with(timeout=30.0)


@pytest.mark.asyncio
async def test_async_client_get_method(mock_asleep: Mock) -> None:
    """Test client.get() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.get(TEST_URL, params={"page": 1})

        assert response.status_code == 200
        # Verify that params were passed through
        call_kwargs = mock_client.get.call_args[1]
        assert "params" in call_kwargs
        assert call_kwargs["params"] == {"page": 1}


@pytest.mark.asyncio
async def test_async_client_post_method(mock_asleep: Mock) -> None:
    """Test client.post() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.post(TEST_URL, json={"key": "value"})

        assert response.status_code == 201
        call_kwargs = mock_client.post.call_args[1]
        assert "json" in call_kwargs


@pytest.mark.asyncio
async def test_async_client_put_method(mock_asleep: Mock) -> None:
    """Test client.put() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.put(TEST_URL, json={"key": "value"})

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_async_client_delete_method(mock_asleep: Mock) -> None:
    """Test client.delete() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 204
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.delete(TEST_URL)

        assert response.status_code == 204


@pytest.mark.asyncio
async def test_async_client_patch_method(mock_asleep: Mock) -> None:
    """Test client.patch() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_client.patch = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.patch(TEST_URL, json={"key": "value"})

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_async_client_head_method(mock_asleep: Mock) -> None:
    """Test client.head() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.head(TEST_URL)

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_async_client_options_method(mock_asleep: Mock) -> None:
    """Test client.options() method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_client.options = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.options(TEST_URL)

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_async_client_request_method(mock_asleep: Mock) -> None:
    """Test client.request() method with custom HTTP method."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_client.trace = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        async with AsyncResilientClient() as client:
            response = await client.request("TRACE", TEST_URL)

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_async_client_override_max_retries(mock_asleep: Mock) -> None:
    """Test that per-request max_retries override works."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        # Simulate retryable error then success
        mock_response_error = Mock(spec=httpx.Response)
        mock_response_error.status_code = 503
        mock_response_success = Mock(spec=httpx.Response)
        mock_response_success.status_code = 200
        mock_client.get = AsyncMock(side_effect=[mock_response_error, mock_response_success])
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        # Client configured with max_retries=0, but we override it for this request
        async with AsyncResilientClient(max_retries=0) as client:
            response = await client.get(TEST_URL, max_retries=2)

        # Should have retried because we overrode max_retries
        assert response.status_code == 200
        assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_async_client_default_max_retries(mock_asleep: Mock) -> None:
    """Test that client's default max_retries is used when not overridden."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        # Simulate retryable error then success
        mock_response_error = Mock(spec=httpx.Response)
        mock_response_error.status_code = 503
        mock_response_success = Mock(spec=httpx.Response)
        mock_response_success.status_code = 200
        mock_client.get = AsyncMock(side_effect=[mock_response_error, mock_response_success])
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        # Client configured with max_retries=2
        async with AsyncResilientClient(max_retries=2) as client:
            response = await client.get(TEST_URL)

        # Should have retried using client's default
        assert response.status_code == 200
        assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_async_client_validation_errors(mock_asleep: Mock) -> None:
    """Test that client validates parameters on initialization."""
    with pytest.raises(ValueError, match="max_retries"):
        AsyncResilientClient(max_retries=-1)

    with pytest.raises(ValueError, match="timeout"):
        AsyncResilientClient(timeout=0)

    with pytest.raises(ValueError, match="backoff_factor"):
        AsyncResilientClient(backoff_factor=-0.5)


@pytest.mark.asyncio
async def test_async_client_shares_configuration_across_requests(mock_asleep: Mock) -> None:
    """Test that all requests share the same configuration."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client

        # Create client with specific configuration
        async with AsyncResilientClient(max_retries=5, jitter_factor=0.5) as client:
            await client.get(TEST_URL)
            await client.post(TEST_URL)

        # Both requests should use the same client
        assert mock_client.get.call_count == 1
        assert mock_client.post.call_count == 1
