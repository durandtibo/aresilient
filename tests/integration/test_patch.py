from __future__ import annotations

import httpx

from aresilient import patch

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


################################################
#     Tests for patch     #
################################################
# Note: Common tests (successful request, non-retryable status, headers)
# are now in test_core.py to avoid duplication across HTTP methods.
# This file contains PATCH-specific tests only.


def test_patch_large_request_body() -> None:
    """Test PATCH request with large JSON payload."""
    large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(100)]}

    with httpx.Client() as client:
        response = patch(url=f"{HTTPBIN_URL}/patch", json=large_data, client=client)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["json"]["items"][0]["id"] == 0
    assert len(response_data["json"]["items"]) == 100


def test_patch_form_data() -> None:
    """Test PATCH request with form data."""
    with httpx.Client() as client:
        response = patch(
            url=f"{HTTPBIN_URL}/patch", data={"field1": "value1", "field2": "value2"}, client=client
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["form"] == {"field1": "value1", "field2": "value2"}
