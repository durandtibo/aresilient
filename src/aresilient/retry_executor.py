r"""Retry executor implementing class-based composition pattern.

This module implements the retry logic using a class-based composition
pattern with strategy objects for improved maintainability and
testability.
"""

from __future__ import annotations

__all__ = [
    "AsyncRetryExecutor",
    "CallbackConfig",
    "CallbackManager",
    "RetryConfig",
    "RetryDecider",
    "RetryExecutor",
    "RetryStrategy",
]

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from aresilient.backoff.sleep import calculate_sleep_time
from aresilient.callbacks import FailureInfo
from aresilient.exceptions import HttpRequestError
from aresilient.utils.callbacks import (
    invoke_on_request,
    invoke_on_retry,
    invoke_on_success,
)
from aresilient.utils.exceptions import raise_final_error

if TYPE_CHECKING:
    from collections.abc import Callable

    from aresilient.backoff.strategy import BackoffStrategy
    from aresilient.circuit_breaker import CircuitBreaker

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Factor for exponential backoff.
        status_forcelist: Tuple of HTTP status codes that trigger retries.
        jitter_factor: Factor for adding random jitter to backoff delays.
        retry_if: Optional custom predicate to determine retry behavior.
        backoff_strategy: Optional custom backoff strategy.
        max_total_time: Optional maximum total time budget for all retries.
        max_wait_time: Optional maximum backoff delay cap.
    """

    max_retries: int
    backoff_factor: float
    status_forcelist: tuple[int, ...]
    jitter_factor: float
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None = None
    backoff_strategy: BackoffStrategy | None = None
    max_total_time: float | None = None
    max_wait_time: float | None = None


@dataclass
class CallbackConfig:
    """Configuration for callbacks.

    Attributes:
        on_request: Optional callback invoked before each request attempt.
        on_retry: Optional callback invoked before each retry.
        on_success: Optional callback invoked when request succeeds.
        on_failure: Optional callback invoked when all retries are exhausted.
    """

    on_request: Callable | None = None
    on_retry: Callable | None = None
    on_success: Callable | None = None
    on_failure: Callable | None = None


class RetryStrategy:
    """Strategy for calculating retry delays."""

    def __init__(
        self,
        backoff_factor: float,
        jitter_factor: float,
        backoff_strategy: BackoffStrategy | None = None,
        max_wait_time: float | None = None,
    ) -> None:
        """Initialize retry strategy.

        Args:
            backoff_factor: Factor for exponential backoff.
            jitter_factor: Factor for adding random jitter.
            backoff_strategy: Optional custom backoff strategy.
            max_wait_time: Optional maximum backoff delay cap.
        """
        self.backoff_factor = backoff_factor
        self.jitter_factor = jitter_factor
        self.backoff_strategy = backoff_strategy
        self.max_wait_time = max_wait_time

    def calculate_delay(
        self,
        attempt: int,
        response: httpx.Response | None = None,
    ) -> float:
        """Calculate delay before next retry.

        Args:
            attempt: Current attempt number (0-indexed).
            response: Optional HTTP response for Retry-After header.

        Returns:
            Sleep time in seconds.
        """
        return calculate_sleep_time(
            attempt,
            self.backoff_factor,
            self.jitter_factor,
            response,
            self.backoff_strategy,
            self.max_wait_time,
        )


class RetryDecider:
    """Decides whether a request should be retried."""

    def __init__(
        self,
        status_forcelist: tuple[int, ...],
        retry_if: Callable | None,
    ) -> None:
        """Initialize retry decider.

        Args:
            status_forcelist: Tuple of retryable HTTP status codes.
            retry_if: Optional custom retry predicate.
        """
        self.status_forcelist = status_forcelist
        self.retry_if = retry_if

    def should_retry_response(
        self,
        response: httpx.Response,
        attempt: int,
        max_retries: int,
        url: str,
        method: str,
    ) -> tuple[bool, str]:
        """Determine if response should trigger retry.

        Args:
            response: The HTTP response to evaluate.
            attempt: Current attempt number (0-indexed).
            max_retries: Maximum number of retries.
            url: The URL being requested.
            method: The HTTP method being used.

        Returns:
            Tuple of (should_retry, reason).

        Raises:
            HttpRequestError: For non-retryable error responses.
        """
        # Success case (status < 400)
        if response.status_code < 400:
            if self.retry_if is not None and self.retry_if(response, None):
                return (True, "retry_if predicate")
            return (False, "success")

        # Error case (status >= 400)
        if self.retry_if is not None:
            should_retry = self.retry_if(response, None)
            if not should_retry:
                # retry_if returned False for an error response
                logger.debug(
                    f"{method} request to {url} failed with status {response.status_code} "
                    f"(retry_if returned False)"
                )
                raise HttpRequestError(
                    method=method,
                    url=url,
                    message=f"{method} request to {url} failed with status {response.status_code}",
                    status_code=response.status_code,
                    response=response,
                )
            return (should_retry, "retry_if predicate")

        # Check status_forcelist
        is_retryable = response.status_code in self.status_forcelist
        if not is_retryable:
            # Non-retryable status code
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
        return (is_retryable, f"status {response.status_code}")

    def should_retry_exception(
        self,
        exception: Exception,
        attempt: int,
        max_retries: int,
    ) -> tuple[bool, str]:
        """Determine if exception should trigger retry.

        Args:
            exception: The exception to evaluate.
            attempt: Current attempt number (0-indexed).
            max_retries: Maximum number of retries.

        Returns:
            Tuple of (should_retry, reason).
        """
        if self.retry_if is not None:
            should_retry = self.retry_if(None, exception)
            if not should_retry or attempt >= max_retries:
                return (False, "retry_if returned False or max retries")
            return (True, "retry_if predicate")

        # Default: retry timeout and request errors
        if attempt >= max_retries:
            return (False, "max retries exhausted")
        return (True, f"{type(exception).__name__}")


class CallbackManager:
    """Manages callback invocations."""

    def __init__(self, callbacks: CallbackConfig) -> None:
        """Initialize callback manager.

        Args:
            callbacks: Callback configuration.
        """
        self.callbacks = callbacks

    def on_request(self, url: str, method: str, attempt: int, max_retries: int) -> None:
        """Invoke on_request callback.

        Args:
            url: The URL being requested.
            method: The HTTP method.
            attempt: Current attempt number (0-indexed).
            max_retries: Maximum number of retries.
        """
        if self.callbacks.on_request:
            invoke_on_request(
                self.callbacks.on_request,
                url=url,
                method=method,
                attempt=attempt,
                max_retries=max_retries,
            )

    def on_retry(
        self,
        url: str,
        method: str,
        attempt: int,
        max_retries: int,
        sleep_time: float,
        error: Exception | None,
        status_code: int | None,
    ) -> None:
        """Invoke on_retry callback.

        Args:
            url: The URL being requested.
            method: The HTTP method.
            attempt: Current attempt number (0-indexed).
            max_retries: Maximum number of retries.
            sleep_time: Sleep time before retry.
            error: Exception that triggered retry (if any).
            status_code: Status code that triggered retry (if any).
        """
        if self.callbacks.on_retry:
            invoke_on_retry(
                self.callbacks.on_retry,
                url=url,
                method=method,
                attempt=attempt,
                max_retries=max_retries,
                sleep_time=sleep_time,
                last_error=error,
                last_status_code=status_code,
            )

    def on_success(
        self,
        url: str,
        method: str,
        attempt: int,
        max_retries: int,
        response: httpx.Response,
        start_time: float,
    ) -> None:
        """Invoke on_success callback.

        Args:
            url: The URL that was requested.
            method: The HTTP method.
            attempt: Attempt number that succeeded (0-indexed).
            max_retries: Maximum number of retries.
            response: The successful response.
            start_time: Timestamp when request started.
        """
        if self.callbacks.on_success:
            invoke_on_success(
                self.callbacks.on_success,
                url=url,
                method=method,
                attempt=attempt,
                max_retries=max_retries,
                response=response,
                start_time=start_time,
            )

    def on_failure(
        self,
        url: str,
        method: str,
        attempt: int,
        max_retries: int,
        error: Exception,
        status_code: int | None,
        start_time: float,
    ) -> None:
        """Invoke on_failure callback.

        Args:
            url: The URL that was requested.
            method: The HTTP method.
            attempt: Final attempt number (0-indexed).
            max_retries: Maximum number of retries.
            error: The error that caused failure.
            status_code: Status code if available.
            start_time: Timestamp when request started.
        """
        if self.callbacks.on_failure:
            failure_info: FailureInfo = FailureInfo(
                url=url,
                method=method,
                attempt=attempt + 1,
                max_retries=max_retries,
                error=error,
                status_code=status_code,
                total_time=time.time() - start_time,
            )
            self.callbacks.on_failure(failure_info)


class RetryExecutor:
    """Executes HTTP requests with automatic retry logic."""

    def __init__(
        self,
        retry_config: RetryConfig,
        callback_config: CallbackConfig,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize retry executor.

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

    def execute(
        self,
        url: str,
        method: str,
        request_func: Callable[..., httpx.Response],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request with retry logic.

        Args:
            url: The URL to request.
            method: The HTTP method.
            request_func: Function to make the request.
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
                response = request_func(url=url, **kwargs)

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
                time.sleep(sleep_time)

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
