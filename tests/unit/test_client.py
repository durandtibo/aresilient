r"""Unit tests for ResilientClient context manager.

This file contains tests for the synchronous context manager client.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, call, patch

import pytest

from aresilient import ResilientClient
from aresilient.core.config import DEFAULT_TIMEOUT, ClientConfig
from tests.helpers import create_mock_response

if TYPE_CHECKING:
    import httpx

TEST_URL = "https://api.example.com/data"


#####################################
#     Tests for ResilientClient     #
#####################################


def test_client_context_manager_basic(mock_sleep: Mock, mock_response: httpx.Response) -> None:
    """Test that ResilientClient works as a context manager."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(get=Mock(return_value=mock_response))
        mock_client_class.return_value = mock_client

        with ResilientClient() as client:
            response = client.get(TEST_URL)

        assert response.status_code == 200
        mock_client.get.assert_called_once_with(url=TEST_URL)
        mock_client.__exit__.assert_called_once_with(None, None, None)
    mock_sleep.assert_not_called()


def test_client_closes_on_exception(mock_sleep: Mock) -> None:
    """Test that ResilientClient closes properly even when exception
    occurs."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        msg = "test error"

        with pytest.raises(ValueError, match=r"test error"), ResilientClient():
            raise ValueError(msg)

        mock_client.__exit__.assert_called_once()

    mock_sleep.assert_not_called()


def test_client_outside_context_manager_raises(mock_sleep: Mock) -> None:
    """Test that using client outside context manager raises
    RuntimeError."""
    client = ResilientClient()

    with pytest.raises(RuntimeError, match=r"must be used within a context manager"):
        client.get(TEST_URL)

    mock_sleep.assert_not_called()


def test_client_multiple_requests(mock_sleep: Mock) -> None:
    """Test that ResilientClient can handle multiple requests."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(
            get=Mock(return_value=create_mock_response(status_code=200)),
            post=Mock(return_value=create_mock_response(status_code=201)),
        )
        mock_client_class.return_value = mock_client

        with ResilientClient(config=ClientConfig(max_retries=5)) as client:
            response1 = client.get("https://api.example.com/data1")
            response2 = client.post("https://api.example.com/data2", json={"key": "value"})

        assert response1.status_code == 200
        assert response2.status_code == 201
        mock_client.get.assert_called_once_with(url="https://api.example.com/data1")
        mock_client.post.assert_called_once_with(
            url="https://api.example.com/data2", json={"key": "value"}
        )
        mock_client.__exit__.assert_called_once_with(None, None, None)

    mock_sleep.assert_not_called()


def test_client_uses_custom_client(mock_sleep: Mock, mock_response: httpx.Response) -> None:
    """Test that ResilientClient uses a provided httpx.Client."""
    mock_client = Mock(get=Mock(return_value=mock_response))

    with ResilientClient(client=mock_client) as client:
        response = client.get(TEST_URL)

    assert response.status_code == 200
    mock_client.get.assert_called_once_with(url=TEST_URL)
    mock_client.__exit__.assert_not_called()
    mock_sleep.assert_not_called()


def test_client_get_method(mock_sleep: Mock, mock_response: httpx.Response) -> None:
    """Test client.get() method."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(get=Mock(return_value=mock_response))
        mock_client_class.return_value = mock_client

        with ResilientClient() as client:
            response = client.get(TEST_URL, params={"page": 1})

        assert response.status_code == 200
        mock_client.get.assert_called_once_with(url=TEST_URL, params={"page": 1})

    mock_sleep.assert_not_called()


def test_client_post_method(mock_sleep: Mock) -> None:
    """Test client.post() method."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(post=Mock(return_value=create_mock_response(status_code=201)))
        mock_client_class.return_value = mock_client

        with ResilientClient() as client:
            response = client.post(TEST_URL, json={"key": "value"})

        assert response.status_code == 201
        mock_client.post.assert_called_once_with(url=TEST_URL, json={"key": "value"})

    mock_sleep.assert_not_called()


def test_client_put_method(mock_sleep: Mock, mock_response: httpx.Response) -> None:
    """Test client.put() method."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(put=Mock(return_value=mock_response))
        mock_client_class.return_value = mock_client

        with ResilientClient() as client:
            response = client.put(TEST_URL, json={"key": "value"})

        assert response.status_code == 200
        mock_client.put.assert_called_once_with(url=TEST_URL, json={"key": "value"})

    mock_sleep.assert_not_called()


def test_client_delete_method(mock_sleep: Mock) -> None:
    """Test client.delete() method."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(delete=Mock(return_value=create_mock_response(status_code=204)))
        mock_client_class.return_value = mock_client

        with ResilientClient() as client:
            response = client.delete(TEST_URL)

        assert response.status_code == 204
        mock_client.delete.assert_called_once_with(url=TEST_URL)

    mock_sleep.assert_not_called()


def test_client_patch_method(mock_sleep: Mock, mock_response: httpx.Response) -> None:
    """Test client.patch() method."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(patch=Mock(return_value=mock_response))
        mock_client_class.return_value = mock_client

        with ResilientClient() as client:
            response = client.patch(TEST_URL, json={"key": "value"})

        assert response.status_code == 200
        mock_client.patch.assert_called_once_with(url=TEST_URL, json={"key": "value"})

    mock_sleep.assert_not_called()


def test_client_head_method(mock_sleep: Mock, mock_response: httpx.Response) -> None:
    """Test client.head() method."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(head=Mock(return_value=mock_response))
        mock_client_class.return_value = mock_client

        with ResilientClient() as client:
            response = client.head(TEST_URL)

        assert response.status_code == 200
        mock_client.head.assert_called_once_with(url=TEST_URL)

    mock_sleep.assert_not_called()


def test_client_options_method(mock_sleep: Mock, mock_response: httpx.Response) -> None:
    """Test client.options() method."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(options=Mock(return_value=mock_response))
        mock_client_class.return_value = mock_client

        with ResilientClient() as client:
            response = client.options(TEST_URL)

        assert response.status_code == 200
        mock_client.options.assert_called_once_with(url=TEST_URL)

    mock_sleep.assert_not_called()


def test_client_request_method(mock_sleep: Mock, mock_response: httpx.Response) -> None:
    """Test client.request() method with custom HTTP method."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(trace=Mock(return_value=mock_response))
        mock_client_class.return_value = mock_client

        with ResilientClient() as client:
            response = client.request(method="TRACE", url=TEST_URL)

        assert response.status_code == 200

    mock_sleep.assert_not_called()


def test_client_default_max_retries(
    mock_sleep: Mock, mock_response: httpx.Response, mock_response_fail: httpx.Response
) -> None:
    """Test that client's default max_retries is used when not
    overridden."""
    with patch("httpx.Client") as mock_client_class:
        # Simulate retryable error then success
        mock_client = Mock(get=Mock(side_effect=[mock_response_fail, mock_response]))
        mock_client_class.return_value = mock_client

        # Client configured with max_retries=2
        with ResilientClient(config=ClientConfig(max_retries=2)) as client:
            response = client.get(TEST_URL)

        # Should have retried using client's default
        assert response.status_code == 200
        assert mock_client.get.call_args_list == [call(url=TEST_URL), call(url=TEST_URL)]

    mock_sleep.assert_called_once_with(0.3)


def test_client_validation_max_retries_negative(mock_sleep: Mock) -> None:
    """Test that client validates max_retries parameter must be >= 0."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0, got -1"):
        ResilientClient(config=ClientConfig(max_retries=-1))

    mock_sleep.assert_not_called()


def test_client_default_timeout(mock_sleep: Mock) -> None:
    """Test that ResilientClient creates a default client with
    DEFAULT_TIMEOUT."""
    with patch("httpx.Client") as mock_client_class:
        ResilientClient()

        mock_client_class.assert_called_once_with(timeout=DEFAULT_TIMEOUT)

    mock_sleep.assert_not_called()


def test_client_shares_configuration_across_requests(
    mock_sleep: Mock, mock_response: httpx.Response
) -> None:
    """Test that all requests share the same configuration."""
    with patch("httpx.Client") as mock_client_class:
        mock_client = Mock(
            get=Mock(return_value=mock_response), post=Mock(return_value=mock_response)
        )
        mock_client_class.return_value = mock_client

        # Create client with specific configuration
        with ResilientClient(config=ClientConfig(max_retries=5, jitter_factor=0.5)) as client:
            client.get(TEST_URL)
            client.post(TEST_URL)

        # Both requests should use the same client
        mock_client.get.assert_called_once_with(url=TEST_URL)
        mock_client.post.assert_called_once_with(url=TEST_URL)

    mock_sleep.assert_not_called()


def test_client_exit_without_enter() -> None:
    """Test that __exit__ can be called without __enter__.

    This tests that calling __exit__ before entering the context manager
    does not raise an error and properly delegates to the owned client.
    """
    with patch("httpx.Client") as mock_client_class:
        client = ResilientClient()

        # Manually trigger __exit__ without calling __enter__
        client.__exit__(None, None, None)

        # Should complete without errors
        mock_client_class.return_value.__exit__.assert_called_once_with(None, None, None)
        assert client._entered is False
