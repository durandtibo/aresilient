r"""Unit tests for put_with_automatic_retry_async function.

This file contains tests that are specific to the async PUT HTTP method.
Common tests across all async HTTP methods are in test_core_async.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from aresilient import put_with_automatic_retry_async

TEST_URL = "https://api.example.com/data"


####################################################
#     Tests for put_with_automatic_retry_async     #
####################################################


@pytest.mark.asyncio
async def test_put_with_automatic_retry_async_with_data(
    mock_async_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test async PUT request with form data.

    This is PUT-specific because form data submission is typically done
    with PUT requests.
    """
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_async_client.put = AsyncMock(return_value=mock_response)

    response = await put_with_automatic_retry_async(
        TEST_URL, client=mock_async_client, data={"username": "test", "role": "admin"}
    )

    assert response.status_code == 200
    mock_async_client.put.assert_called_once_with(
        url=TEST_URL, data={"username": "test", "role": "admin"}
    )
    mock_asleep.assert_not_called()
