from __future__ import annotations

import httpx
import pytest

from aresnet import delete_with_automatic_retry_async

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#######################################################
#     Tests for delete_with_automatic_retry_async     #
#######################################################


@pytest.mark.asyncio
async def test_delete_with_automatic_retry_async_successful_request() -> None:
    """Test successful DELETE request without retries."""
    async with httpx.AsyncClient() as client:
        response = await delete_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/delete", client=client
        )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["url"] == "https://httpbin.org/delete"


@pytest.mark.asyncio
async def test_delete_with_automatic_retry_async_successful_request_without_client() -> None:
    """Test successful DELETE request without retries."""
    response = await delete_with_automatic_retry_async(url=f"{HTTPBIN_URL}/delete")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["url"] == "https://httpbin.org/delete"


@pytest.mark.asyncio
async def test_delete_with_non_retryable_status_fails_immediately_async() -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPStatusError, match=r"Client error '404 NOT FOUND'"):
            await delete_with_automatic_retry_async(url=f"{HTTPBIN_URL}/status/404", client=client)


@pytest.mark.asyncio
async def test_delete_with_automatic_retry_async_with_headers() -> None:
    """Test DELETE request with custom headers."""
    async with httpx.AsyncClient() as client:
        response = await delete_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/delete",
            client=client,
            headers={"X-Custom-Header": "test-value"},
        )

    assert response.status_code == 200
    response_data = response.json()
    assert "X-Custom-Header" in response_data["headers"]
    assert response_data["headers"]["X-Custom-Header"] == "test-value"


@pytest.mark.asyncio
async def test_delete_with_automatic_retry_async_with_query_params() -> None:
    """Test DELETE request with query parameters."""
    async with httpx.AsyncClient() as client:
        response = await delete_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/delete",
            client=client,
            params={"key1": "value1", "key2": "value2"},
        )

    assert response.status_code == 200
    response_data = response.json()
    assert "key1=value1" in response_data["url"]
    assert "key2=value2" in response_data["url"]


@pytest.mark.asyncio
async def test_delete_with_automatic_retry_async_with_auth_headers() -> None:
    """Test DELETE request with authorization headers."""
    async with httpx.AsyncClient() as client:
        response = await delete_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/delete",
            client=client,
            headers={"Authorization": "Bearer test-token-123"},
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["headers"]["Authorization"] == "Bearer test-token-123"


@pytest.mark.asyncio
async def test_delete_with_automatic_retry_async_multiple_headers() -> None:
    """Test DELETE request with multiple custom headers."""
    async with httpx.AsyncClient() as client:
        response = await delete_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/delete",
            client=client,
            headers={
                "X-Custom-Header-1": "value-1",
                "X-Custom-Header-2": "value-2",
                "X-Correlation-ID": "xyz-789",
            },
        )

    assert response.status_code == 200
    response_data = response.json()
    # httpbin normalizes header names to title case
    assert response_data["headers"]["X-Custom-Header-1"] == "value-1"
    assert response_data["headers"]["X-Custom-Header-2"] == "value-2"
    assert response_data["headers"]["X-Correlation-Id"] == "xyz-789"
