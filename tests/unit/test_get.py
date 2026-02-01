r"""Unit tests for get_with_automatic_retry function.

This file contains tests that are specific to the GET HTTP method.
Common tests across all HTTP methods are in test_core.py.
"""

from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresilient import get_with_automatic_retry
from tests.test_utils_helpers import assert_successful_request, setup_mock_client_for_method

TEST_URL = "https://api.example.com/data"


##############################################
#     Tests for get_with_automatic_retry     #
##############################################


def test_get_with_automatic_retry_with_params(mock_sleep: Mock) -> None:
    """Test GET request with query parameters.

    This is GET-specific because query parameters are typically used
    with GET requests.
    
    This test demonstrates the use of test utility functions to reduce
    boilerplate code.
    """
    # Use utility function to set up mock client - more concise than manual setup
    client, _ = setup_mock_client_for_method("get", 200)

    # Use utility function to assert successful request
    response = assert_successful_request(
        get_with_automatic_retry,
        TEST_URL,
        client,
        params={"page": 1, "limit": 10},
    )

    # Verify the request was made with correct parameters
    client.get.assert_called_once_with(url=TEST_URL, params={"page": 1, "limit": 10})
    mock_sleep.assert_not_called()
