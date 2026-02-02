r"""Backoff strategy implementations for retry delays.

This module provides various backoff strategies for calculating retry delays,
including exponential, linear, Fibonacci, and constant backoff patterns.
"""

from __future__ import annotations

__all__ = [
    "BackoffStrategy",
    "ConstantBackoff",
    "ExponentialBackoff",
    "FibonacciBackoff",
    "LinearBackoff",
]

from abc import ABC, abstractmethod


class BackoffStrategy(ABC):
    """Abstract base class for backoff strategies.

    A backoff strategy determines how long to wait before retrying a failed
    request based on the attempt number and other parameters.
    """

    @abstractmethod
    def calculate(self, attempt: int) -> float:
        """Calculate the backoff delay for a given retry attempt.

        Args:
            attempt: The current attempt number (0-indexed). For example,
                attempt=0 is the first retry, attempt=1 is the second retry, etc.

        Returns:
            The calculated delay in seconds before the next retry attempt.
        """


class ExponentialBackoff(BackoffStrategy):
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
        >>> from aresilient.utils.backoff_strategy import ExponentialBackoff
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
        """Initialize exponential backoff strategy.

        Args:
            base_delay: The base delay factor (default: 0.3).
            max_delay: Optional maximum delay cap in seconds.

        Raises:
            ValueError: If base_delay is negative or max_delay is non-positive.
        """
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
            The calculated delay: base_delay * (2 ** attempt), capped at max_delay if set.
        """
        delay = self.base_delay * (2 ** attempt)
        if self.max_delay is not None:
            delay = min(delay, self.max_delay)
        return delay


class LinearBackoff(BackoffStrategy):
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
        >>> from aresilient.utils.backoff_strategy import LinearBackoff
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
        """Initialize linear backoff strategy.

        Args:
            base_delay: The base delay in seconds (default: 1.0).
            max_delay: Optional maximum delay cap in seconds.

        Raises:
            ValueError: If base_delay is negative or max_delay is non-positive.
        """
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
            The calculated delay: base_delay * (attempt + 1), capped at max_delay if set.
        """
        delay = self.base_delay * (attempt + 1)
        if self.max_delay is not None:
            delay = min(delay, self.max_delay)
        return delay


class FibonacciBackoff(BackoffStrategy):
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
        >>> from aresilient.utils.backoff_strategy import FibonacciBackoff
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
        """Initialize Fibonacci backoff strategy.

        Args:
            base_delay: The base delay in seconds (default: 1.0).
            max_delay: Optional maximum delay cap in seconds.

        Raises:
            ValueError: If base_delay is negative or max_delay is non-positive.
        """
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
            The calculated delay: base_delay * fibonacci(attempt + 1), capped at max_delay if set.
        """
        fib_number = self._fibonacci(attempt + 1)
        delay = self.base_delay * fib_number
        if self.max_delay is not None:
            delay = min(delay, self.max_delay)
        return delay


class ConstantBackoff(BackoffStrategy):
    """Constant/fixed backoff strategy.

    Returns the same delay for every retry attempt, regardless of the attempt number.

    This strategy is useful for testing or when you know the exact delay that works
    best for a particular service.

    Args:
        delay: The fixed delay in seconds to use for all retry attempts (default: 1.0).

    Example:
        ```pycon
        >>> from aresilient.utils.backoff_strategy import ConstantBackoff
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
        """Initialize constant backoff strategy.

        Args:
            delay: The fixed delay in seconds (default: 1.0).

        Raises:
            ValueError: If delay is negative.
        """
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
