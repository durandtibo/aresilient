r"""Unit tests for get_with_automatic_retry_async function.

This file contains tests that are specific to the async GET HTTP method.
Common tests across all async HTTP methods are in test_core_async.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from aresilient import get_with_automatic_retry_async
from tests.utils_helpers import (
    assert_successful_request_async,
    setup_mock_async_client_for_method,
)

TEST_URL = "https://api.example.com/data"


####################################################
#     Tests for get_with_automatic_retry_async     #
####################################################


@pytest.mark.asyncio
async def test_get_with_automatic_retry_async_with_params(mock_asleep: Mock) -> None:
    """Test async GET request with query parameters.

    This is GET-specific because query parameters are typically used
    with GET requests. This test demonstrates the use of async test
    utility functions to reduce boilerplate code.
    """
    # Use utility function to set up mock async client - more concise than manual setup
    client, _ = setup_mock_async_client_for_method("get", 200)

    # Use utility function to assert successful request
    response = await assert_successful_request_async(
        get_with_automatic_retry_async,
        TEST_URL,
        client,
        params={"page": 1, "limit": 10},
    )

    # Verify the request was made with correct parameters
    client.get.assert_called_once_with(url=TEST_URL, params={"page": 1, "limit": 10})
    mock_asleep.assert_not_called()
