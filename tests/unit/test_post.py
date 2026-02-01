r"""Unit tests for post_with_automatic_retry function.

This file contains tests that are specific to the POST HTTP method.
Common tests across all HTTP methods are in test_core.py.
"""

from __future__ import annotations

from unittest.mock import Mock

import httpx

from aresilient import post_with_automatic_retry

TEST_URL = "https://api.example.com/data"


###############################################
#     Tests for post_with_automatic_retry     #
###############################################


def test_post_with_automatic_retry_with_data(mock_client: httpx.Client, mock_sleep: Mock) -> None:
    """Test POST request with form data.

    This is POST-specific because form data submission is typically done
    with POST requests.
    """
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_client.post = Mock(return_value=mock_response)

    response = post_with_automatic_retry(
        TEST_URL, client=mock_client, data={"username": "test", "password": "secret"}
    )

    assert response.status_code == 200
    mock_client.post.assert_called_once_with(
        url=TEST_URL, data={"username": "test", "password": "secret"}
    )
    mock_sleep.assert_not_called()
