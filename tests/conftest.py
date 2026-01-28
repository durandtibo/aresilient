from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def mock_sleep() -> Generator[Mock, None, None]:
    """Patch time.sleep to make tests run faster."""
    with patch("time.sleep", return_value=None) as mock:
        yield mock
