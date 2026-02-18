from __future__ import annotations

import asyncio

import httpx
import pytest

from aresilient import options_async

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#####################################################
#     Tests for options_async     #
#####################################################
# Note: Common async tests (successful request, headers)
# are now in test_core_async.py to avoid duplication across HTTP methods.
# This file contains OPTIONS-specific async tests only.


@pytest.mark.asyncio
async def test_options_async_concurrent_requests() -> None:
    """Test multiple concurrent async OPTIONS requests."""
    async with httpx.AsyncClient() as client:
        # Create multiple concurrent OPTIONS requests
        urls = [
            f"{HTTPBIN_URL}/get",
            f"{HTTPBIN_URL}/headers",
            f"{HTTPBIN_URL}/post",
        ]
        tasks = [options_async(url, client=client) for url in urls]
        responses = await asyncio.gather(*tasks)

    # All requests should succeed (200 or 405 depending on httpbin support)
    assert all(r.status_code in (200, 405) for r in responses)


@pytest.mark.asyncio
async def test_options_async_with_custom_headers() -> None:
    """Test async OPTIONS request with custom headers."""
    async with httpx.AsyncClient() as client:
        response = await options_async(
            url=f"{HTTPBIN_URL}/get",
            client=client,
            headers={"X-Custom-Header": "test-value"},
        )

    # OPTIONS may return 405 on httpbin
    assert response.status_code in (200, 405)


@pytest.mark.asyncio
async def test_options_async_successful_request_with_client() -> None:
    """Test successful async OPTIONS request with explicit client."""
    async with httpx.AsyncClient() as client:
        response = await options_async(url=f"{HTTPBIN_URL}/get", client=client)

    # OPTIONS may return 405 on httpbin
    assert response.status_code in (200, 405)


@pytest.mark.asyncio
async def test_options_async_successful_request_without_client() -> None:
    """Test successful async OPTIONS request without explicit client."""
    response = await options_async(url=f"{HTTPBIN_URL}/get")

    # OPTIONS may return 405 on httpbin
    assert response.status_code in (200, 405)
