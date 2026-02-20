r"""Backoff and sleep time calculation utilities.

This module provides functions for calculating sleep time with backoff
strategies and jitter for HTTP request retries.
"""

from __future__ import annotations

__all__ = ["calculate_sleep_time"]

import logging
import random
from typing import TYPE_CHECKING

from aresilient.backoff.exponential import ExponentialBackoff
from aresilient.utils.retry_after import parse_retry_after

if TYPE_CHECKING:
    import httpx

    from aresilient.backoff.base import BaseBackoffStrategy

logger: logging.Logger = logging.getLogger(__name__)


def calculate_sleep_time(
    attempt: int,
    jitter_factor: float,
    response: httpx.Response | None,
    backoff_strategy: BaseBackoffStrategy | None = None,
    max_wait_time: float | None = None,
) -> float:
    """Calculate sleep time for retry with backoff strategy and jitter.

    This function implements backoff strategies with optional jitter for retrying
    failed HTTP requests. It also supports the Retry-After header when present in
    the server response, which takes precedence over the backoff calculation.
    Advanced backoff strategies can be used by providing a BaseBackoffStrategy instance.

    The sleep time is calculated as follows:
    1. Determine base sleep time:
       - If Retry-After header is present: use that value
       - Otherwise: use backoff_strategy.calculate(attempt)
    2. Apply max_wait_time cap (if max_wait_time is set):
       - sleep_time = min(sleep_time, max_wait_time)
    3. Apply jitter (if jitter_factor > 0):
       - jitter = random.uniform(0, jitter_factor) * base_sleep_time
       - total_sleep_time = base_sleep_time + jitter

    Args:
        attempt: The current attempt number (0-indexed). For example,
            attempt=0 is the first retry, attempt=1 is the second retry, etc.
        jitter_factor: Factor for adding random jitter to backoff delays.
            The jitter is calculated as: random.uniform(0, jitter_factor) * base_sleep_time,
            and this jitter is ADDED to the base sleep time. Set to 0 to disable jitter.
            Recommended value is 0.1 to add up to 10% additional random delay.
        response: The HTTP response object (if available). Used to extract
            the Retry-After header if present.
        backoff_strategy: BaseBackoffStrategy instance or None.
            Defaults to ExponentialBackoff with base_delay=0.3.
        max_wait_time: Optional maximum backoff delay cap in seconds.
            If provided, individual backoff delays will not exceed this value,
            even with exponential backoff growth or Retry-After headers.

    Returns:
        The calculated sleep time in seconds, including any jitter applied.

    Example:
        ```pycon
        >>> from aresilient.utils.sleep import calculate_sleep_time
        >>> from aresilient.backoff import ExponentialBackoff
        >>> # First retry with ExponentialBackoff(base_delay=0.3), no jitter
        >>> calculate_sleep_time(attempt=0, jitter_factor=0.0, response=None)
        0.3
        >>> # Second retry
        >>> calculate_sleep_time(attempt=1, jitter_factor=0.0, response=None)
        0.6
        >>> # Third retry
        >>> calculate_sleep_time(attempt=2, jitter_factor=0.0, response=None)
        1.2
        >>> # Third retry with max_wait_time cap
        >>> calculate_sleep_time(attempt=2, jitter_factor=0.0, response=None, max_wait_time=1.0)
        1.0

        ```
    """
    # Check for Retry-After header in the response (if available)
    retry_after_sleep: float | None = None
    if response is not None and hasattr(response, "headers"):
        retry_after_header = response.headers.get("Retry-After")
        retry_after_sleep = parse_retry_after(retry_after_header)

    # Use Retry-After if available, otherwise use backoff strategy
    if retry_after_sleep is not None:
        sleep_time = retry_after_sleep
        logger.debug(f"Using Retry-After header value: {sleep_time:.2f}s")
    else:
        if backoff_strategy is None:
            backoff_strategy = ExponentialBackoff()
        sleep_time = backoff_strategy.calculate(attempt)

    # Apply max_wait_time cap if configured
    if max_wait_time is not None and sleep_time > max_wait_time:
        logger.debug(
            f"Capping sleep time from {sleep_time:.2f}s to {max_wait_time:.2f}s (max_wait_time={max_wait_time:.2f}s)"
        )
        sleep_time = max_wait_time

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
