from __future__ import annotations

import httpx

from aresilient import options_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#################################################
#     Tests for options_with_automatic_retry     #
#################################################
# Note: Common tests (successful request, headers)
# are now in test_core.py to avoid duplication across HTTP methods.
# This file contains OPTIONS-specific tests only.


def test_options_with_automatic_retry_with_custom_headers() -> None:
    """Test OPTIONS request with custom headers."""
    with httpx.Client() as client:
        response = options_with_automatic_retry(
            url=f"{HTTPBIN_URL}/get",
            client=client,
            headers={"X-Custom-Header": "test-value"},
        )

    # OPTIONS may return 405 on httpbin
    assert response.status_code in (200, 405)
