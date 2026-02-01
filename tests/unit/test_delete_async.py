r"""Unit tests for delete_with_automatic_retry_async function.

This file contains tests that are specific to the async DELETE HTTP
method. Common tests across all async HTTP methods are in
test_core_async.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from aresilient import delete_with_automatic_retry_async

TEST_URL = "https://api.example.com/data"


@pytest.fixture
def mock_client() -> httpx.AsyncClient:
    """Create a mock httpx.AsyncClient for testing."""
    return Mock(spec=httpx.AsyncClient, aclose=AsyncMock())


########################################################
#     Tests for delete_with_automatic_retry_async     #
########################################################


@pytest.mark.asyncio
async def test_delete_with_automatic_retry_async_with_data(
    mock_client: httpx.AsyncClient, mock_asleep: Mock
) -> None:
    """Test async DELETE request with form data.

    This is DELETE-specific because some APIs accept data with DELETE
    requests.
    """
    mock_response = Mock(spec=httpx.Response, status_code=204)
    mock_client.delete = AsyncMock(return_value=mock_response)

    response = await delete_with_automatic_retry_async(
        TEST_URL, client=mock_client, data={"reason": "deprecated", "permanent": "true"}
    )

    assert response.status_code == 204
    mock_client.delete.assert_called_once_with(
        url=TEST_URL, data={"reason": "deprecated", "permanent": "true"}
    )
    mock_asleep.assert_not_called()
