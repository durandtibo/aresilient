r"""Backoff and sleep time calculation utilities.

This module provides functions for calculating sleep time with exponential
backoff and jitter for HTTP request retries.
"""

from __future__ import annotations

__all__ = ["calculate_sleep_time"]

import logging
import random
from typing import TYPE_CHECKING

from aresilient.utils.retry_after import parse_retry_after

if TYPE_CHECKING:
    import httpx

logger: logging.Logger = logging.getLogger(__name__)


def calculate_sleep_time(
    attempt: int,
    backoff_factor: float,
    jitter_factor: float,
    response: httpx.Response | None,
) -> float:
    """Calculate sleep time for retry with exponential backoff and
    jitter.

    This function implements an exponential backoff strategy with optional
    jitter for retrying failed HTTP requests. It also supports the Retry-After
    header when present in the server response, which takes precedence over
    the exponential backoff calculation.

    The sleep time is calculated as follows:
    1. Determine base sleep time:
       - If Retry-After header is present: use that value
       - Otherwise: backoff_factor * (2 ** attempt)
    2. Apply jitter (if jitter_factor > 0):
       - jitter = random.uniform(0, jitter_factor) * base_sleep_time
       - total_sleep_time = base_sleep_time + jitter

    Args:
        attempt: The current attempt number (0-indexed). For example,
            attempt=0 is the first retry, attempt=1 is the second retry, etc.
        backoff_factor: Factor for exponential backoff between retries.
            The base wait time is calculated as: backoff_factor * (2 ** attempt).
        jitter_factor: Factor for adding random jitter to backoff delays.
            The jitter is calculated as: random.uniform(0, jitter_factor) * base_sleep_time,
            and this jitter is ADDED to the base sleep time. Set to 0 to disable jitter.
            Recommended value is 0.1 to add up to 10% additional random delay.
        response: The HTTP response object (if available). Used to extract
            the Retry-After header if present.

    Returns:
        The calculated sleep time in seconds, including any jitter applied.

    Example:
        ```pycon
        >>> from aresilient.utils import calculate_sleep_time
        >>> # First retry with backoff_factor=0.3, no jitter
        >>> calculate_sleep_time(attempt=0, backoff_factor=0.3, jitter_factor=0.0, response=None)
        0.3
        >>> # Second retry
        >>> calculate_sleep_time(attempt=1, backoff_factor=0.3, jitter_factor=0.0, response=None)
        0.6
        >>> # Third retry
        >>> calculate_sleep_time(attempt=2, backoff_factor=0.3, jitter_factor=0.0, response=None)
        1.2

        ```
    """
    # Check for Retry-After header in the response (if available)
    retry_after_sleep: float | None = None
    if response is not None and hasattr(response, "headers"):
        retry_after_header = response.headers.get("Retry-After")
        retry_after_sleep = parse_retry_after(retry_after_header)

    # Use Retry-After if available, otherwise use exponential backoff
    if retry_after_sleep is not None:
        sleep_time = retry_after_sleep
        logger.debug(f"Using Retry-After header value: {sleep_time:.2f}s")
    else:
        sleep_time = backoff_factor * (2**attempt)

    # Add jitter if jitter_factor is configured
    if jitter_factor > 0:
        jitter = random.uniform(0, jitter_factor) * sleep_time  # noqa: S311
        total_sleep_time = sleep_time + jitter
        logger.debug(
            f"Waiting {total_sleep_time:.2f}s before retry (base={sleep_time:.2f}s, jitter={jitter:.2f}s)"
        )
    else:
        total_sleep_time = sleep_time
        logger.debug(f"Waiting {total_sleep_time:.2f}s before retry")

    return total_sleep_time
