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
from aresilient.core.validation import validate_timeout
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

    Args:
        config: Optional ClientConfig instance for retry configuration.
            If ``None``, a default ClientConfig is used.
        timeout: Maximum seconds to wait for server responses. Must be > 0.

    Example:
        ```pycon
        >>> import asyncio
        >>> from aresilient import AsyncResilientClient
        >>> from aresilient.core.config import ClientConfig
        >>> async def main():  # doctest: +SKIP
        ...     async with AsyncResilientClient(
        ...         config=ClientConfig(max_retries=5), timeout=30
        ...     ) as client:
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
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        # Validate timeout separately (used for httpx.AsyncClient creation, not retry logic)
        validate_timeout(timeout)

        # Store timeout separately (used for httpx.AsyncClient creation)
        self._timeout = timeout

        # Store retry configuration in ClientConfig dataclass
        self._config = config or ClientConfig()

        # Client will be created when entering context
        self._client: httpx.AsyncClient | None = None
        self._entered = False

    async def __aenter__(self) -> Self:
        """Enter the async context manager and create the underlying
        httpx client.

        Returns:
            The AsyncResilientClient instance for making requests.
        """
        self._client = httpx.AsyncClient(timeout=self._timeout)
        self._entered = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager and close the underlying httpx
        client.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._entered = False

    def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure the client is available for use.

        Returns:
            The httpx.AsyncClient instance.

        Raises:
            RuntimeError: If the client is used outside of a context manager.
        """
        if not self._entered or self._client is None:
            msg = "AsyncResilientClient must be used within an async context manager (async with statement)"
            raise RuntimeError(msg)
        return self._client

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        r"""Send an HTTP request with automatic retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, etc.).
            url: The URL to send the request to.
            **kwargs: Additional keyword arguments passed to httpx.AsyncClient.request().

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Raises:
            RuntimeError: If called outside of a context manager.
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
        client = self._ensure_client()

        return await request_async(
            url=url,
            method=method,
            request_func=getattr(client, method.lower()),
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
