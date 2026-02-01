from __future__ import annotations

import asyncio

import httpx
import pytest

from aresilient import options_with_automatic_retry_async

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#####################################################
#     Tests for options_with_automatic_retry_async     #
#####################################################
# Note: Common async tests (successful request, headers)
# are now in test_http_methods_common_async.py to avoid duplication across HTTP methods.
# This file contains OPTIONS-specific async tests only.


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
