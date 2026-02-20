r"""Abstract base class for backoff strategies."""

from __future__ import annotations

__all__ = ["BaseBackoffStrategy"]

from abc import ABC, abstractmethod


class BaseBackoffStrategy(ABC):
    """Abstract base class for backoff strategies.

    A backoff strategy determines how long to wait before retrying a
    failed request based on the attempt number and other parameters.
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
