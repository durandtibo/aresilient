from __future__ import annotations

import httpx
import pytest

from aresilient import HttpRequestError, head_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


###############################################
#     Tests for head_with_automatic_retry     #
###############################################


def test_head_with_automatic_retry_successful_request() -> None:
    """Test successful HEAD request without retries."""
    with httpx.Client() as client:
        response = head_with_automatic_retry(url=f"{HTTPBIN_URL}/get", client=client)
    assert response.status_code == 200
    # HEAD requests should not have a body
    assert len(response.content) == 0
    # But should have headers
    assert "Content-Type" in response.headers


def test_head_with_automatic_retry_successful_request_without_client() -> None:
    """Test successful HEAD request without client."""
    response = head_with_automatic_retry(url=f"{HTTPBIN_URL}/get")
    assert response.status_code == 200
    assert len(response.content) == 0


def test_head_with_non_retryable_status_fails_immediately() -> None:
    """Test that 404 (non-retryable) fails immediately without retries."""
    with (
        httpx.Client() as client,
        pytest.raises(HttpRequestError, match=r"HEAD request to .* failed with status 404"),
    ):
        head_with_automatic_retry(url=f"{HTTPBIN_URL}/status/404", client=client)


def test_head_with_automatic_retry_check_content_length() -> None:
    """Test HEAD request to check Content-Length header."""
    with httpx.Client() as client:
        # Request a specific number of bytes to check Content-Length
        response = head_with_automatic_retry(url=f"{HTTPBIN_URL}/bytes/1024", client=client)

    assert response.status_code == 200
    # HEAD should return Content-Length header
    assert "Content-Length" in response.headers
    assert response.headers["Content-Length"] == "1024"
    # But no actual content
    assert len(response.content) == 0


def test_head_with_automatic_retry_with_headers() -> None:
    """Test HEAD request with custom headers."""
    with httpx.Client() as client:
        response = head_with_automatic_retry(
            url=f"{HTTPBIN_URL}/headers",
            client=client,
            headers={"X-Custom-Header": "test-value", "User-Agent": "aresilient-test"},
        )

    assert response.status_code == 200
    # HEAD request should succeed but have no body
    assert len(response.content) == 0
