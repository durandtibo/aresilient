r"""Synchronous context manager client for resilient HTTP requests.

This module provides a context manager-based client for making multiple
HTTP requests with shared retry configuration. The ResilientClient
automatically manages the underlying httpx.Client lifecycle and provides
convenient methods for all HTTP operations with automatic retry logic.
"""

from __future__ import annotations

__all__ = ["ResilientClient"]

from typing import TYPE_CHECKING, Any

import httpx

from aresilient.core.config import (
    DEFAULT_TIMEOUT,
    ClientConfig,
)
from aresilient.request import request

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Self


class ResilientClient:
    r"""Synchronous context manager for resilient HTTP requests.

    This class provides a context manager interface for making multiple HTTP
    requests with shared retry configuration. The client automatically manages
    the lifecycle of the underlying httpx.Client and applies consistent retry
    logic across all requests.

    Args:
        config: Optional ClientConfig instance for retry configuration.
            If ``None``, a default ClientConfig is used.
        client: Optional httpx.Client instance to use for requests.
            If ``None``, a new client is created with the default timeout.

    Example:
        ```pycon
        >>> from aresilient import ResilientClient
        >>> from aresilient.core.config import ClientConfig
        >>> with ResilientClient(
        ...     config=ClientConfig(max_retries=5)
        ... ) as client:  # doctest: +SKIP
        ...     response1 = client.get("https://api.example.com/data1")
        ...     response2 = client.post("https://api.example.com/data2", json={"key": "value"})
        ...
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
        client: httpx.Client | None = None,
    ) -> None:
        self._config = config or ClientConfig()
        self._owns_client = client is None
        self._client: httpx.Client | None = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
        self._entered = False

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            The ResilientClient instance for making requests.
        """
        self._entered = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager and close the underlying httpx
        client.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        if self._client is not None and self._owns_client:
            self._client.close()
            self._client = None
        self._entered = False

    def _ensure_client(self) -> httpx.Client:
        """Ensure the client is available for use.

        Returns:
            The httpx.Client instance.

        Raises:
            RuntimeError: If the client is used outside of a context manager.
        """
        if not self._entered or self._client is None:
            msg = "ResilientClient must be used within a context manager (with statement)"
            raise RuntimeError(msg)
        return self._client

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP request with automatic retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, etc.).
            url: The URL to send the request to.
            **kwargs: Additional keyword arguments passed to httpx.Client.request().

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Raises:
            RuntimeError: If called outside of a context manager.
            HttpRequestError: If the request fails after all retries.

        Example:
            ```pycon
            >>> from aresilient import ResilientClient
            >>> with ResilientClient() as client:  # doctest: +SKIP
            ...     response = client.request("GET", "https://api.example.com/data")
            ...

            ```
        """
        client = self._ensure_client()

        return request(
            url=url,
            method=method,
            request_func=getattr(client, method.lower()),
            config=self._config,
            **kwargs,
        )

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP GET request with automatic retry logic.

        Args:
            url: The URL to send the GET request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> from aresilient import ResilientClient
            >>> with ResilientClient() as client:  # doctest: +SKIP
            ...     response = client.get("https://api.example.com/data")
            ...

            ```
        """
        return self.request(method="GET", url=url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP POST request with automatic retry logic.

        Args:
            url: The URL to send the POST request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> from aresilient import ResilientClient
            >>> with ResilientClient() as client:  # doctest: +SKIP
            ...     response = client.post("https://api.example.com/data", json={"key": "value"})
            ...

            ```
        """
        return self.request(method="POST", url=url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP PUT request with automatic retry logic.

        Args:
            url: The URL to send the PUT request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> from aresilient import ResilientClient
            >>> with ResilientClient() as client:  # doctest: +SKIP
            ...     response = client.put("https://api.example.com/data", json={"key": "value"})
            ...

            ```
        """
        return self.request(method="PUT", url=url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP DELETE request with automatic retry logic.

        Args:
            url: The URL to send the DELETE request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> from aresilient import ResilientClient
            >>> with ResilientClient() as client:  # doctest: +SKIP
            ...     response = client.delete("https://api.example.com/data")
            ...

            ```
        """
        return self.request(method="DELETE", url=url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP PATCH request with automatic retry logic.

        Args:
            url: The URL to send the PATCH request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> from aresilient import ResilientClient
            >>> with ResilientClient() as client:  # doctest: +SKIP
            ...     response = client.patch("https://api.example.com/data", json={"key": "value"})
            ...

            ```
        """
        return self.request(method="PATCH", url=url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP HEAD request with automatic retry logic.

        Args:
            url: The URL to send the HEAD request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> from aresilient import ResilientClient
            >>> with ResilientClient() as client:  # doctest: +SKIP
            ...     response = client.head("https://api.example.com/data")
            ...

            ```
        """
        return self.request(method="HEAD", url=url, **kwargs)

    def options(self, url: str, **kwargs: Any) -> httpx.Response:
        r"""Send an HTTP OPTIONS request with automatic retry logic.

        Args:
            url: The URL to send the OPTIONS request to.
            **kwargs: Additional keyword arguments (see request() method).

        Returns:
            An httpx.Response object containing the server's HTTP response.

        Example:
            ```pycon
            >>> from aresilient import ResilientClient
            >>> with ResilientClient() as client:  # doctest: +SKIP
            ...     response = client.options("https://api.example.com/data")
            ...

            ```
        """
        return self.request(method="OPTIONS", url=url, **kwargs)
