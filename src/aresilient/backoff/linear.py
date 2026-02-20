r"""Linear backoff strategy."""

from __future__ import annotations

__all__ = ["LinearBackoff"]

from aresilient.backoff.base import BaseBackoffStrategy


class LinearBackoff(BaseBackoffStrategy):
    """Linear backoff strategy.

    Calculates delay as: base_delay * (attempt + 1), with optional max_delay cap.

    This strategy provides evenly spaced retry delays, which can be useful for
    services that recover quickly or when you want predictable timing.

    Args:
        base_delay: The base delay in seconds (default: 1.0). The actual delay
            is calculated as base_delay * (attempt + 1).
        max_delay: Optional maximum delay cap in seconds. If specified,
            delays will not exceed this value.

    Example:
        ```pycon
        >>> from aresilient.backoff import LinearBackoff
        >>> backoff = LinearBackoff(base_delay=1.0)
        >>> backoff.calculate(0)  # First retry: 1.0 * 1
        1.0
        >>> backoff.calculate(1)  # Second retry: 1.0 * 2
        2.0
        >>> backoff.calculate(2)  # Third retry: 1.0 * 3
        3.0
        >>> # With max_delay cap
        >>> backoff = LinearBackoff(base_delay=2.0, max_delay=5.0)
        >>> backoff.calculate(5)  # Would be 12.0, but capped
        5.0

        ```
    """

    def __init__(self, base_delay: float = 1.0, max_delay: float | None = None) -> None:
        if base_delay < 0:
            msg = f"base_delay must be non-negative, got {base_delay}"
            raise ValueError(msg)
        if max_delay is not None and max_delay <= 0:
            msg = f"max_delay must be positive if specified, got {max_delay}"
            raise ValueError(msg)

        self.base_delay = base_delay
        self.max_delay = max_delay

    def calculate(self, attempt: int) -> float:
        """Calculate linear backoff delay.

        Args:
            attempt: The current attempt number (0-indexed).

        Returns:
            The calculated delay: base_delay * (attempt + 1),
            capped at max_delay if set.
        """
        delay = self.base_delay * (attempt + 1)
        if self.max_delay is not None:
            delay = min(delay, self.max_delay)
        return delay
