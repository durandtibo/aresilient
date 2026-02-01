r"""Shared test helpers and fixtures for HTTP method wrapper tests.

This module contains common test infrastructure used across multiple
test files to reduce duplication and improve maintainability.
"""

from __future__ import annotations

__all__ = [
    "HTTPBIN_URL",
    "HTTP_METHODS",
    "HTTP_METHODS_ASYNC",
    "AsyncHttpMethodTestCase",
    "HttpMethodTestCase",
]

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from aresilient import (
    delete_with_automatic_retry,
    delete_with_automatic_retry_async,
    get_with_automatic_retry,
    get_with_automatic_retry_async,
    head_with_automatic_retry,
    head_with_automatic_retry_async,
    options_with_automatic_retry,
    options_with_automatic_retry_async,
    patch_with_automatic_retry,
    patch_with_automatic_retry_async,
    post_with_automatic_retry,
    post_with_automatic_retry_async,
    put_with_automatic_retry,
    put_with_automatic_retry_async,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import httpx

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


@dataclass
class HttpMethodTestCase:
    """Test case definition for HTTP method testing.

    Attributes:
        method_name: The HTTP method name (e.g., "GET", "POST").
        method_func: The function to test (e.g., get_with_automatic_retry).
        client_method: The httpx.Client method name (e.g., "get", "post").
        status_code: Expected success status code.
        test_url: The full test URL (e.g., "https://httpbin.org/get"). Optional.
        supports_body: Whether the HTTP method supports request bodies. Optional.
    """

    method_name: str
    method_func: Callable[..., httpx.Response]
    client_method: str
    status_code: int | None = None
    test_url: str | None = None
    supports_body: bool | None = None


@dataclass
class AsyncHttpMethodTestCase:
    """Test case definition for async HTTP method testing.

    Attributes:
        method_name: The HTTP method name (e.g., "GET", "POST").
        method_func: The async function to test (e.g., get_with_automatic_retry_async).
        client_method: The httpx.AsyncClient method name (e.g., "get", "post").
        status_code: Expected success status code.
        test_url: The full test URL (e.g., "https://httpbin.org/get"). Optional.
        supports_body: Whether the HTTP method supports request bodies. Optional.
    """

    method_name: str
    method_func: Callable[..., Awaitable[httpx.Response]]
    client_method: str
    status_code: int | None = None
    test_url: str | None = None
    supports_body: bool | None = None


# Define test parameters for all sync HTTP methods
HTTP_METHODS = [
    pytest.param(
        HttpMethodTestCase(
            method_name="GET",
            method_func=get_with_automatic_retry,
            client_method="get",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="GET",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="POST",
            method_func=post_with_automatic_retry,
            client_method="post",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/post",
            supports_body=True,
        ),
        id="POST",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="PUT",
            method_func=put_with_automatic_retry,
            client_method="put",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/put",
            supports_body=True,
        ),
        id="PUT",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="DELETE",
            method_func=delete_with_automatic_retry,
            client_method="delete",
            status_code=204,
            test_url=f"{HTTPBIN_URL}/delete",
            supports_body=False,
        ),
        id="DELETE",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="PATCH",
            method_func=patch_with_automatic_retry,
            client_method="patch",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/patch",
            supports_body=True,
        ),
        id="PATCH",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="HEAD",
            method_func=head_with_automatic_retry,
            client_method="head",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="HEAD",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="OPTIONS",
            method_func=options_with_automatic_retry,
            client_method="options",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="OPTIONS",
    ),
]


# Define test parameters for all async HTTP methods
HTTP_METHODS_ASYNC = [
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="GET",
            method_func=get_with_automatic_retry_async,
            client_method="get",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="GET",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="POST",
            method_func=post_with_automatic_retry_async,
            client_method="post",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/post",
            supports_body=True,
        ),
        id="POST",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="PUT",
            method_func=put_with_automatic_retry_async,
            client_method="put",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/put",
            supports_body=True,
        ),
        id="PUT",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="DELETE",
            method_func=delete_with_automatic_retry_async,
            client_method="delete",
            status_code=204,
            test_url=f"{HTTPBIN_URL}/delete",
            supports_body=False,
        ),
        id="DELETE",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="PATCH",
            method_func=patch_with_automatic_retry_async,
            client_method="patch",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/patch",
            supports_body=True,
        ),
        id="PATCH",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="HEAD",
            method_func=head_with_automatic_retry_async,
            client_method="head",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="HEAD",
    ),
    pytest.param(
        AsyncHttpMethodTestCase(
            method_name="OPTIONS",
            method_func=options_with_automatic_retry_async,
            client_method="options",
            status_code=200,
            test_url=f"{HTTPBIN_URL}/get",
            supports_body=False,
        ),
        id="OPTIONS",
    ),
]
