r"""Unit tests for patch_with_automatic_retry_async function.

This file contains tests that are specific to the async PATCH HTTP
method. Common tests across all async HTTP methods are in
test_core_async.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from aresilient import patch_with_automatic_retry_async

TEST_URL = "https://api.example.com/data"


######################################################
#     Tests for patch_with_automatic_retry_async     #
######################################################


@pytest.mark.asyncio
async def test_patch_with_automatic_retry_async_with_data(
    mock_async_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test async PATCH request with form data.

    This is PATCH-specific because form data submission is typically
    done with PATCH requests.
    """
    mock_response = Mock(spec=httpx.Response, status_code=200)
    mock_async_client.patch = AsyncMock(return_value=mock_response)

    response = await patch_with_automatic_retry_async(
        TEST_URL, client=mock_async_client, data={"status": "active"}
    )

    assert response.status_code == 200
    mock_async_client.patch.assert_called_once_with(url=TEST_URL, data={"status": "active"})
    mock_asleep.assert_not_called()
