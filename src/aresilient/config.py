r"""Default configurations for HTTP requests with automatic retry logic.

This module re-exports default configuration constants from
aresilient.core.config for backward compatibility. New code should
import from aresilient.core.config.
"""

from __future__ import annotations

__all__ = ["DEFAULT_BACKOFF_FACTOR", "DEFAULT_MAX_RETRIES", "DEFAULT_TIMEOUT", "RETRY_STATUS_CODES"]

from aresilient.core.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
