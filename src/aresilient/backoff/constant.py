r"""Constant backoff strategy."""

from __future__ import annotations

__all__ = ["ConstantBackoff"]

from aresilient.backoff.base import BaseBackoffStrategy


class ConstantBackoff(BaseBackoffStrategy):
    """Constant/fixed backoff strategy.

    Returns the same delay for every retry attempt, regardless of the attempt number.

    This strategy is useful for testing or when you know the exact delay that works
    best for a particular service.

    Args:
        delay: The fixed delay in seconds to use for all retry attempts (default: 1.0).

    Example:
        ```pycon
        >>> from aresilient.backoff import ConstantBackoff
        >>> backoff = ConstantBackoff(delay=2.5)
        >>> backoff.calculate(0)  # First retry
        2.5
        >>> backoff.calculate(1)  # Second retry
        2.5
        >>> backoff.calculate(10)  # Tenth retry
        2.5

        ```
    """

    def __init__(self, delay: float = 1.0) -> None:
        if delay < 0:
            msg = f"delay must be non-negative, got {delay}"
            raise ValueError(msg)

        self.delay = delay

    def calculate(self, attempt: int) -> float:  # noqa: ARG002
        """Calculate constant backoff delay.

        Args:
            attempt: The current attempt number (0-indexed, unused).

        Returns:
            The fixed delay value.
        """
        return self.delay
