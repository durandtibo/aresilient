r"""Backoff strategies and utilities for retry delays.

This package provides various backoff strategies for calculating retry
delays, including exponential, linear, Fibonacci, and constant backoff
patterns.
"""

from __future__ import annotations

__all__ = [
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
