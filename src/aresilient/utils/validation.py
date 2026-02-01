r"""Parameter validation utilities for HTTP request retry logic.

This module provides validation functions for retry parameters to ensure
they meet the required constraints before being used in HTTP request
retry logic.
"""

from __future__ import annotations

__all__ = ["validate_retry_params"]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx


def validate_retry_params(
    max_retries: int,
    backoff_factor: float,
    jitter_factor: float = 0.0,
    timeout: float | httpx.Timeout | None = None,
) -> None:
    """Validate retry parameters.

    Args:
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0. A value of 0 means no retries (only the initial attempt).
        backoff_factor: Factor for exponential backoff between retries.
            Must be >= 0.
        jitter_factor: Factor for adding random jitter to backoff delays.
            Must be >= 0. Recommended value is 0.1 for 10% jitter.
        timeout: Maximum seconds to wait for the server response.
            Must be > 0 if provided as a numeric value.

    Raises:
        ValueError: If max_retries, backoff_factor, or jitter_factor are negative,
            or if timeout is non-positive.

    Example:
        ```pycon
        >>> from aresilient.utils import validate_retry_params
        >>> validate_retry_params(max_retries=3, backoff_factor=0.5)
        >>> validate_retry_params(max_retries=3, backoff_factor=0.5, jitter_factor=0.1)
        >>> validate_retry_params(max_retries=3, backoff_factor=0.5, timeout=10.0)
        >>> validate_retry_params(max_retries=-1, backoff_factor=0.5)  # doctest: +SKIP

        ```
    """
    if max_retries < 0:
        msg = f"max_retries must be >= 0, got {max_retries}"
        raise ValueError(msg)
    if backoff_factor < 0:
        msg = f"backoff_factor must be >= 0, got {backoff_factor}"
        raise ValueError(msg)
    if jitter_factor < 0:
        msg = f"jitter_factor must be >= 0, got {jitter_factor}"
        raise ValueError(msg)
    if timeout is not None and isinstance(timeout, (int, float)) and timeout <= 0:
        msg = f"timeout must be > 0, got {timeout}"
        raise ValueError(msg)
