from __future__ import annotations

import httpx
import pytest

from aresilient import get_async

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


####################################################
#     Tests for get_async     #
####################################################
# Note: Common async tests (successful request, non-retryable status, headers, query params)
# are now in test_core_async.py to avoid duplication across HTTP methods.
# This file contains GET-specific async tests only.


@pytest.mark.asyncio
async def test_get_async_redirect_chain() -> None:
    """Test GET request that follows a redirect chain."""
    # httpbin.org supports redirects: /redirect/n redirects n times
    # Create a client with follow_redirects=True to handle the redirect chain
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await get_async(url=f"{HTTPBIN_URL}/redirect/3", client=client)

    assert response.status_code == 200
    # After redirects, we should end up at /get
    response_data = response.json()
    assert "url" in response_data


@pytest.mark.asyncio
async def test_get_async_large_response() -> None:
    """Test GET request with large response body."""
    # Request a large amount of bytes (10KB)
    async with httpx.AsyncClient() as client:
        response = await get_async(url=f"{HTTPBIN_URL}/bytes/10240", client=client)

    assert response.status_code == 200
    assert len(response.content) == 10240


@pytest.mark.asyncio
async def test_get_async_with_custom_headers() -> None:
    """Test async GET request with custom headers."""
    async with httpx.AsyncClient() as client:
        response = await get_async(
            url=f"{HTTPBIN_URL}/headers",
            client=client,
            headers={"X-Custom-Header": "test-value"},
        )

    assert response.status_code == 200

    # Verify headers in response
    response_data = response.json()
    assert "headers" in response_data
    assert "X-Custom-Header" in response_data["headers"]
    assert response_data["headers"]["X-Custom-Header"] == "test-value"
