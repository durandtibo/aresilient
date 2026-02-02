r"""Retry package implementing class-based composition pattern.

This package provides a modular retry execution system using composition
and strategy patterns for improved maintainability and testability.

Public API:
    - RetryConfig: Configuration for retry behavior
    - CallbackConfig: Configuration for callbacks
    - RetryStrategy: Strategy for calculating retry delays
    - RetryDecider: Logic for deciding whether to retry
    - CallbackManager: Manager for callback invocations
    - RetryExecutor: Synchronous retry executor
    - AsyncRetryExecutor: Asynchronous retry executor
"""

from __future__ import annotations

__all__ = [
    "AsyncRetryExecutor",
    "CallbackConfig",
    "CallbackManager",
    "RetryConfig",
    "RetryDecider",
    "RetryExecutor",
    "RetryStrategy",
]

from aresilient.retry.config import CallbackConfig, RetryConfig
from aresilient.retry.decider import RetryDecider
from aresilient.retry.executor import RetryExecutor
from aresilient.retry.executor_async import AsyncRetryExecutor
from aresilient.retry.manager import CallbackManager
from aresilient.retry.strategy import RetryStrategy
