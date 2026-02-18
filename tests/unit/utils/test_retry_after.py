r"""Unit tests for Retry-After header parsing utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from aresilient.utils import parse_retry_after

#######################################
#     Tests for parse_retry_after     #
#######################################


@pytest.mark.parametrize(
    ("header", "seconds"), [("1", 1.0), ("0", 0.0), ("120", 120.0), ("3600", 3600.0)]
)
def test_parse_retry_after_integer(header: str, seconds: float) -> None:
    """Test parsing Retry-After header with integer seconds."""
    assert parse_retry_after(header) == seconds


@pytest.mark.parametrize("header", [None, "invalid", "not a number", "1.2.3"])
def test_parse_retry_after_none(header: str | None) -> None:
    """Test parsing None Retry-After header."""
    assert parse_retry_after(header) is None


def test_parse_retry_after_http_date() -> None:
    """Test parsing Retry-After header with HTTP-date format."""
    # Mock datetime.now to return a fixed time
    mock_datetime = Mock(
        spec=datetime,
        now=Mock(
            return_value=datetime(
                year=2015, month=10, day=21, hour=7, minute=28, second=0, tzinfo=timezone.utc
            )
        ),
    )

    with patch("aresilient.utils.retry_after.datetime", mock_datetime) as mock_datetime:
        # Test with a date 60 seconds in the future
        result = parse_retry_after("Wed, 21 Oct 2015 07:29:00 GMT")

        # Should return approximately 60 seconds
        assert result is not None
        assert 59.0 <= result <= 61.0
