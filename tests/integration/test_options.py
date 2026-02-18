from __future__ import annotations

import httpx

from aresilient import options

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#################################################
#     Tests for options     #
#################################################
# Note: Common tests (successful request, headers)
# are now in test_core.py to avoid duplication across HTTP methods.
# This file contains OPTIONS-specific tests only.


def test_options_with_custom_headers() -> None:
    """Test OPTIONS request with custom headers."""
    with httpx.Client() as client:
        response = options(
            url=f"{HTTPBIN_URL}/get",
            client=client,
            headers={"X-Custom-Header": "test-value"},
        )

    # OPTIONS may return 405 on httpbin
    assert response.status_code in (200, 405)


def test_options_successful_request_with_client() -> None:
    """Test successful OPTIONS request with explicit client."""
    with httpx.Client() as client:
        response = options(url=f"{HTTPBIN_URL}/get", client=client)

    # OPTIONS may return 405 on httpbin
    assert response.status_code in (200, 405)


def test_options_successful_request_without_client() -> None:
    """Test successful OPTIONS request without explicit client."""
    response = options(url=f"{HTTPBIN_URL}/get")

    # OPTIONS may return 405 on httpbin
    assert response.status_code in (200, 405)
