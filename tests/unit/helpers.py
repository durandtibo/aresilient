r"""Shared test helpers and fixtures for HTTP method wrapper tests.

This module contains common test infrastructure used across multiple
test files to reduce duplication and improve maintainability.
"""

from __future__ import annotations

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
    from collections.abc import Callable

    import httpx


@dataclass
class HttpMethodTestCase:
    """Test case definition for HTTP method testing.

    Attributes:
        method_name: The HTTP method name (e.g., "GET", "POST").
        method_func: The function to test (e.g., get_with_automatic_retry).
        client_method: The httpx.Client method name (e.g., "get", "post").
        status_code: Expected success status code.
    """

    method_name: str
    method_func: Callable[..., httpx.Response]
    client_method: str
    status_code: int


# Define test parameters for all sync HTTP methods
HTTP_METHODS = [
    pytest.param(
        HttpMethodTestCase(
            method_name="GET",
            method_func=get_with_automatic_retry,
            client_method="get",
            status_code=200,
        ),
        id="GET",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="POST",
            method_func=post_with_automatic_retry,
            client_method="post",
            status_code=200,
        ),
        id="POST",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="PUT",
            method_func=put_with_automatic_retry,
            client_method="put",
            status_code=200,
        ),
        id="PUT",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="DELETE",
            method_func=delete_with_automatic_retry,
            client_method="delete",
            status_code=204,
        ),
        id="DELETE",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="PATCH",
            method_func=patch_with_automatic_retry,
            client_method="patch",
            status_code=200,
        ),
        id="PATCH",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="HEAD",
            method_func=head_with_automatic_retry,
            client_method="head",
            status_code=200,
        ),
        id="HEAD",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="OPTIONS",
            method_func=options_with_automatic_retry,
            client_method="options",
            status_code=200,
        ),
        id="OPTIONS",
    ),
]


# Define test parameters for all async HTTP methods
HTTP_METHODS_ASYNC = [
    pytest.param(
        HttpMethodTestCase(
            method_name="GET",
            method_func=get_with_automatic_retry_async,
            client_method="get",
            status_code=200,
        ),
        id="GET",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="POST",
            method_func=post_with_automatic_retry_async,
            client_method="post",
            status_code=200,
        ),
        id="POST",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="PUT",
            method_func=put_with_automatic_retry_async,
            client_method="put",
            status_code=200,
        ),
        id="PUT",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="DELETE",
            method_func=delete_with_automatic_retry_async,
            client_method="delete",
            status_code=204,
        ),
        id="DELETE",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="PATCH",
            method_func=patch_with_automatic_retry_async,
            client_method="patch",
            status_code=200,
        ),
        id="PATCH",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="HEAD",
            method_func=head_with_automatic_retry_async,
            client_method="head",
            status_code=200,
        ),
        id="HEAD",
    ),
    pytest.param(
        HttpMethodTestCase(
            method_name="OPTIONS",
            method_func=options_with_automatic_retry_async,
            client_method="options",
            status_code=200,
        ),
        id="OPTIONS",
    ),
]
