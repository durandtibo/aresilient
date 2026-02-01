r"""Unit tests for get_with_automatic_retry function.

This file contains tests that are specific to the GET HTTP method.
Common tests across all HTTP methods are in test_core.py.
"""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresilient import get_with_automatic_retry

TEST_URL = "https://api.example.com/data"


@pytest.fixture
def mock_client() -> httpx.Client:
    """Create a mock httpx.Client for testing."""
    return Mock(spec=httpx.Client)


##############################################
#     Tests for get_with_automatic_retry     #
##############################################


def test_get_with_automatic_retry_with_params(mock_client: httpx.Client, mock_sleep: Mock) -> None:
    """Test GET request with query parameters.

    This is GET-specific because query parameters are typically used
    with GET requests.
    """
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_client.get = Mock(return_value=mock_response)

    response = get_with_automatic_retry(
        TEST_URL, client=mock_client, params={"page": 1, "limit": 10}
    )

    assert response.status_code == 200
    mock_client.get.assert_called_once_with(url=TEST_URL, params={"page": 1, "limit": 10})
    mock_sleep.assert_not_called()
