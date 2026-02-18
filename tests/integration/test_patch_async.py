from __future__ import annotations

import httpx
import pytest

from aresilient import patch_async

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


######################################################
#     Tests for patch_async     #
######################################################
# Note: Common async tests (successful request, non-retryable status, headers)
# are now in test_core_async.py to avoid duplication across HTTP methods.
# This file contains PATCH-specific async tests only.


@pytest.mark.asyncio
async def test_patch_async_large_request_body() -> None:
    """Test PATCH request with large JSON payload."""
    large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(100)]}

    async with httpx.AsyncClient() as client:
        response = await patch_async(url=f"{HTTPBIN_URL}/patch", json=large_data, client=client)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["json"]["items"][0]["id"] == 0
    assert len(response_data["json"]["items"]) == 100


@pytest.mark.asyncio
async def test_patch_async_form_data() -> None:
    """Test PATCH request with form data."""
    async with httpx.AsyncClient() as client:
        response = await patch_async(
            url=f"{HTTPBIN_URL}/patch", data={"field1": "value1", "field2": "value2"}, client=client
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["form"] == {"field1": "value1", "field2": "value2"}
