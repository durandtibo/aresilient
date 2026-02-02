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
    """Executes async HTTP requests with automatic retry logic."""

    def __init__(
        self,
        retry_config: RetryConfig,
        callback_config: CallbackConfig,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize async retry executor.

        Args:
            retry_config: Retry configuration.
            callback_config: Callback configuration.
            circuit_breaker: Optional circuit breaker.
        """
        self.config = retry_config
        self.strategy = RetryStrategy(
            retry_config.backoff_factor,
            retry_config.jitter_factor,
            retry_config.backoff_strategy,
            retry_config.max_wait_time,
        )
        self.decider = RetryDecider(
            retry_config.status_forcelist,
            retry_config.retry_if,
        )
        self.callbacks = CallbackManager(callback_config)
        self.circuit_breaker = circuit_breaker

    async def execute(
        self,
        url: str,
        method: str,
        request_func: Callable[..., httpx.Response],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute async request with retry logic.

        Args:
            url: The URL to request.
            method: The HTTP method.
            request_func: Async function to make the request.
            **kwargs: Additional arguments for request_func.

        Returns:
            The successful HTTP response.

        Raises:
            HttpRequestError: If all retries are exhausted or circuit breaker is open.
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
