from __future__ import annotations

import httpx
import pytest

from aresnet import HttpRequestError, patch_with_automatic_retry_async

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


###################################################
#     Tests for patch_with_automatic_retry_async     #
###################################################


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_successful_request() -> None:
    """Test successful PATCH request without retries."""
    async with httpx.AsyncClient() as client:
        response = await patch_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/patch", json={"test": "data", "number": 42}, client=client
        )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["url"] == "https://httpbin.org/patch"
    assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_successful_request_without_client() -> None:
    """Test successful PATCH request without retries."""
    response = await patch_with_automatic_retry_async(
        url=f"{HTTPBIN_URL}/patch", json={"test": "data", "number": 42}
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.asyncio
async def test_patch_with_non_retryable_status_fails_immediately_async() -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    async with httpx.AsyncClient() as client:
        with pytest.raises(HttpRequestError, match=r"PATCH request to .* failed with status 404"):
            await patch_with_automatic_retry_async(url=f"{HTTPBIN_URL}/status/404", client=client)


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_large_request_body() -> None:
    """Test PATCH request with large JSON payload."""
    large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(100)]}

    async with httpx.AsyncClient() as client:
        response = await patch_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/patch", json=large_data, client=client
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["json"]["items"][0]["id"] == 0
    assert len(response_data["json"]["items"]) == 100


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_form_data() -> None:
    """Test PATCH request with form data."""
    async with httpx.AsyncClient() as client:
        response = await patch_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/patch", data={"field1": "value1", "field2": "value2"}, client=client
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["form"] == {"field1": "value1", "field2": "value2"}


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_with_headers() -> None:
    """Test PATCH request with custom headers."""
    async with httpx.AsyncClient() as client:
        response = await patch_with_automatic_retry_async(
            url=f"{HTTPBIN_URL}/patch",
            client=client,
            json={"test": "data"},
            headers={"X-Custom-Header": "test-value"},
        )

    assert response.status_code == 200
    response_data = response.json()
    assert "X-Custom-Header" in response_data["headers"]
    assert response_data["headers"]["X-Custom-Header"] == "test-value"
