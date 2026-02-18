r"""Unit tests for put function.

This file contains tests that are specific to the PUT HTTP method.
Common tests across all HTTP methods are in test_core.py.
"""

from __future__ import annotations

from unittest.mock import Mock

import httpx

from aresilient import put

TEST_URL = "https://api.example.com/data"


#########################
#     Tests for put     #
#########################


def test_put_with_data(mock_client: httpx.Client, mock_sleep: Mock) -> None:
    """Test PUT request with form data.

    This is PUT-specific because form data submission is typically done
    with PUT requests.
    """
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_client.put = Mock(return_value=mock_response)

    response = put(TEST_URL, client=mock_client, data={"username": "test", "role": "admin"})

    assert response.status_code == 200
    mock_client.put.assert_called_once_with(
        url=TEST_URL, data={"username": "test", "role": "admin"}
    )
    mock_sleep.assert_not_called()
