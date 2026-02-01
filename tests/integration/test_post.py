from __future__ import annotations

import httpx

from aresilient import post_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


###############################################
#     Tests for post_with_automatic_retry     #
###############################################
# Note: Common tests (successful request, non-retryable status, headers)
# are now in test_http_methods_common.py to avoid duplication across HTTP methods.
# This file contains POST-specific tests only.


def test_post_with_automatic_retry_large_request_body() -> None:
    """Test POST request with large JSON payload."""
    large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(100)]}

    with httpx.Client() as client:
        response = post_with_automatic_retry(
            url=f"{HTTPBIN_URL}/post", json=large_data, client=client
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["json"]["items"][0]["id"] == 0
    assert len(response_data["json"]["items"]) == 100


def test_post_with_automatic_retry_form_data() -> None:
    """Test POST request with form data."""
    with httpx.Client() as client:
        response = post_with_automatic_retry(
            url=f"{HTTPBIN_URL}/post", data={"field1": "value1", "field2": "value2"}, client=client
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["form"] == {"field1": "value1", "field2": "value2"}
