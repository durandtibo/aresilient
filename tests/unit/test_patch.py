r"""Unit tests for patch function.

This file contains tests that are specific to the PATCH HTTP method.
Common tests across all HTTP methods are in test_core.py.
"""

from __future__ import annotations

from unittest.mock import Mock

import httpx

from aresilient import patch

TEST_URL = "https://api.example.com/data"


###########################
#     Tests for patch     #
###########################


def test_patch_with_data(mock_client: httpx.Client, mock_sleep: Mock) -> None:
    """Test PATCH request with form data.

    This is PATCH-specific because form data submission is typically
    done with PATCH requests.
    """
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_client.patch = Mock(return_value=mock_response)

    response = patch(TEST_URL, client=mock_client, data={"status": "active"})

    assert response.status_code == 200
    mock_client.patch.assert_called_once_with(url=TEST_URL, data={"status": "active"})
    mock_sleep.assert_not_called()
