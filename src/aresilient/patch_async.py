r"""Contains asynchronous HTTP PATCH request with automatic retry
logic."""

from __future__ import annotations

__all__ = ["patch_async"]

from typing import TYPE_CHECKING, Any

from aresilient.core.config import (
    DEFAULT_TIMEOUT,
    ClientConfig,
)
from aresilient.core.http_logic import execute_http_method_async

if TYPE_CHECKING:
    import httpx


async def patch_async(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    config: ClientConfig | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> httpx.Response:
    r"""Send an HTTP PATCH request asynchronously with automatic retry
    logic for transient errors.

    This function performs an HTTP PATCH request with a configured retry
    policy for transient server errors (429, 500, 502, 503, 504). It applies
    a backoff retry strategy (exponential by default). The function validates
    the HTTP response and raises detailed errors for failures.

    Args:
        url: The URL to send the PATCH request to.
        client: An optional httpx.AsyncClient object to use for making
            requests. If None, a new client will be created and closed
            after use.
        config: An optional ClientConfig object with retry configuration.
            If None, default ClientConfig values are used.
        timeout: Maximum seconds to wait for the server response.
            Only used if client is None. Must be > 0.
        **kwargs: Additional keyword arguments passed to
            ``httpx.AsyncClient.patch()``.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries, or if max_total_time is
            exceeded.
        ValueError: If timeout is non-positive.

    Example:
        ```pycon
        >>> import asyncio
        >>> from aresilient import patch_async
        >>> from aresilient.core import ClientConfig
        >>> config = ClientConfig(max_retries=5)
        >>> async def example():
        ...     response = await patch_async("https://api.example.com/data", config=config)
        ...     return response.status_code
        ...
        >>> asyncio.run(example())  # doctest: +SKIP

        ```
    """
    return await execute_http_method_async(
        url=url,
        method="PATCH",
        client=client,
        config=config,
        timeout=timeout,
        **kwargs,
    )
