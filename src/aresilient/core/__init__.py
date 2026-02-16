r"""Core shared logic for sync and async HTTP operations.

This module contains shared functionality used by both synchronous and
asynchronous HTTP request implementations, including validation, retry
logic, and HTTP method handling.
"""

from __future__ import annotations

__all__ = ["validate_retry_params"]

from aresilient.core.validation import validate_retry_params
