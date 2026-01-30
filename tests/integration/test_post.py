from __future__ import annotations

import httpx
import pytest

from aresnet import HttpRequestError, post_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


###################################################
#     Tests for post_with_automatic_retry     #
###################################################


def test_post_with_automatic_retry_successful_request() -> None:
    """Test successful POST request without retries."""
    with httpx.Client() as client:
        response = post_with_automatic_retry(
            url=f"{HTTPBIN_URL}/post", json={"test": "data", "number": 42}, client=client
        )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["url"] == "https://httpbin.org/post"
    assert response_data["json"] == {"test": "data", "number": 42}


def test_post_with_automatic_retry_successful_request_without_client() -> None:
    """Test successful POST request without retries."""
    response = post_with_automatic_retry(
        url=f"{HTTPBIN_URL}/post", json={"test": "data", "number": 42}
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["json"] == {"test": "data", "number": 42}


def test_post_with_non_retryable_status_fails_immediately() -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    with (
        httpx.Client() as client,
        pytest.raises(HttpRequestError, match=r"POST request to .* failed with status 404"),
    ):
        post_with_automatic_retry(url=f"{HTTPBIN_URL}/status/404", client=client)


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


def test_post_with_automatic_retry_with_headers() -> None:
    """Test POST request with custom headers."""
    with httpx.Client() as client:
        response = post_with_automatic_retry(
            url=f"{HTTPBIN_URL}/post",
            client=client,
            json={"test": "data"},
            headers={"X-Custom-Header": "test-value"},
        )

    assert response.status_code == 200
    response_data = response.json()
    assert "X-Custom-Header" in response_data["headers"]
    assert response_data["headers"]["X-Custom-Header"] == "test-value"
