r"""Fibonacci backoff strategy."""

from __future__ import annotations

__all__ = ["FibonacciBackoff"]

from aresilient.backoff.base import BaseBackoffStrategy


class FibonacciBackoff(BaseBackoffStrategy):
    """Fibonacci backoff strategy.

    Calculates delay as: base_delay * fibonacci(attempt + 1), with optional max_delay cap.

    This strategy provides a middle ground between linear and exponential backoff,
    starting slow and ramping up gradually. The Fibonacci sequence (1, 1, 2, 3, 5, 8, 13, ...)
    provides a more gradual increase than exponential backoff.

    Args:
        base_delay: The base delay in seconds (default: 1.0). The actual delay
            is calculated as base_delay * fibonacci(attempt + 1).
        max_delay: Optional maximum delay cap in seconds. If specified,
            delays will not exceed this value.

    Example:
        ```pycon
        >>> from aresilient.backoff import FibonacciBackoff
        >>> backoff = FibonacciBackoff(base_delay=1.0)
        >>> backoff.calculate(0)  # First retry: 1.0 * fib(1) = 1.0
        1.0
        >>> backoff.calculate(1)  # Second retry: 1.0 * fib(2) = 1.0
        1.0
        >>> backoff.calculate(2)  # Third retry: 1.0 * fib(3) = 2.0
        2.0
        >>> backoff.calculate(3)  # Fourth retry: 1.0 * fib(4) = 3.0
        3.0
        >>> backoff.calculate(4)  # Fifth retry: 1.0 * fib(5) = 5.0
        5.0
        >>> # With max_delay cap
        >>> backoff = FibonacciBackoff(base_delay=1.0, max_delay=10.0)
        >>> backoff.calculate(10)  # fib(11) = 89, would be 89.0, but capped
        10.0

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

    @staticmethod
    def _fibonacci(n: int) -> int:
        """Calculate the nth Fibonacci number (1-indexed).

        Args:
            n: The position in the Fibonacci sequence (1-indexed).

        Returns:
            The nth Fibonacci number.
        """
        if n <= 0:
            return 0
        if n <= 2:
            return 1

        # Iterative approach for efficiency
        a, b = 1, 1
        for _ in range(n - 2):
            a, b = b, a + b
        return b

    def calculate(self, attempt: int) -> float:
        """Calculate Fibonacci backoff delay.

        Args:
            attempt: The current attempt number (0-indexed).

        Returns:
            The calculated delay: base_delay * fibonacci(attempt + 1),
            capped at max_delay if set.
        """
        fib_number = self._fibonacci(attempt + 1)
        delay = self.base_delay * fib_number
        if self.max_delay is not None:
            delay = min(delay, self.max_delay)
        return delay
