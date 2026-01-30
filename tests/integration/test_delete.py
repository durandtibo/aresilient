from __future__ import annotations

import httpx
import pytest

from aresnet import HttpRequestError, delete_with_automatic_retry

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


##################################################
#     Tests for delete_with_automatic_retry     #
##################################################


def test_delete_with_automatic_retry_successful_request() -> None:
    """Test successful DELETE request without retries."""
    with httpx.Client() as client:
        response = delete_with_automatic_retry(url=f"{HTTPBIN_URL}/delete", client=client)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["url"] == "https://httpbin.org/delete"


def test_delete_with_automatic_retry_successful_request_without_client() -> None:
    """Test successful DELETE request without retries."""
    response = delete_with_automatic_retry(url=f"{HTTPBIN_URL}/delete")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["url"] == "https://httpbin.org/delete"


def test_delete_with_non_retryable_status_fails_immediately() -> None:
    """Test that 404 (non-retryable) fails immediately without
    retries."""
    with (
        httpx.Client() as client,
        pytest.raises(HttpRequestError, match=r"DELETE request to .* failed with status 404"),
    ):
        delete_with_automatic_retry(url=f"{HTTPBIN_URL}/status/404", client=client)


def test_delete_with_automatic_retry_with_headers() -> None:
    """Test DELETE request with custom headers."""
    with httpx.Client() as client:
        response = delete_with_automatic_retry(
            url=f"{HTTPBIN_URL}/delete",
            client=client,
            headers={"X-Custom-Header": "test-value"},
        )

    assert response.status_code == 200
    response_data = response.json()
    assert "X-Custom-Header" in response_data["headers"]
    assert response_data["headers"]["X-Custom-Header"] == "test-value"


def test_delete_with_automatic_retry_with_query_params() -> None:
    """Test DELETE request with query parameters."""
    with httpx.Client() as client:
        response = delete_with_automatic_retry(
            url=f"{HTTPBIN_URL}/delete",
            params={"param1": "value1", "param2": "value2"},
            client=client,
        )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["args"] == {"param1": "value1", "param2": "value2"}
