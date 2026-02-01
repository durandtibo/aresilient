r"""Unit tests for post_with_automatic_retry function.

This file contains tests that are specific to the POST HTTP method.
Common tests across all HTTP methods are in test_core.py.
"""

from __future__ import annotations

from unittest.mock import Mock

import httpx

from aresilient import post_with_automatic_retry
from tests.helpers import assert_successful_request, setup_mock_client_for_method

TEST_URL = "https://api.example.com/data"


###############################################
#     Tests for post_with_automatic_retry     #
###############################################


def test_post_with_automatic_retry_with_data(mock_sleep: Mock) -> None:
    """Test POST request with form data.

    This is POST-specific because form data submission is typically done
    with POST requests. This test demonstrates the use of test utility
    functions to reduce boilerplate code.
    """
    # Use utility function to set up mock client - more concise than manual setup
    client, _ = setup_mock_client_for_method("post", 200)

    # Use utility function to assert successful request
    response = assert_successful_request(
        post_with_automatic_retry,
        TEST_URL,
        client,
        data={"username": "test", "password": "secret"},
    )

    # Verify the request was made with correct data
    client.post.assert_called_once_with(
        url=TEST_URL, data={"username": "test", "password": "secret"}
    )
    mock_sleep.assert_not_called()
