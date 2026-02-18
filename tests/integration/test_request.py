from __future__ import annotations

import httpx
import pytest

from aresilient import HttpRequestError
from aresilient.request import request

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#############################
#     Tests for request     #
#############################


def test_request_successful_request() -> None:
    """Test successful GET request without retries."""
    with httpx.Client() as client:
        response = request(url=f"{HTTPBIN_URL}/get", method="GET", request_func=client.get)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["url"] == "https://httpbin.org/get"


def test_get_with_non_retryable_status_fails_immediately() -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    with (
        httpx.Client() as client,
        pytest.raises(HttpRequestError, match=r"GET request to .* failed with status 404"),
    ):
        request(url=f"{HTTPBIN_URL}/status/404", method="GET", request_func=client.get)
