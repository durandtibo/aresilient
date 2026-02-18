r"""Unit tests for delete function.

This file contains tests that are specific to the DELETE HTTP method.
Common tests across all HTTP methods are in test_core.py.
"""

from __future__ import annotations

from unittest.mock import Mock

import httpx

from aresilient import delete

TEST_URL = "https://api.example.com/data"


############################
#     Tests for delete     #
############################


def test_delete_with_data(mock_client: httpx.Client, mock_sleep: Mock) -> None:
    """Test DELETE request with form data.

    This is DELETE-specific because some APIs accept data with DELETE
    requests.
    """
    mock_response = Mock(spec=httpx.Response, status_code=204)
    mock_client.delete = Mock(return_value=mock_response)

    response = delete(
        TEST_URL, client=mock_client, data={"reason": "deprecated", "permanent": "true"}
    )

    assert response.status_code == 204
    mock_client.delete.assert_called_once_with(
        url=TEST_URL, data={"reason": "deprecated", "permanent": "true"}
    )
    mock_sleep.assert_not_called()
