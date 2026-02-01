from __future__ import annotations

import httpx

from aresilient import get_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


##############################################
#     Tests for get_with_automatic_retry     #
##############################################
# Note: Common tests (successful request, non-retryable status, headers, query params)
# are now in test_http_methods_common.py to avoid duplication across HTTP methods.
# This file contains GET-specific tests only.


def test_get_with_automatic_retry_redirect_chain() -> None:
    """Test GET request that follows a redirect chain."""
    # httpbin.org supports redirects: /redirect/n redirects n times
    # Create a client with follow_redirects=True to handle the redirect chain
    with httpx.Client(follow_redirects=True) as client:
        response = get_with_automatic_retry(url=f"{HTTPBIN_URL}/redirect/3", client=client)

    assert response.status_code == 200
    # After redirects, we should end up at /get
    response_data = response.json()
    assert "url" in response_data


def test_get_with_automatic_retry_large_response() -> None:
    """Test GET request with large response body."""
    # Request a large amount of bytes (10KB)
    with httpx.Client() as client:
        response = get_with_automatic_retry(url=f"{HTTPBIN_URL}/bytes/10240", client=client)

    assert response.status_code == 200
    assert len(response.content) == 10240
