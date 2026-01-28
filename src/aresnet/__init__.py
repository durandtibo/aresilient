r"""Root package."""

from __future__ import annotations

__all__ = [
    "DEFAULT_BACKOFF_FACTOR",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "RETRY_STATUS_CODES",
    "HttpRequestError",
]

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresnet.exception import HttpRequestError
