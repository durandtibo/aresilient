r"""HTTP response handling utilities.

This module provides functions for handling HTTP responses and
determining whether they should be retried based on status codes.
"""

from __future__ import annotations

__all__ = ["handle_response"]

import logging
from typing import TYPE_CHECKING

from aresilient.exceptions import HttpRequestError

if TYPE_CHECKING:
    import httpx

logger: logging.Logger = logging.getLogger(__name__)


def handle_response(
    response: httpx.Response,
    url: str,
    method: str,
    status_forcelist: tuple[int, ...],
) -> None:
    """Handle HTTP response and raise error for non-retryable status
    codes.

    This function checks the HTTP response status code and raises an error if
    the status code is not in the retryable status list. This allows the retry
    logic to distinguish between transient errors (e.g., 503 Service Unavailable)
    that should be retried and permanent errors (e.g., 404 Not Found) that should
    fail immediately.

    Args:
        response: The HTTP response object to validate.
        url: The URL that was requested, used in error messages.
        method: The HTTP method name (e.g., "GET", "POST"), used in error messages.
        status_forcelist: Tuple of HTTP status codes that are considered
            retryable (e.g., (429, 500, 502, 503, 504)). If the response status
            code is not in this tuple, an error is raised.

    Raises:
        HttpRequestError: If the response status code is not in status_forcelist,
            indicating a non-retryable error (e.g., 404, 401, 403).

    Note:
        This is an internal utility function. If the response status code is in
        status_forcelist, the function returns without raising an error, allowing
        the retry loop to continue.
    """
    # Non-retryable HTTP error (e.g., 404, 401, 403)
    if response.status_code not in status_forcelist:
        logger.debug(
            f"{method} request to {url} failed with non-retryable status {response.status_code}"
        )
        raise HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} failed with status {response.status_code}",
            status_code=response.status_code,
            response=response,
        )
