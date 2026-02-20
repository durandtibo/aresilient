r"""Backoff strategies and utilities for retry delays.

This package provides various backoff strategies for calculating retry
delays, including exponential, linear, Fibonacci, and constant backoff
patterns.
"""

from __future__ import annotations

__all__ = [
    "BackoffStrategy",
    "ConstantBackoff",
    "ExponentialBackoff",
    "FibonacciBackoff",
    "LinearBackoff",
]

from aresilient.backoff.strategy import (
    BackoffStrategy,
    ConstantBackoff,
    ExponentialBackoff,
    FibonacciBackoff,
    LinearBackoff,
)
