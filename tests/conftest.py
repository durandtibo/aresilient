from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def mock_sleep() -> Generator[Mock, None, None]:
    """Patch time.sleep to make tests run faster."""
    with patch("time.sleep", return_value=None) as mock:
        yield mock


@pytest.fixture
def mock_asleep() -> Generator[Mock, None, None]:
    """Patch asyncio.sleep to make tests run faster."""
    with patch("asyncio.sleep", return_value=None) as mock:
        yield mock


@pytest.fixture
def mock_client() -> httpx.Client:
    """Create a mock httpx.Client for testing."""
    return Mock(spec=httpx.Client)


@pytest.fixture
def mock_async_client() -> httpx.AsyncClient:
    """Create a mock httpx.AsyncClient for testing."""
    return Mock(spec=httpx.AsyncClient, aclose=AsyncMock())


@pytest.fixture
def mock_response() -> httpx.Response:
    """Create a mock httpx.Response for testing."""
    return Mock(spec=httpx.Response, status_code=200)


@pytest.fixture
def mock_request_func(mock_response: httpx.Response) -> Mock:
    """Create a mock request function for testing."""
    return Mock(return_value=mock_response)


@pytest.fixture
def mock_async_request_func(mock_response: httpx.Response) -> AsyncMock:
    """Create a mock async request function for testing."""
    return AsyncMock(return_value=mock_response)


@pytest.fixture
def mock_callback() -> Mock:
    """Create a mock callback function for testing callbacks.

    This fixture provides a simple Mock object that can be used to test
    callback functionality across different test scenarios.

    Returns:
        A Mock object that can be used as a callback function.

    Example:
        >>> def test_callback(mock_callback):
        ...     some_function(on_request=mock_callback)
        ...     mock_callback.assert_called_once()
    """
    return Mock()
