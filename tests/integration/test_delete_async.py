from __future__ import annotations

import httpx
import pytest

from aresilient import delete_with_automatic_retry_async

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#######################################################
#     Tests for delete_with_automatic_retry_async     #
#######################################################
# Note: Common async tests (successful request, non-retryable status, headers, query params)
# are now in test_core_async.py to avoid duplication across HTTP methods.
# This file contains DELETE-specific async tests only.


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
