from __future__ import annotations

import httpx
import pytest

from aresnet import HttpRequestError, get_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


##################################################
#     Tests for get_with_automatic_retry     #
##################################################


def test_get_with_automatic_retry_successful_request() -> None:
    """Test successful GET request without retries."""
    with httpx.Client() as client:
        response = get_with_automatic_retry(url=f"{HTTPBIN_URL}/get", client=client)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["url"] == "https://httpbin.org/get"


def test_get_with_automatic_retry_successful_request_without_client() -> None:
    """Test successful GET request without retries."""
    response = get_with_automatic_retry(url=f"{HTTPBIN_URL}/get")
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
        get_with_automatic_retry(url=f"{HTTPBIN_URL}/status/404", client=client)


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


def test_get_with_automatic_retry_with_headers() -> None:
    """Test GET request with custom headers."""
    with httpx.Client() as client:
        response = get_with_automatic_retry(
            url=f"{HTTPBIN_URL}/headers",
            client=client,
            headers={"X-Custom-Header": "test-value", "User-Agent": "aresnet-test"},
        )

    assert response.status_code == 200
    response_data = response.json()
    assert "X-Custom-Header" in response_data["headers"]
    assert response_data["headers"]["X-Custom-Header"] == "test-value"


def test_get_with_automatic_retry_with_query_params() -> None:
    """Test GET request with query parameters."""
    with httpx.Client() as client:
        response = get_with_automatic_retry(
            url=f"{HTTPBIN_URL}/get", params={"param1": "value1", "param2": "value2"}, client=client
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["args"] == {"param1": "value1", "param2": "value2"}
