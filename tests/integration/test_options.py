from __future__ import annotations

import httpx
import pytest

from aresilient import HttpRequestError, options_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#################################################
#     Tests for options_with_automatic_retry     #
#################################################


def test_options_with_automatic_retry_successful_request() -> None:
    """Test successful OPTIONS request without retries."""
    with httpx.Client() as client:
        response = options_with_automatic_retry(url=f"{HTTPBIN_URL}/get", client=client)
    # httpbin may return 200 or 405 for OPTIONS depending on endpoint
    assert response.status_code in (200, 405)


def test_options_with_automatic_retry_successful_request_without_client() -> None:
    """Test successful OPTIONS request without client."""
    response = options_with_automatic_retry(url=f"{HTTPBIN_URL}/get")
    assert response.status_code in (200, 405)


def test_options_with_non_retryable_status_fails_immediately() -> None:
    """Test that 404 (non-retryable) fails immediately without retries."""
    with (
        httpx.Client() as client,
        pytest.raises(HttpRequestError, match=r"OPTIONS request to .* failed with status 404"),
    ):
        options_with_automatic_retry(url=f"{HTTPBIN_URL}/status/404", client=client)


def test_options_with_automatic_retry_with_headers() -> None:
    """Test OPTIONS request with custom headers."""
    with httpx.Client() as client:
        response = options_with_automatic_retry(
            url=f"{HTTPBIN_URL}/headers",
            client=client,
            headers={"X-Custom-Header": "test-value", "Origin": "https://example.com"},
        )

    # httpbin may not support OPTIONS on all endpoints
    assert response.status_code in (200, 405)
