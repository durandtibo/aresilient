from __future__ import annotations

import httpx

from aresilient import head_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


###############################################
#     Tests for head_with_automatic_retry     #
###############################################
# Note: Common tests (successful request, non-retryable status, headers)
# are now in test_http_methods_common.py to avoid duplication across HTTP methods.
# This file contains HEAD-specific tests only.


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
