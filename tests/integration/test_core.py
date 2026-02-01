from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from aresilient import HttpRequestError
from tests.helpers import HTTP_METHODS, HTTPBIN_URL

if TYPE_CHECKING:
    from tests.helpers import HttpMethodTestCase


@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS if tc.values[0].supports_body],
)
def test_http_method_successful_request_with_client_with_body(
    test_case: HttpMethodTestCase,
) -> None:
    """Test successful HTTP request with explicit client for methods
    that support body."""
    tc = test_case
    with httpx.Client() as client:
        response = tc.method_func(
            url=tc.test_url,
            json={"test": "data", "number": 42},
            client=client,
        )

    assert response.status_code == 200

    # Verify response data
    response_data = response.json()
    assert tc.test_url in response_data["url"]
    assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.parametrize(
    "test_case",
    [
        tc
        for tc in HTTP_METHODS
        if not tc.values[0].supports_body and tc.values[0].method_name not in ("HEAD", "OPTIONS")
    ],
)
def test_http_method_successful_request_with_client_without_body(
    test_case: HttpMethodTestCase,
) -> None:
    """Test successful HTTP request with explicit client for methods
    without body support."""
    tc = test_case
    with httpx.Client() as client:
        response = tc.method_func(url=tc.test_url, client=client)

    assert response.status_code == 200

    # Verify response data
    response_data = response.json()
    assert tc.test_url in response_data["url"]


@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS if tc.values[0].supports_body],
)
def test_http_method_successful_request_without_client_with_body(
    test_case: HttpMethodTestCase,
) -> None:
    """Test successful HTTP request without explicit client for methods
    that support body."""
    tc = test_case
    response = tc.method_func(
        url=tc.test_url,
        json={"test": "data", "number": 42},
    )

    assert response.status_code == 200

    # Verify response data
    response_data = response.json()
    assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.parametrize(
    "test_case",
    [
        tc
        for tc in HTTP_METHODS
        if not tc.values[0].supports_body and tc.values[0].method_name not in ("HEAD", "OPTIONS")
    ],
)
def test_http_method_successful_request_without_client_without_body(
    test_case: HttpMethodTestCase,
) -> None:
    """Test successful HTTP request without explicit client for methods
    without body support."""
    tc = test_case
    response = tc.method_func(url=tc.test_url)

    assert response.status_code == 200

    # Verify response data
    response_data = response.json()
    assert "url" in response_data


@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS if tc.values[0].method_name != "OPTIONS"],
)
def test_http_method_non_retryable_status_fails_immediately(test_case: HttpMethodTestCase) -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    tc = test_case
    with (
        httpx.Client() as client,
        pytest.raises(
            HttpRequestError, match=rf"{tc.method_name} request to .* failed with status 404"
        ),
    ):
        tc.method_func(url=f"{HTTPBIN_URL}/status/404", client=client)


@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS if tc.values[0].supports_body],
)
def test_http_method_with_custom_headers_with_body(test_case: HttpMethodTestCase) -> None:
    """Test HTTP request with custom headers for methods that support
    body."""
    tc = test_case
    with httpx.Client() as client:
        response = tc.method_func(
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


@pytest.mark.parametrize(
    "test_case",
    [
        tc
        for tc in HTTP_METHODS
        if not tc.values[0].supports_body
        and tc.values[0].method_name not in ("GET", "HEAD", "OPTIONS")
    ],
)
def test_http_method_with_custom_headers_without_body(test_case: HttpMethodTestCase) -> None:
    """Test HTTP request with custom headers for methods without body
    support (except GET, HEAD, OPTIONS)."""
    tc = test_case
    with httpx.Client() as client:
        response = tc.method_func(
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


@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS if tc.values[0].method_name in ("GET", "DELETE")],
)
def test_http_method_with_query_params(test_case: HttpMethodTestCase) -> None:
    """Test HTTP request with query parameters."""
    tc = test_case
    with httpx.Client() as client:
        response = tc.method_func(
            url=tc.test_url,
            params={"param1": "value1", "param2": "value2"},
            client=client,
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["args"] == {"param1": "value1", "param2": "value2"}
