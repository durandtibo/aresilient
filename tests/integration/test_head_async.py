from __future__ import annotations

import asyncio

import httpx
import pytest

from aresilient import head_with_automatic_retry_async

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


###################################################
#     Tests for head_with_automatic_retry_async     #
###################################################
# Note: Common async tests (successful request, non-retryable status, headers)
# are now in test_core_async.py to avoid duplication across HTTP methods.
# This file contains HEAD-specific async tests only.


@pytest.mark.asyncio
async def test_head_with_automatic_retry_async_check_content_length() -> None:
    """Test async HEAD request to check Content-Length header."""
    async with httpx.AsyncClient() as client:
        # Request a specific number of bytes to check Content-Length
        response = await head_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/bytes/1024", client=client
        )

    assert response.status_code == 200
    # HEAD should return Content-Length header
    assert "Content-Length" in response.headers
    assert response.headers["Content-Length"] == "1024"
    # But no actual content
    assert len(response.content) == 0


@pytest.mark.asyncio
async def test_head_with_automatic_retry_async_concurrent_requests() -> None:
    """Test multiple concurrent async HEAD requests."""
    async with httpx.AsyncClient() as client:
        # Create multiple concurrent HEAD requests
        urls = [
            f"{HTTPBIN_URL}/get",
            f"{HTTPBIN_URL}/bytes/1024",
            f"{HTTPBIN_URL}/headers",
        ]
        tasks = [head_with_automatic_retry_async(url, client=client) for url in urls]
        responses = await asyncio.gather(*tasks)

    # All requests should succeed
    assert all(r.status_code == 200 for r in responses)
    # All should have no content (HEAD requests)
    assert all(len(r.content) == 0 for r in responses)


@pytest.mark.asyncio
async def test_head_with_automatic_retry_async_with_custom_headers() -> None:
    """Test async HEAD request with custom headers."""
    async with httpx.AsyncClient() as client:
        response = await head_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/headers",
            client=client,
            headers={"X-Custom-Header": "test-value"},
        )

    assert response.status_code == 200
    # HEAD request should succeed but have no body
    assert len(response.content) == 0


@pytest.mark.asyncio
async def test_head_with_automatic_retry_async_successful_request_with_client() -> None:
    """Test successful async HEAD request with explicit client."""
    async with httpx.AsyncClient() as client:
        response = await head_with_automatic_retry_async(url=f"{HTTPBIN_URL}/get", client=client)

    assert response.status_code == 200
    # HEAD has no body
    assert len(response.content) == 0


@pytest.mark.asyncio
async def test_head_with_automatic_retry_async_successful_request_without_client() -> None:
    """Test successful async HEAD request without explicit client."""
    response = await head_with_automatic_retry_async(url=f"{HTTPBIN_URL}/get")

    assert response.status_code == 200
    # HEAD has no body
    assert len(response.content) == 0
