r"""Configuration dataclasses for retry behavior.

This module provides configuration objects for retry logic and
callbacks.
"""

from __future__ import annotations

__all__ = ["CallbackConfig", "RetryConfig"]

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from aresilient.backoff.strategy import BackoffStrategy


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Factor for exponential backoff.
        status_forcelist: Tuple of HTTP status codes that trigger retries.
        jitter_factor: Factor for adding random jitter to backoff delays.
        retry_if: Optional custom predicate to determine retry behavior.
        backoff_strategy: Optional custom backoff strategy.
        max_total_time: Optional maximum total time budget for all retries.
        max_wait_time: Optional maximum backoff delay cap.
    """

    max_retries: int
    backoff_factor: float
    status_forcelist: tuple[int, ...]
    jitter_factor: float
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None = None
    backoff_strategy: BackoffStrategy | None = None
    max_total_time: float | None = None
    max_wait_time: float | None = None


@dataclass
class CallbackConfig:
    """Configuration for callbacks.

    Attributes:
        on_request: Optional callback invoked before each request attempt.
        on_retry: Optional callback invoked before each retry.
        on_success: Optional callback invoked when request succeeds.
        on_failure: Optional callback invoked when all retries are exhausted.
    """

    on_request: Callable | None = None
    on_retry: Callable | None = None
    on_success: Callable | None = None
    on_failure: Callable | None = None
