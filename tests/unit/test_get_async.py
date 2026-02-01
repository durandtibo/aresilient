r"""Unit tests for get_with_automatic_retry_async function.

This file contains tests that are specific to the async GET HTTP method.
Common tests across all async HTTP methods are in test_core_async.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from aresilient import get_with_automatic_retry_async

TEST_URL = "https://api.example.com/data"


####################################################
#     Tests for get_with_automatic_retry_async     #
####################################################


@pytest.mark.asyncio
async def test_get_with_automatic_retry_async_with_params(
    mock_async_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test async GET request with query parameters.

    This is GET-specific because query parameters are typically used
    with GET requests.
    """
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_async_client.get = AsyncMock(return_value=mock_response)

    response = await get_with_automatic_retry_async(
        TEST_URL, client=mock_async_client, params={"page": 1, "limit": 10}
    )

    assert response.status_code == 200
    mock_async_client.get.assert_called_once_with(url=TEST_URL, params={"page": 1, "limit": 10})
    mock_asleep.assert_not_called()
