r"""Parameter validation utilities for HTTP request retry logic.

This module provides validation functions for retry parameters to ensure
they meet the required constraints before being used in HTTP request
retry logic.
"""

from __future__ import annotations

__all__ = ["validate_retry_params", "validate_timeout"]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx


def validate_timeout(timeout: float | httpx.Timeout) -> None:
    """Validate timeout parameter.

    Args:
        timeout: Maximum seconds to wait for server responses.
            Must be > 0 if provided as a numeric value.

    Raises:
        ValueError: If timeout is a numeric value <= 0.

    Example:
        ```pycon
        >>> from aresilient.core.validation import validate_timeout
        >>> validate_timeout(10.0)
        >>> validate_timeout(30)
        >>> validate_timeout(0)  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        ValueError: timeout must be > 0, got 0

        ```
    """
    if isinstance(timeout, (int, float)) and timeout <= 0:
        msg = f"timeout must be > 0, got {timeout}"
        raise ValueError(msg)


def validate_retry_params(
    max_retries: int,
    jitter_factor: float = 0.0,
    max_total_time: float | None = None,
    max_wait_time: float | None = None,
) -> None:
    """Validate retry parameters.

    Args:
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0. A value of 0 means no retries (only the initial attempt).
        jitter_factor: Factor for adding random jitter to backoff delays.
            Must be >= 0. Recommended value is 0.1 for 10% jitter.
        max_total_time: Maximum total time budget for all retry attempts.
            Must be > 0 if provided. The retry loop will stop if the total
            elapsed time exceeds this value.
        max_wait_time: Maximum backoff delay cap in seconds.
            Must be > 0 if provided. Individual backoff delays will not exceed
            this value, even with exponential backoff growth.

    Raises:
        ValueError: If max_retries or jitter_factor are negative,
            or if timeout, max_total_time, or max_wait_time are non-positive.

    Example:
        ```pycon
        >>> from aresilient.core import validate_retry_params
        >>> validate_retry_params(max_retries=3)
        >>> validate_retry_params(max_retries=3, jitter_factor=0.1)
        >>> validate_retry_params(max_retries=3, max_total_time=30.0)
        >>> validate_retry_params(max_retries=3, max_wait_time=5.0)
        >>> validate_retry_params(max_retries=-1)  # doctest: +SKIP

        ```
    """
    if max_retries < 0:
        msg = f"max_retries must be >= 0, got {max_retries}"
        raise ValueError(msg)
    if jitter_factor < 0:
        msg = f"jitter_factor must be >= 0, got {jitter_factor}"
        raise ValueError(msg)
    if max_total_time is not None and max_total_time <= 0:
        msg = f"max_total_time must be > 0, got {max_total_time}"
        raise ValueError(msg)
    if max_wait_time is not None and max_wait_time <= 0:
        msg = f"max_wait_time must be > 0, got {max_wait_time}"
        raise ValueError(msg)
