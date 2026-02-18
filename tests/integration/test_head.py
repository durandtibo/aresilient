from __future__ import annotations

import httpx

from aresilient import head

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


###############################################
#     Tests for head     #
###############################################
# Note: Common tests (successful request, non-retryable status, headers)
# are now in test_core.py to avoid duplication across HTTP methods.
# This file contains HEAD-specific tests only.


def test_head_check_content_length() -> None:
    """Test HEAD request to check Content-Length header."""
    with httpx.Client() as client:
        # Request a specific number of bytes to check Content-Length
        response = head(url=f"{HTTPBIN_URL}/bytes/1024", client=client)

    assert response.status_code == 200
    # HEAD should return Content-Length header
    assert "Content-Length" in response.headers
    assert response.headers["Content-Length"] == "1024"
    # But no actual content
    assert len(response.content) == 0


def test_head_with_custom_headers() -> None:
    """Test HEAD request with custom headers."""
    with httpx.Client() as client:
        response = head(
            url=f"{HTTPBIN_URL}/headers",
            client=client,
            headers={"X-Custom-Header": "test-value"},
        )

    assert response.status_code == 200
    # HEAD request should succeed but have no body
    assert len(response.content) == 0


def test_head_successful_request_with_client() -> None:
    """Test successful HEAD request with explicit client."""
    with httpx.Client() as client:
        response = head(url=f"{HTTPBIN_URL}/get", client=client)

    assert response.status_code == 200
    # HEAD has no body
    assert len(response.content) == 0


def test_head_successful_request_without_client() -> None:
    """Test successful HEAD request without explicit client."""
    response = head(url=f"{HTTPBIN_URL}/get")

    assert response.status_code == 200
    # HEAD has no body
    assert len(response.content) == 0
