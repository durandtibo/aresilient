r"""Default configurations for HTTP requests with automatic retry logic.

This module defines the default configuration constants used throughout the
aresnet library for HTTP request retry behavior, timeouts, and error handling.
These constants provide sensible defaults for most use cases but can be
overridden when calling the HTTP request functions.
"""

from __future__ import annotations

__all__ = ["DEFAULT_BACKOFF_FACTOR", "DEFAULT_MAX_RETRIES", "DEFAULT_TIMEOUT", "RETRY_STATUS_CODES"]

# Default timeout in seconds for HTTP requests
# This is a reasonable default for most API calls
DEFAULT_TIMEOUT = 10.0

# Default maximum number of retry attempts
# Total attempts = max_retries + 1 (initial attempt)
DEFAULT_MAX_RETRIES = 3

# Default backoff factor for exponential backoff
# Wait time = backoff_factor * (2 ** retry_number)
# With 0.3: 1st retry waits 0.3s, 2nd waits 0.6s, 3rd waits 1.2s
DEFAULT_BACKOFF_FACTOR = 0.3

# HTTP status codes that should trigger automatic retry
# 429: Too Many Requests - Rate limiting
# 500: Internal Server Error - Temporary server issue
# 502: Bad Gateway - Upstream server error
# 503: Service Unavailable - Server overloaded or down
# 504: Gateway Timeout - Upstream server timeout
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
