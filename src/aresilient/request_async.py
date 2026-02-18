r"""Contains utility functions for asynchronous HTTP requests with
automatic retry logic."""

from __future__ import annotations

__all__ = ["request_async"]

from typing import TYPE_CHECKING, Any

from aresilient.core.config import ClientConfig
from aresilient.retry import (
    AsyncRetryExecutor,
    CallbackConfig,
    RetryConfig,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import httpx


async def request_async(
    url: str,
    method: str,
    request_func: Callable[..., Awaitable[httpx.Response]],
    *,
    config: ClientConfig | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """Perform an async HTTP request with automatic retry logic.

    This function implements a retry mechanism with exponential backoff for
    handling transient HTTP errors. It attempts the request up to max_retries + 1
    times, waiting progressively longer between each retry.

    The retry logic handles three types of failures:
    1. Retryable HTTP status codes (e.g., 429, 500, 502, 503, 504)
    2. Timeout exceptions (httpx.TimeoutException)
    3. General network errors (httpx.RequestError)

    Backoff Strategy:
    - Default: Exponential backoff: backoff_factor * (2 ** attempt)
    - Custom: Use backoff_strategy parameter for alternative strategies
      (Linear, Fibonacci, Constant, or custom implementations)
    - Jitter: Optional randomization added to prevent thundering herd
    - Retry-After header: If present in the response (429/503), the server's
      suggested wait time is used instead of backoff calculation

    Args:
        url: The URL to send the request to.
        method: The HTTP method name (e.g., "GET", "POST") for logging.
        request_func: The async function to call to make the request (e.g.,
            client.get, client.post).
        config: An optional ClientConfig object with retry configuration.
            If None, default ClientConfig values are used.
        **kwargs: Additional keyword arguments passed to the request function.

    Returns:
        An httpx.Response object containing the server's HTTP response.

    Raises:
        HttpRequestError: If the request times out, encounters network errors,
            or fails after exhausting all retries, or if max_total_time is exceeded.

    Example:
        ```pycon
        >>> import asyncio
        >>> import httpx
        >>> from aresilient import request_async
        >>> from aresilient.backoff import LinearBackoff
        >>> from aresilient.core import ClientConfig
        >>> def log_retry(info):
        ...     print(f"Retry {info.attempt}/{info.max_retries + 1}")
        ...
        >>> config = ClientConfig(
        ...     max_retries=5,
        ...     backoff_strategy=LinearBackoff(base_delay=1.0),
        ...     jitter_factor=0.1,
        ...     max_total_time=30.0,
        ...     max_wait_time=5.0,
        ...     on_retry=log_retry,
        ... )
        >>> async def example():
        ...     async with httpx.AsyncClient() as client:
        ...         response = await request_async(
        ...             url="https://api.example.com/data",
        ...             method="GET",
        ...             request_func=client.get,
        ...             config=config,
        ...         )
        ...         return response.status_code
        ...
        >>> asyncio.run(example())  # doctest: +SKIP

        ```
    """
    config = config or ClientConfig()

    # Create retry configuration
    retry_config = RetryConfig(
        max_retries=config.max_retries,
        backoff_factor=config.backoff_factor,
        status_forcelist=config.status_forcelist,
        jitter_factor=config.jitter_factor,
        retry_if=config.retry_if,
        backoff_strategy=config.backoff_strategy,
        max_total_time=config.max_total_time,
        max_wait_time=config.max_wait_time,
    )

    # Create callback configuration
    callback_config = CallbackConfig(
        on_request=config.on_request,
        on_retry=config.on_retry,
        on_success=config.on_success,
        on_failure=config.on_failure,
    )

    # Create executor and execute request
    executor = AsyncRetryExecutor(retry_config, callback_config, config.circuit_breaker)
    return await executor.execute(url, method, request_func, **kwargs)
