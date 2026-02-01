"""Integration tests for retry_if custom predicate functionality.

These tests verify the retry_if predicate works end-to-end with actual
httpx clients and servers.
"""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresilient import HttpRequestError, get_with_automatic_retry

####################################################
#     Integration tests for retry_if predicate     #
####################################################


def test_retry_if_with_response_content_check() -> None:
    """Test retry_if checking response content in real scenario."""
    # Create responses that will be returned in sequence
    mock_response_retry = Mock(spec=httpx.Response, status_code=200, text="please retry")
    mock_response_ok = Mock(spec=httpx.Response, status_code=200, text="success")

    # Create a mock client that returns these responses
    mock_client = Mock(spec=httpx.Client)
    mock_client.get = Mock(side_effect=[mock_response_retry, mock_response_ok])

    def should_retry(response: httpx.Response | None, exception: Exception | None) -> bool:
        """Retry if response contains 'retry'."""
        return bool(response and "retry" in response.text.lower())

    response = get_with_automatic_retry(
        url="https://api.example.com/data",
        client=mock_client,
        retry_if=should_retry,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_client.get.call_count == 2


def test_retry_if_with_custom_status_logic() -> None:
    """Test retry_if with custom status code logic."""
    mock_response_429 = Mock(spec=httpx.Response, status_code=429)
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)

    mock_client = Mock(spec=httpx.Client)
    mock_client.get = Mock(side_effect=[mock_response_429, mock_response_500, mock_response_ok])

    def should_retry(response: httpx.Response | None, exception: Exception | None) -> bool:
        """Retry on 429 or 500."""
        return bool(response and response.status_code in (429, 500))

    response = get_with_automatic_retry(
        url="https://api.example.com/data",
        client=mock_client,
        retry_if=should_retry,
        max_retries=5,
    )

    assert response == mock_response_ok
    assert mock_client.get.call_count == 3


def test_retry_if_with_exception_handling() -> None:
    """Test retry_if handles exceptions correctly."""
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)

    mock_client = Mock(spec=httpx.Client)
    mock_client.get = Mock(
        side_effect=[
            httpx.ConnectError("connection failed"),
            httpx.TimeoutException("timeout"),
            mock_response_ok,
        ]
    )

    def should_retry(response: httpx.Response | None, exception: Exception | None) -> bool:
        """Retry on network errors."""
        return bool(isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)))

    response = get_with_automatic_retry(
        url="https://api.example.com/data",
        client=mock_client,
        retry_if=should_retry,
        max_retries=5,
    )

    assert response == mock_response_ok
    assert mock_client.get.call_count == 3


def test_retry_if_exhausts_retries() -> None:
    """Test retry_if exhausts retries when always returning True."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)

    mock_client = Mock(spec=httpx.Client)
    mock_client.get = Mock(return_value=mock_response_500)

    def should_retry(response: httpx.Response | None, exception: Exception | None) -> bool:
        """Always retry."""
        return True

    with pytest.raises(HttpRequestError, match="failed with status 500 after 4 attempts"):
        get_with_automatic_retry(
            url="https://api.example.com/data",
            client=mock_client,
            retry_if=should_retry,
            max_retries=3,
        )

    # Should have tried 4 times (initial + 3 retries)
    assert mock_client.get.call_count == 4


def test_retry_if_does_not_retry() -> None:
    """Test retry_if that always returns False (no retry)."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)

    mock_client = Mock(spec=httpx.Client)
    mock_client.get = Mock(return_value=mock_response_500)

    def should_retry(response: httpx.Response | None, exception: Exception | None) -> bool:
        """Never retry."""
        return False

    with pytest.raises(HttpRequestError, match="failed with status 500"):
        get_with_automatic_retry(
            url="https://api.example.com/data",
            client=mock_client,
            retry_if=should_retry,
            max_retries=3,
        )

    # Should only try once
    mock_client.get.assert_called_once()


def test_retry_if_with_complex_business_logic() -> None:
    """Test retry_if with complex business logic scenario."""
    # Simulate API responses with different content
    mock_response_insufficient = Mock(
        spec=httpx.Response, status_code=400, text='{"error": "insufficient funds"}'
    )
    mock_response_rate_limit = Mock(
        spec=httpx.Response, status_code=200, text='{"status": "rate_limited"}'
    )
    mock_response_ok = Mock(spec=httpx.Response, status_code=200, text='{"status": "success"}')

    mock_client = Mock(spec=httpx.Client)
    mock_client.get = Mock(
        side_effect=[mock_response_insufficient, mock_response_rate_limit, mock_response_ok]
    )

    def should_retry(response: httpx.Response | None, exception: Exception | None) -> bool:
        """Custom business logic for retry:
        - Retry on insufficient funds (can be replenished)
        - Retry on rate limit in response content
        - Don't retry on other errors
        """
        if response:
            # Retry if insufficient funds (will be replenished)
            if "insufficient funds" in response.text.lower():
                return True
            # Retry if rate limited
            if "rate_limit" in response.text.lower():
                return True
        return False

    response = get_with_automatic_retry(
        url="https://api.example.com/data",
        client=mock_client,
        retry_if=should_retry,
        max_retries=5,
    )

    assert response == mock_response_ok
    assert mock_client.get.call_count == 3


def test_retry_if_with_callbacks() -> None:
    """Test retry_if works with on_retry and on_success callbacks."""
    mock_response_500 = Mock(spec=httpx.Response, status_code=500)
    mock_response_ok = Mock(spec=httpx.Response, status_code=200)

    mock_client = Mock(spec=httpx.Client)
    mock_client.get = Mock(side_effect=[mock_response_500, mock_response_ok])

    on_retry_callback = Mock()
    on_success_callback = Mock()

    def should_retry(response: httpx.Response | None, exception: Exception | None) -> bool:
        return bool(response and response.status_code >= 500)

    response = get_with_automatic_retry(
        url="https://api.example.com/data",
        client=mock_client,
        retry_if=should_retry,
        on_retry=on_retry_callback,
        on_success=on_success_callback,
        max_retries=3,
    )

    assert response == mock_response_ok
    assert mock_client.get.call_count == 2
    on_retry_callback.assert_called_once()
    on_success_callback.assert_called_once()
