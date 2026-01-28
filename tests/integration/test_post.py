from __future__ import annotations

import httpx
import pytest

from aresnet import post_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


###############################################
#     Tests for post_with_automatic_retry     #
###############################################


def test_post_with_automatic_retry_successful_request() -> None:
    """Test successful POST request without retries."""
    response = post_with_automatic_retry(
        url=f"{HTTPBIN_URL}/post", json={"test": "data", "number": 42}
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["json"] == {"test": "data", "number": 42}


def test_post_with_automatic_retry_successful_request_with_client() -> None:
    """Test successful POST request without retries."""
    with httpx.Client() as client:
        response = post_with_automatic_retry(url=f"{HTTPBIN_URL}/post", client=client)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["url"] == "https://httpbin.org/post"


def test_post_with_non_retryable_status_fails_immediately() -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    with pytest.raises(httpx.HTTPStatusError):
        post_with_automatic_retry(url=f"{HTTPBIN_URL}/status/404")
