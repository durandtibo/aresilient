r"""Exponential backoff strategy."""

from __future__ import annotations

__all__ = ["ExponentialBackoff"]

from aresilient.backoff.base import BaseBackoffStrategy


class ExponentialBackoff(BaseBackoffStrategy):
    """Exponential backoff strategy.

    Calculates delay as: base_delay * (2 ** attempt), with optional max_delay cap.

    This is the default backoff strategy and works well for most scenarios where
    you want progressively longer delays between retries.

    Args:
        base_delay: The base delay factor (default: 0.3). The actual delay
            is calculated as base_delay * (2 ** attempt).
        max_delay: Optional maximum delay cap in seconds. If specified,
            delays will not exceed this value.

    Example:
        ```pycon
        >>> from aresilient.backoff import ExponentialBackoff
        >>> backoff = ExponentialBackoff(base_delay=0.3)
        >>> backoff.calculate(0)  # First retry
        0.3
        >>> backoff.calculate(1)  # Second retry
        0.6
        >>> backoff.calculate(2)  # Third retry
        1.2
        >>> # With max_delay cap
        >>> backoff = ExponentialBackoff(base_delay=1.0, max_delay=5.0)
        >>> backoff.calculate(10)  # Would be 1024.0, but capped
        5.0

        ```
    """

    def __init__(self, base_delay: float = 0.3, max_delay: float | None = None) -> None:
        if base_delay < 0:
            msg = f"base_delay must be non-negative, got {base_delay}"
            raise ValueError(msg)
        if max_delay is not None and max_delay <= 0:
            msg = f"max_delay must be positive if specified, got {max_delay}"
            raise ValueError(msg)

        self.base_delay = base_delay
        self.max_delay = max_delay

    def calculate(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: The current attempt number (0-indexed).

        Returns:
            The calculated delay: base_delay * (2 ** attempt),
            capped at max_delay if set.
        """
        delay = self.base_delay * (2**attempt)
        if self.max_delay is not None:
            delay = min(delay, self.max_delay)
        return delay
