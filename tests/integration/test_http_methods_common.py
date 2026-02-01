from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from aresilient import HttpRequestError
from tests.helpers import HTTP_METHODS, HTTPBIN_URL

if TYPE_CHECKING:
    from _pytest.mark.structures import ParameterSet


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_http_method_successful_request_with_client(test_case: ParameterSet) -> None:
    """Test successful HTTP request with explicit client."""
    tc = test_case.values[0]
    with httpx.Client() as client:
        if tc.supports_body:
            response = tc.method_func(
                url=tc.test_url,
                json={"test": "data", "number": 42},
                client=client,
            )
        else:
            response = tc.method_func(url=tc.test_url, client=client)

    assert response.status_code == 200 or (
        tc.method_name == "OPTIONS" and response.status_code == 405
    )

    # Verify response data (except for HEAD and OPTIONS which have no body)
    if tc.method_name not in ("HEAD", "OPTIONS"):
        response_data = response.json()
        assert tc.test_url in response_data["url"]
        if tc.supports_body:
            assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_http_method_successful_request_without_client(test_case: ParameterSet) -> None:
    """Test successful HTTP request without explicit client."""
    tc = test_case.values[0]
    if tc.supports_body:
        response = tc.method_func(
            url=tc.test_url,
            json={"test": "data", "number": 42},
        )
    else:
        response = tc.method_func(url=tc.test_url)

    assert response.status_code == 200 or (
        tc.method_name == "OPTIONS" and response.status_code == 405
    )

    # Verify response data (except for HEAD and OPTIONS which have no body)
    if tc.method_name not in ("HEAD", "OPTIONS"):
        response_data = response.json()
        if tc.supports_body:
            assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS if tc.values[0].method_name != "OPTIONS"],
)
def test_http_method_non_retryable_status_fails_immediately(test_case: ParameterSet) -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    tc = test_case.values[0]
    with (
        httpx.Client() as client,
        pytest.raises(
            HttpRequestError, match=rf"{tc.method_name} request to .* failed with status 404"
        ),
    ):
        tc.method_func(url=f"{HTTPBIN_URL}/status/404", client=client)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_http_method_with_custom_headers(test_case: ParameterSet) -> None:
    """Test HTTP request with custom headers."""
    tc = test_case.values[0]
    with httpx.Client() as client:
        if tc.supports_body:
            response = tc.method_func(
                url=tc.test_url,
                client=client,
                json={"test": "data"},
                headers={"X-Custom-Header": "test-value"},
            )
        else:
            # Use /headers endpoint for methods that don't support body
            test_endpoint = f"{HTTPBIN_URL}/headers" if tc.method_name != "OPTIONS" else tc.test_url
            response = tc.method_func(
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


@pytest.mark.parametrize(
    "test_case",
    [tc for tc in HTTP_METHODS if tc.values[0].method_name in ("GET", "DELETE")],
)
def test_http_method_with_query_params(test_case: ParameterSet) -> None:
    """Test HTTP request with query parameters."""
    tc = test_case.values[0]
    with httpx.Client() as client:
        response = tc.method_func(
            url=tc.test_url,
            params={"param1": "value1", "param2": "value2"},
            client=client,
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["args"] == {"param1": "value1", "param2": "value2"}
