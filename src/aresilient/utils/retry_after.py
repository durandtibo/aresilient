r"""Retry-After header parsing utilities.

This module provides functions for parsing the Retry-After header value
from HTTP responses according to RFC 7231.
"""

from __future__ import annotations

__all__ = ["parse_retry_after"]

import logging
from contextlib import suppress
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

logger: logging.Logger = logging.getLogger(__name__)


def parse_retry_after(retry_after_header: str | None) -> float | None:
    """Parse the Retry-After header value from an HTTP response.

    The Retry-After header can be specified in two formats according to RFC 7231:
    1. An integer representing the number of seconds to wait (e.g., "120")
    2. An HTTP-date in RFC 5322 format (e.g., "Wed, 21 Oct 2015 07:28:00 GMT")

    This function attempts to parse both formats and returns the number of seconds
    to wait. If parsing fails or the header is absent, it returns None to allow
    the caller to use the default exponential backoff strategy.

    Args:
        retry_after_header: The value of the Retry-After header as a string,
            or None if the header is not present in the response.

    Returns:
        The number of seconds to wait before retrying, or None if:
        - The header is not present (retry_after_header is None)
        - The header value cannot be parsed as either an integer or HTTP-date
        For HTTP-date format, negative values (dates in the past) are clamped to 0.0.

    Example:
        ```pycon
        >>> from aresilient.utils import parse_retry_after
        >>> # Parse integer seconds
        >>> parse_retry_after("120")
        120.0
        >>> parse_retry_after("0")
        0.0
        >>> # No header present
        >>> parse_retry_after(None) is None
        True
        >>> # Invalid format returns None
        >>> parse_retry_after("invalid") is None
        True

        ```
    """
    if retry_after_header is None:
        return None

    # Try parsing as an integer (seconds)
    with suppress(ValueError):
        return float(retry_after_header)

    # Try parsing as HTTP-date (RFC 5322 format)
    try:
        retry_date: datetime = parsedate_to_datetime(retry_after_header)
        now = datetime.now(timezone.utc)
        delta_seconds = (retry_date - now).total_seconds()
        # Ensure we don't return negative values
        return max(0.0, delta_seconds)
    except (ValueError, TypeError, OverflowError):
        logger.debug(f"Failed to parse Retry-After header: {retry_after_header!r}")
        return None
