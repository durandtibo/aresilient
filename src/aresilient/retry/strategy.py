r"""Retry strategy for calculating backoff delays.

This module provides the RetryStrategy class for calculating retry
delays.
"""

from __future__ import annotations

__all__ = ["RetryStrategy"]

from typing import TYPE_CHECKING

from aresilient.backoff.sleep import calculate_sleep_time

if TYPE_CHECKING:
    import httpx

    from aresilient.backoff.strategy import BackoffStrategy


class RetryStrategy:
    """Strategy for calculating retry delays with backoff and jitter.

    This class encapsulates the logic for calculating sleep times between
    retry attempts using configurable backoff strategies and jitter.

    Attributes:
        backoff_factor: Factor for exponential backoff calculations.
        jitter_factor: Factor for adding random jitter to delays.
        backoff_strategy: Optional custom backoff strategy instance.
        max_wait_time: Optional maximum wait time cap in seconds.
    """

    def __init__(
        self,
        backoff_factor: float,
        jitter_factor: float,
        backoff_strategy: BackoffStrategy | None = None,
        max_wait_time: float | None = None,
    ) -> None:
        """Initialize retry strategy.

        Args:
            backoff_factor: Factor for exponential backoff.
            jitter_factor: Factor for adding random jitter.
            backoff_strategy: Optional custom backoff strategy.
            max_wait_time: Optional maximum wait time cap.
        """
        self.backoff_factor = backoff_factor
        self.jitter_factor = jitter_factor
        self.backoff_strategy = backoff_strategy
        self.max_wait_time = max_wait_time

    def calculate_delay(
        self,
        attempt: int,
        response: httpx.Response | None = None,
    ) -> float:
        """Calculate delay before next retry.

        Args:
            attempt: Current attempt number (0-indexed).
            response: Optional HTTP response.

        Returns:
            Sleep time in seconds.
        """
        return calculate_sleep_time(
            attempt,
            self.backoff_factor,
            self.jitter_factor,
            response,
            self.backoff_strategy,
            self.max_wait_time,
        )
