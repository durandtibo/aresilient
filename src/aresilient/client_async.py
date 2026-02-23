r"""Asynchronous context manager client for resilient HTTP requests.

This module provides an async context manager-based client for making
multiple HTTP requests with shared retry configuration. The
AsyncResilientClient automatically manages the underlying
httpx.AsyncClient lifecycle and provides convenient methods for all HTTP
operations with automatic retry logic.
"""

from __future__ import annotations

__all__ = ["AsyncResilientClient"]

from typing import TYPE_CHECKING, Any

import httpx

from aresilient.core.config import (
    DEFAULT_TIMEOUT,
    ClientConfig,
)
from aresilient.request_async import request_async

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Self


class AsyncResilientClient:
    r"""Asynchronous context manager for resilient HTTP requests.

    This class provides an async context manager interface for making multiple HTTP
    requests with shared retry configuration. The client automatically manages
    the lifecycle of the underlying httpx.AsyncClient and applies consistent retry
    logic across all requests.

    Two usage patterns are supported:

    **Scenario 1 – Two context managers (external lifecycle management)**:
    The ``httpx.AsyncClient`` is created and managed by an outer ``async with``
    block, and passed into ``AsyncResilientClient``. ``AsyncResilientClient``
    does *not* close the underlying client when it exits, leaving full control
    to the caller. Use this pattern when you need to share a single
    ``httpx.AsyncClient`` across multiple ``AsyncResilientClient`` instances,
    or when you need to configure the client with headers, auth, proxies, etc.
    and want explicit lifecycle control.

    .. code-block:: python

        import httpx
        from aresilient import AsyncResilientClient
        from aresilient.core.config import ClientConfig

        async with httpx.AsyncClient(headers={"Authorization": "Bearer token"}) as http_client:
            async with AsyncResilientClient(
                client=http_client, config=ClientConfig(max_retries=5)
            ) as client:
                response = await client.get("https://api.example.com/data1")
        # http_client is closed here by the outer ``async with`` block

    **Scenario 2 – Single context manager (AsyncResilientClient manages lifecycle)**:
    An ``httpx.AsyncClient`` instance is passed inline (or omitted, in which
    case a default client is created). ``AsyncResilientClient`` enters and
    closes the underlying client automatically when the ``async with`` block
    exits. Use this pattern for the simplest usage when you don't need to
    reuse the ``httpx.AsyncClient`` outside the ``async with`` block.

    .. code-block:: python

        import httpx
        from aresilient import AsyncResilientClient
        from aresilient.core.config import ClientConfig

        async with AsyncResilientClient(
            client=httpx.AsyncClient(), config=ClientConfig(max_retries=5)
        ) as client:
            response = await client.get("https://api.example.com/data1")
        # httpx.AsyncClient is closed here by AsyncResilientClient

        # Equivalent shorthand (AsyncResilientClient creates a default client):
        async with AsyncResilientClient(config=ClientConfig(max_retries=5)) as client:
            response = await client.get("https://api.example.com/data1")

    Args:
        config: Optional ClientConfig instance for retry configuration.
            If ``None``, a default ClientConfig is used.
        client: Optional httpx.AsyncClient instance to use for requests.
            If ``None``, a new client is created with the default timeout.

    Example:
        ```pycon
        >>> import asyncio
        >>> from aresilient import AsyncResilientClient
        >>> from aresilient.core.config import ClientConfig
        >>> async def main():  # doctest: +SKIP
        ...     async with AsyncResilientClient(config=ClientConfig(max_retries=5)) as client:
        ...         response1 = await client.get("https://api.example.com/data1")
        ...         response2 = await client.post(
        ...             "https://api.example.com/data2", json={"key": "value"}
        ...         )
        ...
        >>> asyncio.run(main())  # doctest: +SKIP
        # Client automatically closed after context exits

        ```

    Note:
        All HTTP method calls (get, post, put, delete, patch, head, options, request)
        use the resilience parameters defined in the ``config`` passed to the constructor.
    """

    def __init__(
        self,
        *,
        config: ClientConfig | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config or ClientConfig()
        self._client: httpx.AsyncClient = client or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        self._close_client = False

    async def __aenter__(self) -> Self:
        """Enter the async context manager.

        If the underlying ``httpx.AsyncClient`` is not yet open, it is
        entered and its lifecycle is managed by this context manager (closed
        on exit). If the client is already open (e.g. managed by an outer
        ``async with`` block), ``AsyncResilientClient`` uses it without
        closing it on exit.

        Returns:
            The AsyncResilientClient instance for making requests.
        """
        if self._client.is_closed:
            await self._client.__aenter__()
            self._close_client = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager and close the underlying httpx
        client if this context manager opened it.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        if self._close_client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._close_client = False

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP request with automatic retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, etc.).
            url: The URL to send the request to.
            **kwargs: Additional keyword arguments passed to httpx.AsyncClient.request().

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Raises:
            HttpRequestError: If the request fails after all retries.

        Example:
            ```pycon
            >>> import asyncio
            >>> from aresilient import AsyncResilientClient
            >>> async def main():  # doctest: +SKIP
            ...     async with AsyncResilientClient() as client:
            ...         response = await client.request("GET", "https://api.example.com/data")
            ...
            >>> asyncio.run(main())  # doctest: +SKIP

            ```
        """
        return await request_async(
            url=url,
            method=method,
            request_func=getattr(self._client, method.lower()),
            config=self._config,
            **kwargs,
        )

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP GET request with automatic retry logic.

        Args:
            url: The URL to send the GET request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> import asyncio
            >>> from aresilient import AsyncResilientClient
            >>> async def main():  # doctest: +SKIP
            ...     async with AsyncResilientClient() as client:
            ...         response = await client.get("https://api.example.com/data")
            ...
            >>> asyncio.run(main())  # doctest: +SKIP

            ```
        """
        return await self.request(method="GET", url=url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP POST request with automatic retry logic.

        Args:
            url: The URL to send the POST request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> import asyncio
            >>> from aresilient import AsyncResilientClient
            >>> async def main():  # doctest: +SKIP
            ...     async with AsyncResilientClient() as client:
            ...         response = await client.post(
            ...             "https://api.example.com/data", json={"key": "value"}
            ...         )
            ...
            >>> asyncio.run(main())  # doctest: +SKIP

            ```
        """
        return await self.request(method="POST", url=url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP PUT request with automatic retry logic.

        Args:
            url: The URL to send the PUT request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> import asyncio
            >>> from aresilient import AsyncResilientClient
            >>> async def main():  # doctest: +SKIP
            ...     async with AsyncResilientClient() as client:
            ...         response = await client.put(
            ...             "https://api.example.com/data", json={"key": "value"}
            ...         )
            ...
            >>> asyncio.run(main())  # doctest: +SKIP

            ```
        """
        return await self.request(method="PUT", url=url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP DELETE request with automatic retry logic.

        Args:
            url: The URL to send the DELETE request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> import asyncio
            >>> from aresilient import AsyncResilientClient
            >>> async def main():  # doctest: +SKIP
            ...     async with AsyncResilientClient() as client:
            ...         response = await client.delete("https://api.example.com/data")
            ...
            >>> asyncio.run(main())  # doctest: +SKIP

            ```
        """
        return await self.request(method="DELETE", url=url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP PATCH request with automatic retry logic.

        Args:
            url: The URL to send the PATCH request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> import asyncio
            >>> from aresilient import AsyncResilientClient
            >>> async def main():  # doctest: +SKIP
            ...     async with AsyncResilientClient() as client:
            ...         response = await client.patch(
            ...             "https://api.example.com/data", json={"key": "value"}
            ...         )
            ...
            >>> asyncio.run(main())  # doctest: +SKIP

            ```
        """
        return await self.request(method="PATCH", url=url, **kwargs)

    async def head(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP HEAD request with automatic retry logic.

        Args:
            url: The URL to send the HEAD request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> import asyncio
            >>> from aresilient import AsyncResilientClient
            >>> async def main():  # doctest: +SKIP
            ...     async with AsyncResilientClient() as client:
            ...         response = await client.head("https://api.example.com/data")
            ...
            >>> asyncio.run(main())  # doctest: +SKIP

            ```
        """
        return await self.request(method="HEAD", url=url, **kwargs)

    async def options(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP OPTIONS request with automatic retry logic.

        Args:
            url: The URL to send the OPTIONS request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> import asyncio
            >>> from aresilient import AsyncResilientClient
            >>> async def main():  # doctest: +SKIP
            ...     async with AsyncResilientClient() as client:
            ...         response = await client.options("https://api.example.com/data")
            ...
            >>> asyncio.run(main())  # doctest: +SKIP

            ```
        """
        return await self.request(method="OPTIONS", url=url, **kwargs)
