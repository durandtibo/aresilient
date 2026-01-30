r"""Contain synchronous HTTP DELETE request with automatic retry
logic."""

from __future__ import annotations

__all__ = ["delete_with_automatic_retry"]

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

from aresnet.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)
from aresnet.request import request_with_automatic_retry
from aresnet.utils import http_method_with_retry_wrapper


def delete_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
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
            Only used if client is None.
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. The wait
            time is calculated as: {backoff_factor} * (2 ** retry_number) seconds.
            Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        **kwargs: Additional keyword arguments passed to ``httpx.Client.delete()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries.
        ValueError: If max_retries or backoff_factor are negative.

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
    return http_method_with_retry_wrapper(
        url=url,
        method="DELETE",
        client_method_name="delete",
        request_with_retry=request_with_automatic_retry,
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )
