r"""Contain the default configurations for HTTP requests using the httpx
library."""

from __future__ import annotations

__all__ = ["DEFAULT_BACKOFF_FACTOR", "DEFAULT_MAX_RETRIES", "DEFAULT_TIMEOUT", "RETRY_STATUS_CODES"]

DEFAULT_TIMEOUT = 10.0

# Constants for retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.3
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
