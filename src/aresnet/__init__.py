r"""Root package."""

from __future__ import annotations

__all__ = [
    "DEFAULT_BACKOFF_FACTOR",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "RETRY_STATUS_CODES",
    "HttpRequestError",
    "__version__",
    "delete_with_automatic_retry",
    "delete_with_automatic_retry_async",
    "get_with_automatic_retry",
    "get_with_automatic_retry_async",
    "patch_with_automatic_retry",
    "patch_with_automatic_retry_async",
    "post_with_automatic_retry",
    "post_with_automatic_retry_async",
    "put_with_automatic_retry",
    "put_with_automatic_retry_async",
    "request_with_automatic_retry",
    "request_with_automatic_retry_async",
]

from importlib.metadata import PackageNotFoundError, version

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresnet.exceptions import HttpRequestError
from aresnet.http import (
    delete_with_automatic_retry,
    delete_with_automatic_retry_async,
    get_with_automatic_retry,
    get_with_automatic_retry_async,
    patch_with_automatic_retry,
    patch_with_automatic_retry_async,
    post_with_automatic_retry,
    post_with_automatic_retry_async,
    put_with_automatic_retry,
    put_with_automatic_retry_async,
)
from aresnet.request import request_with_automatic_retry
from aresnet.request_async import request_with_automatic_retry_async

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    # Package is not installed, fallback if needed
    __version__ = "0.0.0"
