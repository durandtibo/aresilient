from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from aresilient import (
    HttpRequestError,
    delete_with_automatic_retry,
    get_with_automatic_retry,
    head_with_automatic_retry,
    options_with_automatic_retry,
    patch_with_automatic_retry,
    post_with_automatic_retry,
    put_with_automatic_retry,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"

# HTTP method mapping for parametrized tests
HTTP_METHODS = {
    "GET": (get_with_automatic_retry, "/get", False),
    "POST": (post_with_automatic_retry, "/post", True),
    "PUT": (put_with_automatic_retry, "/put", True),
    "PATCH": (patch_with_automatic_retry, "/patch", True),
    "DELETE": (delete_with_automatic_retry, "/delete", False),
    "HEAD": (head_with_automatic_retry, "/get", False),
    "OPTIONS": (options_with_automatic_retry, "/get", False),
}


@pytest.mark.parametrize(
    ("method_name", "func", "endpoint", "supports_body"),
    [
        (method, *config)
        for method, config in HTTP_METHODS.items()
    ],
    ids=list(HTTP_METHODS.keys()),
)
def test_http_method_successful_request_with_client(
    method_name: str, func: Callable[..., httpx.Response], endpoint: str, supports_body: bool
) -> None:
    """Test successful HTTP request with explicit client."""
    with httpx.Client() as client:
        if supports_body:
            response = func(
                url=f"{HTTPBIN_URL}{endpoint}",
                json={"test": "data", "number": 42},
                client=client,
            )
        else:
            response = func(url=f"{HTTPBIN_URL}{endpoint}", client=client)

    assert response.status_code == 200 or (method_name == "OPTIONS" and response.status_code == 405)

    # Verify response data (except for HEAD and OPTIONS which have no body)
    if method_name not in ("HEAD", "OPTIONS"):
        response_data = response.json()
        assert f"https://httpbin.org{endpoint}" in response_data["url"]
        if supports_body:
            assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.parametrize(
    ("method_name", "func", "endpoint", "supports_body"),
    [
        (method, *config)
        for method, config in HTTP_METHODS.items()
    ],
    ids=list(HTTP_METHODS.keys()),
)
def test_http_method_successful_request_without_client(
    method_name: str, func: Callable[..., httpx.Response], endpoint: str, supports_body: bool
) -> None:
    """Test successful HTTP request without explicit client."""
    if supports_body:
        response = func(
            url=f"{HTTPBIN_URL}{endpoint}",
            json={"test": "data", "number": 42},
        )
    else:
        response = func(url=f"{HTTPBIN_URL}{endpoint}")

    assert response.status_code == 200 or (method_name == "OPTIONS" and response.status_code == 405)

    # Verify response data (except for HEAD and OPTIONS which have no body)
    if method_name not in ("HEAD", "OPTIONS"):
        response_data = response.json()
        if supports_body:
            assert response_data["json"] == {"test": "data", "number": 42}


@pytest.mark.parametrize(
    ("method_name", "func"),
    [
        (method, config[0])
        for method, config in HTTP_METHODS.items()
        if method != "OPTIONS"  # OPTIONS doesn't consistently return 404
    ],
    ids=[method for method in HTTP_METHODS if method != "OPTIONS"],
)
def test_http_method_non_retryable_status_fails_immediately(
    method_name: str, func: Callable[..., httpx.Response]
) -> None:
    """Test that 404 (non-retryable) fails immediately without retries."""
    with (
        httpx.Client() as client,
        pytest.raises(
            HttpRequestError, match=rf"{method_name} request to .* failed with status 404"
        ),
    ):
        func(url=f"{HTTPBIN_URL}/status/404", client=client)


@pytest.mark.parametrize(
    ("method_name", "func", "endpoint", "supports_body"),
    [
        (method, *config)
        for method, config in HTTP_METHODS.items()
    ],
    ids=list(HTTP_METHODS.keys()),
)
def test_http_method_with_custom_headers(
    method_name: str, func: Callable[..., httpx.Response], endpoint: str, supports_body: bool
) -> None:
    """Test HTTP request with custom headers."""
    with httpx.Client() as client:
        if supports_body:
            response = func(
                url=f"{HTTPBIN_URL}{endpoint}",
                client=client,
                json={"test": "data"},
                headers={"X-Custom-Header": "test-value"},
            )
        else:
            # Use /headers endpoint for methods that don't support body
            test_endpoint = "/headers" if method_name != "OPTIONS" else endpoint
            response = func(
                url=f"{HTTPBIN_URL}{test_endpoint}",
                client=client,
                headers={"X-Custom-Header": "test-value"},
            )

    assert response.status_code == 200 or (method_name == "OPTIONS" and response.status_code == 405)

    # Verify headers in response (except for HEAD which has no body)
    if method_name == "HEAD":
        # HEAD request should succeed but have no body
        assert len(response.content) == 0
    elif method_name != "OPTIONS":
        # For OPTIONS, httpbin might not return the headers in the body
        response_data = response.json()
        if "headers" in response_data:
            assert "X-Custom-Header" in response_data["headers"]
            assert response_data["headers"]["X-Custom-Header"] == "test-value"


@pytest.mark.parametrize(
    ("method_name", "func"),
    [
        ("GET", get_with_automatic_retry),
        ("DELETE", delete_with_automatic_retry),
    ],
    ids=["GET", "DELETE"],
)
def test_http_method_with_query_params(method_name: str, func: Callable[..., httpx.Response]) -> None:
    """Test HTTP request with query parameters."""
    endpoint = f"/{method_name.lower()}"
    with httpx.Client() as client:
        response = func(
            url=f"{HTTPBIN_URL}{endpoint}",
            params={"param1": "value1", "param2": "value2"},
            client=client,
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["args"] == {"param1": "value1", "param2": "value2"}
