from __future__ import annotations

import httpx

from aresilient import put_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


##############################################
#     Tests for put_with_automatic_retry     #
##############################################
# Note: Common tests (successful request, non-retryable status, headers)
# are now in test_core.py to avoid duplication across HTTP methods.
# This file contains PUT-specific tests only.


def test_put_with_automatic_retry_large_request_body() -> None:
    """Test PUT request with large JSON payload."""
    large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(100)]}

    with httpx.Client() as client:
        response = put_with_automatic_retry(
            url=f"{HTTPBIN_URL}/put", json=large_data, client=client
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["json"]["items"][0]["id"] == 0
    assert len(response_data["json"]["items"]) == 100


def test_put_with_automatic_retry_form_data() -> None:
    """Test PUT request with form data."""
    with httpx.Client() as client:
        response = put_with_automatic_retry(
            url=f"{HTTPBIN_URL}/put", data={"field1": "value1", "field2": "value2"}, client=client
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["form"] == {"field1": "value1", "field2": "value2"}
