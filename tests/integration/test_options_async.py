from __future__ import annotations

import asyncio

import httpx
import pytest

from aresilient import HttpRequestError, options_with_automatic_retry_async

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#####################################################
#     Tests for options_with_automatic_retry_async     #
#####################################################


@pytest.mark.asyncio
async def test_options_with_automatic_retry_async_successful_request() -> None:
    """Test successful async OPTIONS request without retries."""
    async with httpx.AsyncClient() as client:
        response = await options_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/get", client=client
        )
    # httpbin may return 200 or 405 for OPTIONS depending on endpoint
    assert response.status_code in (200, 405)


@pytest.mark.asyncio
async def test_options_with_automatic_retry_async_successful_request_without_client() -> None:
    """Test successful async OPTIONS request without client."""
    response = await options_with_automatic_retry_async(url=f"{HTTPBIN_URL}/get")
    assert response.status_code in (200, 405)


@pytest.mark.asyncio
async def test_options_with_non_retryable_status_fails_immediately_async() -> None:
    """Test that 404 (non-retryable) fails immediately without retries."""
    async with httpx.AsyncClient() as client:
        with pytest.raises(
            HttpRequestError, match=r"OPTIONS request to .* failed with status 404"
        ):
            await options_with_automatic_retry_async(
                url=f"{HTTPBIN_URL}/status/404", client=client
            )


@pytest.mark.asyncio
async def test_options_with_automatic_retry_async_with_headers() -> None:
    """Test async OPTIONS request with custom headers."""
    async with httpx.AsyncClient() as client:
        response = await options_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/headers",
            client=client,
            headers={"X-Custom-Header": "test-value", "Origin": "https://example.com"},
        )

    # httpbin may not support OPTIONS on all endpoints
    assert response.status_code in (200, 405)


@pytest.mark.asyncio
async def test_options_with_automatic_retry_async_concurrent_requests() -> None:
    """Test multiple concurrent async OPTIONS requests."""
    async with httpx.AsyncClient() as client:
        # Create multiple concurrent OPTIONS requests
        urls = [
            f"{HTTPBIN_URL}/get",
            f"{HTTPBIN_URL}/headers",
            f"{HTTPBIN_URL}/post",
        ]
        tasks = [options_with_automatic_retry_async(url, client=client) for url in urls]
        responses = await asyncio.gather(*tasks)

    # All requests should succeed (200 or 405 depending on httpbin support)
    assert all(r.status_code in (200, 405) for r in responses)
