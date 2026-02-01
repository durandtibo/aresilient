from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from aresilient import HttpRequestError
from tests.helpers import HTTP_METHODS_ASYNC, HTTPBIN_URL

if TYPE_CHECKING:
    from tests.helpers import AsyncHttpMethodTestCase


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].supports_body],
)
async def test_http_method_async_successful_request_with_client_with_body(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test successful async HTTP request with explicit client for methods that support body."""
    tc = test_case
    async with httpx.AsyncClient() as client:
        response = await tc.method_func(
            url=tc.test_url,
            json={"test": "data", "number": 42},
            client=client,
        )

    assert response.status_code == 200

    # Verify response data
    response_data = response.json()
    assert tc.test_url in response_data["url"]
    assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if not tc.values[0].supports_body and tc.values[0].method_name not in ("HEAD", "OPTIONS")],
)
async def test_http_method_async_successful_request_with_client_without_body(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test successful async HTTP request with explicit client for methods without body support."""
    tc = test_case
    async with httpx.AsyncClient() as client:
        response = await tc.method_func(url=tc.test_url, client=client)

    assert response.status_code == 200

    # Verify response data
    response_data = response.json()
    assert tc.test_url in response_data["url"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].method_name == "HEAD"],
)
async def test_http_method_async_successful_request_with_client_head(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test successful async HEAD request with explicit client."""
    tc = test_case
    async with httpx.AsyncClient() as client:
        response = await tc.method_func(url=tc.test_url, client=client)

    assert response.status_code == 200
    # HEAD has no body
    assert len(response.content) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].method_name == "OPTIONS"],
)
async def test_http_method_async_successful_request_with_client_options(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test successful async OPTIONS request with explicit client."""
    tc = test_case
    async with httpx.AsyncClient() as client:
        response = await tc.method_func(url=tc.test_url, client=client)

    # OPTIONS may return 405 on httpbin
    assert response.status_code in (200, 405)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].supports_body],
)
async def test_http_method_async_successful_request_without_client_with_body(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test successful async HTTP request without explicit client for methods that support body."""
    tc = test_case
    response = await tc.method_func(
        url=tc.test_url,
        json={"test": "data", "number": 42},
    )

    assert response.status_code == 200

    # Verify response data
    response_data = response.json()
    assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if not tc.values[0].supports_body and tc.values[0].method_name not in ("HEAD", "OPTIONS")],
)
async def test_http_method_async_successful_request_without_client_without_body(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test successful async HTTP request without explicit client for methods without body support."""
    tc = test_case
    response = await tc.method_func(url=tc.test_url)

    assert response.status_code == 200

    # Verify response data
    response_data = response.json()
    assert "url" in response_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].method_name == "HEAD"],
)
async def test_http_method_async_successful_request_without_client_head(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test successful async HEAD request without explicit client."""
    tc = test_case
    response = await tc.method_func(url=tc.test_url)

    assert response.status_code == 200
    # HEAD has no body
    assert len(response.content) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].method_name == "OPTIONS"],
)
async def test_http_method_async_successful_request_without_client_options(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test successful async OPTIONS request without explicit client."""
    tc = test_case
    response = await tc.method_func(url=tc.test_url)

    # OPTIONS may return 405 on httpbin
    assert response.status_code in (200, 405)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].method_name != "OPTIONS"],
)
async def test_http_method_async_non_retryable_status_fails_immediately(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    tc = test_case
    async with httpx.AsyncClient() as client:
        with pytest.raises(
            HttpRequestError, match=rf"{tc.method_name} request to .* failed with status 404"
        ):
            await tc.method_func(url=f"{HTTPBIN_URL}/status/404", client=client)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].supports_body],
)
async def test_http_method_async_with_custom_headers_with_body(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test async HTTP request with custom headers for methods that support body."""
    tc = test_case
    async with httpx.AsyncClient() as client:
        response = await tc.method_func(
            url=tc.test_url,
            client=client,
            json={"test": "data"},
            headers={"X-Custom-Header": "test-value"},
        )

    assert response.status_code == 200

    # Verify headers in response
    response_data = response.json()
    assert "headers" in response_data
    assert "X-Custom-Header" in response_data["headers"]
    assert response_data["headers"]["X-Custom-Header"] == "test-value"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if not tc.values[0].supports_body and tc.values[0].method_name not in ("GET", "HEAD", "OPTIONS")],
)
async def test_http_method_async_with_custom_headers_without_body(
    test_case: AsyncHttpMethodTestCase,
) -> None:
    """Test async HTTP request with custom headers for methods without body support (except GET, HEAD, OPTIONS)."""
    tc = test_case
    async with httpx.AsyncClient() as client:
        response = await tc.method_func(
            url=tc.test_url,
            client=client,
            headers={"X-Custom-Header": "test-value"},
        )

    assert response.status_code == 200

    # Verify headers in response
    response_data = response.json()
    assert "headers" in response_data
    assert "X-Custom-Header" in response_data["headers"]
    assert response_data["headers"]["X-Custom-Header"] == "test-value"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS_ASYNC if tc.values[0].method_name in ("GET", "DELETE")],
)
async def test_http_method_async_with_query_params(test_case: AsyncHttpMethodTestCase) -> None:
    """Test async HTTP request with query parameters."""
    tc = test_case
    async with httpx.AsyncClient() as client:
        response = await tc.method_func(
            url=tc.test_url,
            params={"param1": "value1", "param2": "value2"},
            client=client,
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["args"] == {"param1": "value1", "param2": "value2"}
