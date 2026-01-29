r"""Root package."""

from __future__ import annotations

__all__ = [
    "DEFAULT_BACKOFF_FACTOR",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "RETRY_STATUS_CODES",
    "HttpRequestError",
    "__version__",
    "get_with_automatic_retry",
    "post_with_automatic_retry",
    "request_with_automatic_retry",
]

from importlib.metadata import PackageNotFoundError, version

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresnet.exception import HttpRequestError
from aresnet.get import get_with_automatic_retry
from aresnet.post import post_with_automatic_retry
from aresnet.request import request_with_automatic_retry

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    # Package is not installed, fallback if needed
    __version__ = "0.0.0"
