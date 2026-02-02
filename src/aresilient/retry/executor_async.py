r"""Asynchronous retry executor for HTTP requests.

This module provides the AsyncRetryExecutor class that executes async
HTTP requests with automatic retry logic and circuit breaker
integration.
"""

from __future__ import annotations

__all__ = ["AsyncRetryExecutor"]

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

import httpx

from aresilient.exceptions import HttpRequestError
from aresilient.retry.decider import RetryDecider
from aresilient.retry.manager import CallbackManager
from aresilient.retry.strategy import RetryStrategy
from aresilient.utils.exceptions import raise_final_error

if TYPE_CHECKING:
    from collections.abc import Callable

    from aresilient.circuit_breaker import CircuitBreaker
    from aresilient.retry.config import CallbackConfig, RetryConfig

logger: logging.Logger = logging.getLogger(__name__)


class AsyncRetryExecutor:
    """Executes async HTTP requests with automatic retry logic.

    This class implements the core retry loop for asynchronous HTTP requests,
    handling retryable errors, managing callbacks, and coordinating with
    circuit breakers. It uses composition with strategy objects for better
    separation of concerns.

    The executor orchestrates the following components:
    - RetryStrategy: Calculates backoff delays between retries
    - RetryDecider: Determines whether to retry based on responses/exceptions
    - CallbackManager: Invokes user-defined callbacks at lifecycle events
    - CircuitBreaker: Optional fail-fast protection against cascading failures

    Attributes:
        config: Retry configuration containing max retries, backoff settings, etc.
        strategy: Strategy for calculating retry delays.
        decider: Logic for deciding whether to retry.
        callbacks: Manager for invoking callbacks.
        circuit_breaker: Optional circuit breaker for fail-fast behavior.

    Example:
        ```pycon
        >>> import asyncio
        >>> import httpx
        >>> from aresilient.retry import AsyncRetryExecutor, RetryConfig, CallbackConfig
        >>>
        >>> async def main():
        ...     retry_config = RetryConfig(
        ...         max_retries=3,
        ...         backoff_factor=0.5,
        ...         status_forcelist=(500, 502, 503),
        ...         jitter_factor=0.1,
        ...     )
        ...     callback_config = CallbackConfig()
        ...     executor = AsyncRetryExecutor(retry_config, callback_config)
        ...     async with httpx.AsyncClient() as client:
        ...         response = await executor.execute(
        ...             url="https://api.example.com/data",
        ...             method="GET",
        ...             request_func=client.get,
        ...         )
        ...     return response
        ...
        >>>
        >>> asyncio.run(main())  # doctest: +SKIP

        ```
    """

    def __init__(
        self,
        retry_config: RetryConfig,
        callback_config: CallbackConfig,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize async retry executor.

        Creates the executor with the provided configuration and initializes
        the internal strategy, decider, and callback manager components.

        Args:
            retry_config: Configuration for retry behavior including max retries,
                backoff settings, status codes to retry, and time limits.
            callback_config: Configuration for lifecycle callbacks (on_request,
                on_retry, on_success, on_failure).
            circuit_breaker: Optional circuit breaker for fail-fast protection.
                When provided, the executor will check the circuit breaker before
                each request and record successes/failures.
        """
        self.config = retry_config
        self.strategy: RetryStrategy = RetryStrategy(
            retry_config.backoff_factor,
            retry_config.jitter_factor,
            retry_config.backoff_strategy,
            retry_config.max_wait_time,
        )
        self.decider: RetryDecider = RetryDecider(
            retry_config.status_forcelist,
            retry_config.retry_if,
        )
        self.callbacks: CallbackManager = CallbackManager(callback_config)
        self.circuit_breaker = circuit_breaker

    async def execute(
        self,
        url: str,
        method: str,
        request_func: Callable[..., httpx.Response],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute async request with automatic retry logic.

        Attempts the HTTP request up to max_retries + 1 times (initial attempt
        plus retries), waiting progressively longer between attempts using the
        configured backoff strategy.

        The retry loop handles:
        - Successful responses (status < 400): Returns immediately
        - Retryable status codes (e.g., 500, 502, 503): Retries with backoff
        - Non-retryable status codes (e.g., 404): Raises immediately
        - Timeout exceptions (httpx.TimeoutException): Retries with backoff
        - Network errors (httpx.RequestError): Retries with backoff
        - Custom retry predicates: Uses user-defined logic for retry decisions

        Circuit breaker integration:
        - Checks breaker before starting (fails fast if OPEN)
        - Records failures for retryable errors
        - Records success on completion

        Time limits:
        - max_total_time: Stops retrying if total elapsed time exceeds limit
        - max_wait_time: Caps individual backoff delays

        Note:
            This method uses asyncio.sleep() for backoff delays, allowing other
            tasks to run during retry waits. Callbacks are invoked synchronously
            but should be fast operations.

        Args:
            url: The URL to request.
            method: The HTTP method name (e.g., "GET", "POST"). Used for logging.
            request_func: Async function to make the HTTP request. Should accept
                url as first parameter and return httpx.Response.
            **kwargs: Additional keyword arguments passed to request_func.

        Returns:
            The successful HTTP response (status < 400 or custom retry_if
            predicate returns False for successful response).

        Raises:
            HttpRequestError: If all retries are exhausted, a non-retryable
                status code is encountered, max_total_time is exceeded, or
                the circuit breaker is open.
            CircuitBreakerError: If the circuit breaker is in OPEN state.

        Example:
            ```pycon
            >>> import asyncio
            >>> import httpx
            >>> from aresilient.retry import AsyncRetryExecutor, RetryConfig, CallbackConfig
            >>>
            >>> async def main():
            ...     retry_config = RetryConfig(
            ...         max_retries=2,
            ...         backoff_factor=0.3,
            ...         status_forcelist=(500, 502, 503),
            ...         jitter_factor=0.0,
            ...     )
            ...     executor = AsyncRetryExecutor(retry_config, CallbackConfig())
            ...     async with httpx.AsyncClient() as client:
            ...         response = await executor.execute(
            ...             url="https://api.example.com/data",
            ...             method="GET",
            ...             request_func=client.get,
            ...             timeout=10.0,
            ...         )
            ...     return response
            ...
            >>>
            >>> asyncio.run(main())  # doctest: +SKIP

            ```
        """
        # Check circuit breaker before starting
        if self.circuit_breaker is not None:
            self.circuit_breaker.check()

        start_time = time.time()
        last_error: Exception | None = None
        last_status_code: int | None = None
        response: httpx.Response | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                # Attempt request
                self.callbacks.on_request(url, method, attempt, self.config.max_retries)
                response = await request_func(url=url, **kwargs)

                # Evaluate response
                should_retry, reason = self.decider.should_retry_response(
                    response, attempt, self.config.max_retries, url, method
                )

                if not should_retry:
                    # Success!
                    if self.circuit_breaker is not None:
                        self.circuit_breaker.record_success()
                    self.callbacks.on_success(
                        url,
                        method,
                        attempt,
                        self.config.max_retries,
                        response,
                        start_time,
                    )
                    return response

                # Mark for retry - record circuit breaker failure
                last_status_code = response.status_code
                if self.circuit_breaker is not None:
                    error = HttpRequestError(
                        method=method,
                        url=url,
                        message=f"{method} request to {url} failed with status {response.status_code}",
                        status_code=response.status_code,
                        response=response,
                    )
                    self.circuit_breaker.record_failure(error)
                logger.debug(f"{method} to {url}: will retry ({reason})")

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc

                # Evaluate exception
                should_retry, reason = self.decider.should_retry_exception(
                    exc, attempt, self.config.max_retries
                )

                if not should_retry:
                    # Create and raise error immediately
                    if isinstance(exc, httpx.TimeoutException):
                        error = HttpRequestError(
                            method=method,
                            url=url,
                            message=f"{method} request to {url} timed out ({attempt + 1} attempts)",
                            cause=exc,
                        )
                    else:
                        error = HttpRequestError(
                            method=method,
                            url=url,
                            message=f"{method} request to {url} failed after {attempt + 1} attempts: {exc}",
                            cause=exc,
                        )
                    self.callbacks.on_failure(
                        url,
                        method,
                        attempt,
                        self.config.max_retries,
                        error,
                        None,
                        start_time,
                    )
                    raise error from exc

                # Record circuit breaker failure for retryable exception
                if self.circuit_breaker is not None:
                    self.circuit_breaker.record_failure(exc)
                logger.debug(f"{method} to {url}: will retry ({reason})")

            # Sleep before retry (if not last attempt)
            if attempt < self.config.max_retries:
                # Check max_total_time BEFORE sleeping
                if self.config.max_total_time is not None:
                    elapsed_time = time.time() - start_time
                    if elapsed_time >= self.config.max_total_time:
                        # Time budget exceeded - raise error immediately
                        if response is not None:
                            raise_final_error(
                                url=url,
                                method=method,
                                max_retries=self.config.max_retries,
                                response=response,
                                on_failure=self.callbacks.callbacks.on_failure,
                                start_time=start_time,
                            )
                        else:
                            # We have an exception but no response
                            error = HttpRequestError(
                                method=method,
                                url=url,
                                message=(
                                    f"{method} request to {url} failed after {attempt + 1} attempts "
                                    f"(max_total_time exceeded)"
                                ),
                            )
                            self.callbacks.on_failure(
                                url,
                                method,
                                attempt,
                                self.config.max_retries,
                                error,
                                None,
                                start_time,
                            )
                            raise error

                sleep_time = self.strategy.calculate_delay(attempt, response)
                self.callbacks.on_retry(
                    url,
                    method,
                    attempt,
                    self.config.max_retries,
                    sleep_time,
                    last_error,
                    last_status_code,
                )
                await asyncio.sleep(sleep_time)

        # All retries exhausted
        raise_final_error(
            url=url,
            method=method,
            max_retries=self.config.max_retries,
            response=response,
            on_failure=self.callbacks.callbacks.on_failure,
            start_time=start_time,
        )
        return None
