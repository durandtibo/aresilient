from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from aresilient import HttpRequestError
from tests.helpers import HTTP_METHODS_ASYNC, HTTPBIN_URL

if TYPE_CHECKING:
    from _pytest.mark.structures import ParameterSet


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_http_method_async_successful_request_with_client(test_case: ParameterSet) -> None:
    """Test successful async HTTP request with explicit client."""
    tc = test_case.values[0]
    async with httpx.AsyncClient() as client:
        if tc.supports_body:
            response = await tc.method_func(
                url=tc.test_url,
                json={"test": "data", "number": 42},
                client=client,
            )
        else:
            response = await tc.method_func(url=tc.test_url, client=client)

    assert response.status_code == 200 or (
        tc.method_name == "OPTIONS" and response.status_code == 405
    )

    # Verify response data (except for HEAD and OPTIONS which have no body)
    if tc.method_name not in ("HEAD", "OPTIONS"):
        response_data = response.json()
        assert tc.test_url in response_data["url"]
        if tc.supports_body:
            assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_http_method_async_successful_request_without_client(test_case: ParameterSet) -> None:
    """Test successful async HTTP request without explicit client."""
    tc = test_case.values[0]
    if tc.supports_body:
        response = await tc.method_func(
            url=tc.test_url,
            json={"test": "data", "number": 42},
        )
    else:
        response = await tc.method_func(url=tc.test_url)

    assert response.status_code == 200 or (
        tc.method_name == "OPTIONS" and response.status_code == 405
    )

    # Verify response data (except for HEAD and OPTIONS which have no body)
    if tc.method_name not in ("HEAD", "OPTIONS"):
        response_data = response.json()
        if tc.supports_body:
            assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].method_name != "OPTIONS"],
)
async def test_http_method_async_non_retryable_status_fails_immediately(
    test_case: ParameterSet,
) -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    tc = test_case.values[0]
    async with httpx.AsyncClient() as client:
        with pytest.raises(
            HttpRequestError, match=rf"{tc.method_name} request to .* failed with status 404"
        ):
            await tc.method_func(url=f"{HTTPBIN_URL}/status/404", client=client)


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_http_method_async_with_custom_headers(test_case: ParameterSet) -> None:
    """Test async HTTP request with custom headers."""
    tc = test_case.values[0]
    async with httpx.AsyncClient() as client:
        if tc.supports_body:
            response = await tc.method_func(
                url=tc.test_url,
                client=client,
                json={"test": "data"},
                headers={"X-Custom-Header": "test-value"},
            )
        else:
            # Use /headers endpoint for methods that don't support body
            test_endpoint = f"{HTTPBIN_URL}/headers" if tc.method_name != "OPTIONS" else tc.test_url
            response = await tc.method_func(
                url=test_endpoint,
                client=client,
                headers={"X-Custom-Header": "test-value"},
            )

    assert response.status_code == 200 or (
        tc.method_name == "OPTIONS" and response.status_code == 405
    )

    # Verify headers in response (except for HEAD which has no body)
    if tc.method_name == "HEAD":
        # HEAD request should succeed but have no body
        assert len(response.content) == 0
    elif tc.method_name != "OPTIONS":
        # For OPTIONS, httpbin might not return the headers in the body
        response_data = response.json()
        if "headers" in response_data:
            assert "X-Custom-Header" in response_data["headers"]
            assert response_data["headers"]["X-Custom-Header"] == "test-value"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].method_name in ("GET", "DELETE")],
)
async def test_http_method_async_with_query_params(test_case: ParameterSet) -> None:
    """Test async HTTP request with query parameters."""
    tc = test_case.values[0]
    async with httpx.AsyncClient() as client:
        response = await tc.method_func(
            url=tc.test_url,
            params={"param1": "value1", "param2": "value2"},
            client=client,
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["args"] == {"param1": "value1", "param2": "value2"}
