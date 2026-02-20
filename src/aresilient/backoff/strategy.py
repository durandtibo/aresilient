r"""Backoff strategy implementations for retry delays.

This module re-exports all backoff strategies for backward compatibility.
The implementations have been moved to separate modules:

- ``aresilient.backoff.base``: ``BaseBackoffStrategy``
- ``aresilient.backoff.exponential``: ``ExponentialBackoff``
- ``aresilient.backoff.linear``: ``LinearBackoff``
- ``aresilient.backoff.fibonacci``: ``FibonacciBackoff``
- ``aresilient.backoff.constant``: ``ConstantBackoff``
"""

from __future__ import annotations

__all__ = [
    "BackoffStrategy",
    "BaseBackoffStrategy",
    "ConstantBackoff",
    "ExponentialBackoff",
    "FibonacciBackoff",
    "LinearBackoff",
]

from aresilient.backoff.base import BaseBackoffStrategy
from aresilient.backoff.constant import ConstantBackoff
from aresilient.backoff.exponential import ExponentialBackoff
from aresilient.backoff.fibonacci import FibonacciBackoff
from aresilient.backoff.linear import LinearBackoff

# Backward compatibility alias
BackoffStrategy = BaseBackoffStrategy
