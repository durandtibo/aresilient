from __future__ import annotations

import asyncio

import httpx
import pytest

from aresilient import HttpRequestError, head_with_automatic_retry_async

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


###################################################
#     Tests for head_with_automatic_retry_async     #
###################################################


@pytest.mark.asyncio
async def test_head_with_automatic_retry_async_successful_request() -> None:
    """Test successful async HEAD request without retries."""
    async with httpx.AsyncClient() as client:
        response = await head_with_automatic_retry_async(url=f"{HTTPBIN_URL}/get", client=client)
    assert response.status_code == 200
    # HEAD requests should not have a body
    assert len(response.content) == 0
    # But should have headers
    assert "Content-Type" in response.headers


@pytest.mark.asyncio
async def test_head_with_automatic_retry_async_successful_request_without_client() -> None:
    """Test successful async HEAD request without client."""
    response = await head_with_automatic_retry_async(url=f"{HTTPBIN_URL}/get")
    assert response.status_code == 200
    assert len(response.content) == 0


@pytest.mark.asyncio
async def test_head_with_non_retryable_status_fails_immediately_async() -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    async with httpx.AsyncClient() as client:
        with pytest.raises(HttpRequestError, match=r"HEAD request to .* failed with status 404"):
            await head_with_automatic_retry_async(url=f"{HTTPBIN_URL}/status/404", client=client)


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
async def test_head_with_automatic_retry_async_with_headers() -> None:
    """Test async HEAD request with custom headers."""
    async with httpx.AsyncClient() as client:
        response = await head_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/headers",
            client=client,
            headers={"X-Custom-Header": "test-value", "User-Agent": "aresilient-test"},
        )

    assert response.status_code == 200
    # HEAD request should succeed but have no body
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
