r"""Contain synchronous HTTP DELETE request with automatic retry
logic."""

from __future__ import annotations

__all__ = ["delete_with_automatic_retry"]

from typing import Any

import httpx

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresnet.request import request_with_automatic_retry
from aresnet.utils import validate_retry_params


def delete_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    jitter_factor: float = 0.0,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP DELETE request with automatic retry logic for
    transient errors.

    This function performs an HTTP DELETE request with a configured retry policy
    for transient server errors (429, 500, 502, 503, 504). It applies an
    exponential backoff retry strategy. The function validates the HTTP
    response and raises detailed errors for failures.

    Args:
        url: The URL to send the DELETE request to.
        client: An optional httpx.Client object to use for making requests.
            If None, a new client will be created and closed after use.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None. Must be > 0.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: backoff_factor * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        jitter_factor: Factor for adding random jitter to backoff delays. The jitter
            is calculated as: random.uniform(0, jitter_factor) * base_sleep_time,
            and this jitter is ADDED to the base sleep time. Set to 0 to disable
            jitter (default). Recommended value is 0.1 for 10% jitter to prevent
            thundering herd issues. Must be >= 0.
        **kwargs: Additional keyword arguments passed to ``httpx.Client.delete()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries, backoff_factor, or jitter_factor are negative,
            or if timeout is non-positive.

    Example:
        ```pycon
        >>> from aresnet import delete_with_automatic_retry
        >>> response = delete_with_automatic_retry(
        ...     "https://api.example.com/resource/123"
        ... )  # doctest: +SKIP
        >>> response.status_code  # doctest: +SKIP
        204
        ```
    """
    # Input validation
    validate_retry_params(
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        jitter_factor=jitter_factor,
        timeout=timeout,
    )

    owns_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        return request_with_automatic_retry(
            url=url,
            method="DELETE",
            request_func=client.delete,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            jitter_factor=jitter_factor,
            **kwargs,
        )
    finally:
        if owns_client:
            client.close()
