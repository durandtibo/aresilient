r"""Class-based retry executor implementation for HTTP requests.

This module provides a clean, modular implementation of retry logic using
composition and single-responsibility classes. It separates concerns for
configuration, retry strategy, retry decision-making, callback management,
and request execution.

The design uses Approach 5 from the design document, implementing:
- RetryConfig: Configuration for retry behavior
- CallbackConfig: Configuration for lifecycle callbacks
- RetryStrategy: Backoff and sleep time calculation
- RetryDecider: Retry decision logic for responses and exceptions
- CallbackManager: Callback invocation management
- RetryExecutor: Synchronous request execution with retries
- AsyncRetryExecutor: Asynchronous request execution with retries
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

from aresilient.callbacks import FailureInfo
from aresilient.exceptions import HttpRequestError
from aresilient.utils.backoff import calculate_sleep_time
from aresilient.utils.callbacks import (
    invoke_on_request,
    invoke_on_retry,
    invoke_on_success,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Factor for exponential backoff between retries.
        status_forcelist: Tuple of HTTP status codes that should trigger retry.
        jitter_factor: Factor for adding random jitter to backoff delays.
        retry_if: Custom predicate to determine if a response/exception should
            be retried. Takes (response, exception) and returns bool.
    """

    max_retries: int
    backoff_factor: float
    status_forcelist: tuple[int, ...]
    jitter_factor: float
    retry_if: Callable[[httpx.Response | None, Exception | None], bool]


@dataclass
class CallbackConfig:
    """Configuration for lifecycle callbacks.

    Attributes:
        on_request: Callback invoked before each request attempt.
        on_retry: Callback invoked before each retry.
        on_success: Callback invoked when request succeeds.
        on_failure: Callback invoked when all retries are exhausted.
    """

    on_request: Callable[[object], None] | None
    on_retry: Callable[[object], None] | None
    on_success: Callable[[object], None] | None
    on_failure: Callable[[object], None] | None


class RetryStrategy:
    """Strategy for calculating retry delays.

    This class encapsulates the logic for determining how long to wait
    before retrying a failed request, using exponential backoff with
    optional jitter and Retry-After header support.
    """

    def __init__(self, backoff_factor: float, jitter_factor: float) -> None:
        """Initialize retry strategy.

        Args:
            backoff_factor: Factor for exponential backoff between retries.
            jitter_factor: Factor for adding random jitter to backoff delays.
        """
        self.backoff_factor = backoff_factor
        self.jitter_factor = jitter_factor

    def get_sleep_time(
        self, attempt: int, response: httpx.Response | None
    ) -> float:
        """Calculate sleep time for the given attempt.

        Args:
            attempt: Current attempt number (0-indexed).
            response: HTTP response object (if available).

        Returns:
            Sleep time in seconds.
        """
        return calculate_sleep_time(
            attempt=attempt,
            backoff_factor=self.backoff_factor,
            jitter_factor=self.jitter_factor,
            response=response,
        )


class RetryDecider:
    """Decider for retry logic based on responses and exceptions.

    This class determines whether a failed request should be retried
    based on the retry configuration and the type of failure.
    """

    def __init__(
        self,
        status_forcelist: tuple[int, ...],
        retry_if: Callable[[httpx.Response | None, Exception | None], bool],
    ) -> None:
        """Initialize retry decider.

        Args:
            status_forcelist: Tuple of HTTP status codes that should trigger retry.
            retry_if: Custom predicate to determine if retry should occur.
        """
        self.status_forcelist = status_forcelist
        self.retry_if = retry_if

    def should_retry_response(  # noqa: PLR0911
        self, response: httpx.Response, attempt: int, max_retries: int
    ) -> tuple[bool, str]:
        """Determine if a response should trigger a retry.

        Args:
            response: HTTP response object.
            attempt: Current attempt number (0-indexed).
            max_retries: Maximum number of retry attempts.

        Returns:
            Tuple of (should_retry, reason).
        """
        # Check max retries first
        if attempt >= max_retries:
            return (False, "max retries reached")

        # Success case: HTTP status code < 400
        if response.status_code < 400:
            # Check retry_if predicate - might want to retry even on success
            if self.retry_if(response, None):
                return (True, "retry_if predicate returned True for success")
            return (False, "success response")

        # Error case: status >= 400
        # Check if status is in forcelist
        if response.status_code in self.status_forcelist:
            # Check retry_if predicate
            if self.retry_if(response, None):
                return (True, f"status {response.status_code} in forcelist")
            return (False, "retry_if predicate returned False")

        # Status not in forcelist, check retry_if
        if self.retry_if(response, None):
            return (True, "retry_if predicate returned True")

        return (False, f"status {response.status_code} not retryable")

    def should_retry_exception(
        self, exception: Exception, attempt: int, max_retries: int
    ) -> tuple[bool, str]:
        """Determine if an exception should trigger a retry.

        Args:
            exception: Exception that occurred.
            attempt: Current attempt number (0-indexed).
            max_retries: Maximum number of retry attempts.

        Returns:
            Tuple of (should_retry, reason).
        """
        # Check max retries first
        if attempt >= max_retries:
            return (False, "max retries reached")

        # Check retry_if predicate
        if self.retry_if(None, exception):
            return (True, f"retry_if predicate returned True for {type(exception).__name__}")

        return (False, "retry_if predicate returned False")


class CallbackManager:
    """Manager for invoking lifecycle callbacks.

    This class handles the invocation of user-provided callbacks at
    various points in the request lifecycle.
    """

    def __init__(self, callback_config: CallbackConfig) -> None:
        """Initialize callback manager.

        Args:
            callback_config: Configuration for callbacks.
        """
        self.callback_config = callback_config

    def invoke_on_request(
        self, url: str, method: str, attempt: int, max_retries: int
    ) -> None:
        """Invoke on_request callback if provided."""
        invoke_on_request(
            self.callback_config.on_request,
            url=url,
            method=method,
            attempt=attempt,
            max_retries=max_retries,
        )

    def invoke_on_retry(
        self,
        url: str,
        method: str,
        attempt: int,
        max_retries: int,
        sleep_time: float,
        last_error: Exception | None,
        last_status_code: int | None,
    ) -> None:
        """Invoke on_retry callback if provided."""
        invoke_on_retry(
            self.callback_config.on_retry,
            url=url,
            method=method,
            attempt=attempt,
            max_retries=max_retries,
            sleep_time=sleep_time,
            last_error=last_error,
            last_status_code=last_status_code,
        )

    def invoke_on_success(
        self,
        url: str,
        method: str,
        attempt: int,
        max_retries: int,
        response: httpx.Response,
        start_time: float,
    ) -> None:
        """Invoke on_success callback if provided."""
        invoke_on_success(
            self.callback_config.on_success,
            url=url,
            method=method,
            attempt=attempt,
            max_retries=max_retries,
            response=response,
            start_time=start_time,
        )

    def invoke_on_failure(
        self,
        url: str,
        method: str,
        attempt: int,
        max_retries: int,
        error: Exception,
        status_code: int | None,
        start_time: float,
    ) -> None:
        """Invoke on_failure callback if provided."""
        if self.callback_config.on_failure is not None:
            failure_info = FailureInfo(
                url=url,
                method=method,
                attempt=attempt + 1,
                max_retries=max_retries,
                error=error,
                status_code=status_code,
                total_time=time.time() - start_time,
            )
            self.callback_config.on_failure(failure_info)


class RetryExecutor:
    """Synchronous retry executor for HTTP requests.

    This class orchestrates the retry logic for HTTP requests, using
    composition to delegate specific responsibilities to specialized
    components.
    """

    def __init__(
        self,
        retry_config: RetryConfig,
        callback_config: CallbackConfig,
    ) -> None:
        """Initialize retry executor.

        Args:
            retry_config: Configuration for retry behavior.
            callback_config: Configuration for callbacks.
        """
        self.retry_config = retry_config
        self.strategy = RetryStrategy(
            retry_config.backoff_factor, retry_config.jitter_factor
        )
        self.decider = RetryDecider(
            retry_config.status_forcelist, retry_config.retry_if
        )
        self.callbacks = CallbackManager(callback_config)

    def execute(
        self,
        client: httpx.Client,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute HTTP request with retry logic.

        Args:
            client: HTTPX client to use for requests.
            method: HTTP method (e.g., "GET", "POST").
            url: URL to request.
            **kwargs: Additional arguments to pass to client.request().

        Returns:
            The successful HTTP response.

        Raises:
            HttpRequestError: If all retries are exhausted or a non-retryable
                error occurs.
        """
        start_time = time.time()
        last_exception: Exception | None = None
        last_status_code: int | None = None

        for attempt in range(self.retry_config.max_retries + 1):
            # Invoke on_request callback
            self.callbacks.invoke_on_request(
                url=url,
                method=method,
                attempt=attempt,
                max_retries=self.retry_config.max_retries,
            )

            try:
                response = client.request(method=method, url=url, **kwargs)

                # Determine if we should retry based on the response
                should_retry, reason = self.decider.should_retry_response(
                    response, attempt, self.retry_config.max_retries
                )

                if not should_retry:
                    # Check if this is a non-retryable error (status >= 400)
                    if response.status_code >= 400:
                        logger.debug(
                            f"{method} request to {url} failed with status {response.status_code}, {reason}"
                        )
                        error = HttpRequestError(
                            method=method,
                            url=url,
                            message=f"{method} request to {url} failed with status {response.status_code}",
                            status_code=response.status_code,
                            response=response,
                        )
                        self.callbacks.invoke_on_failure(
                            url=url,
                            method=method,
                            attempt=attempt,
                            max_retries=self.retry_config.max_retries,
                            error=error,
                            status_code=response.status_code,
                            start_time=start_time,
                        )
                        raise error

                    # Success case (status < 400 and should not retry)
                    self.callbacks.invoke_on_success(
                        url=url,
                        method=method,
                        attempt=attempt,
                        max_retries=self.retry_config.max_retries,
                        response=response,
                        start_time=start_time,
                    )
                    return response

                # Should retry - calculate sleep time and continue
                last_status_code = response.status_code
                sleep_time = self.strategy.get_sleep_time(attempt, response)

                self.callbacks.invoke_on_retry(
                    url=url,
                    method=method,
                    attempt=attempt,
                    max_retries=self.retry_config.max_retries,
                    sleep_time=sleep_time,
                    last_error=None,
                    last_status_code=last_status_code,
                )

                time.sleep(sleep_time)

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_exception = exc
                last_status_code = None

                # Determine if we should retry based on the exception
                should_retry, reason = self.decider.should_retry_exception(
                    exc, attempt, self.retry_config.max_retries
                )

                if not should_retry:
                    # Create appropriate error
                    if isinstance(exc, httpx.TimeoutException):
                        logger.debug(
                            f"{method} request to {url} timed out, {reason}"
                        )
                        error = HttpRequestError(
                            method=method,
                            url=url,
                            message=f"{method} request to {url} timed out ({attempt + 1} attempts)",
                            cause=exc,
                        )
                    else:
                        error_type = type(exc).__name__
                        logger.debug(
                            f"{method} request to {url} encountered {error_type}, {reason}"
                        )
                        error = HttpRequestError(
                            method=method,
                            url=url,
                            message=f"{method} request to {url} failed after {attempt + 1} attempts: {exc}",
                            cause=exc,
                        )

                    self.callbacks.invoke_on_failure(
                        url=url,
                        method=method,
                        attempt=attempt,
                        max_retries=self.retry_config.max_retries,
                        error=error,
                        status_code=None,
                        start_time=start_time,
                    )
                    raise error from exc

                # Should retry - calculate sleep time and continue
                sleep_time = self.strategy.get_sleep_time(attempt, None)

                self.callbacks.invoke_on_retry(
                    url=url,
                    method=method,
                    attempt=attempt,
                    max_retries=self.retry_config.max_retries,
                    sleep_time=sleep_time,
                    last_error=exc,
                    last_status_code=None,
                )

                time.sleep(sleep_time)

        # Should never reach here, but handle it just in case
        if last_exception:
            error = HttpRequestError(
                method=method,
                url=url,
                message=f"{method} request to {url} failed after {self.retry_config.max_retries + 1} attempts",
                cause=last_exception,
            )
            raise error from last_exception
        raise HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} failed after {self.retry_config.max_retries + 1} attempts",
        )


class AsyncRetryExecutor:
    """Asynchronous retry executor for HTTP requests.

    This class provides the same retry logic as RetryExecutor but for
    asynchronous HTTP requests using async/await.
    """

    def __init__(
        self,
        retry_config: RetryConfig,
        callback_config: CallbackConfig,
    ) -> None:
        """Initialize async retry executor.

        Args:
            retry_config: Configuration for retry behavior.
            callback_config: Configuration for callbacks.
        """
        self.retry_config = retry_config
        self.strategy = RetryStrategy(
            retry_config.backoff_factor, retry_config.jitter_factor
        )
        self.decider = RetryDecider(
            retry_config.status_forcelist, retry_config.retry_if
        )
        self.callbacks = CallbackManager(callback_config)

    async def execute(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute HTTP request with retry logic asynchronously.

        Args:
            client: HTTPX async client to use for requests.
            method: HTTP method (e.g., "GET", "POST").
            url: URL to request.
            **kwargs: Additional arguments to pass to client.request().

        Returns:
            The successful HTTP response.

        Raises:
            HttpRequestError: If all retries are exhausted or a non-retryable
                error occurs.
        """
        start_time = time.time()
        last_exception: Exception | None = None
        last_status_code: int | None = None

        for attempt in range(self.retry_config.max_retries + 1):
            # Invoke on_request callback
            self.callbacks.invoke_on_request(
                url=url,
                method=method,
                attempt=attempt,
                max_retries=self.retry_config.max_retries,
            )

            try:
                response = await client.request(method=method, url=url, **kwargs)

                # Determine if we should retry based on the response
                should_retry, reason = self.decider.should_retry_response(
                    response, attempt, self.retry_config.max_retries
                )

                if not should_retry:
                    # Check if this is a non-retryable error (status >= 400)
                    if response.status_code >= 400:
                        logger.debug(
                            f"{method} request to {url} failed with status {response.status_code}, {reason}"
                        )
                        error = HttpRequestError(
                            method=method,
                            url=url,
                            message=f"{method} request to {url} failed with status {response.status_code}",
                            status_code=response.status_code,
                            response=response,
                        )
                        self.callbacks.invoke_on_failure(
                            url=url,
                            method=method,
                            attempt=attempt,
                            max_retries=self.retry_config.max_retries,
                            error=error,
                            status_code=response.status_code,
                            start_time=start_time,
                        )
                        raise error

                    # Success case (status < 400 and should not retry)
                    self.callbacks.invoke_on_success(
                        url=url,
                        method=method,
                        attempt=attempt,
                        max_retries=self.retry_config.max_retries,
                        response=response,
                        start_time=start_time,
                    )
                    return response

                # Should retry - calculate sleep time and continue
                last_status_code = response.status_code
                sleep_time = self.strategy.get_sleep_time(attempt, response)

                self.callbacks.invoke_on_retry(
                    url=url,
                    method=method,
                    attempt=attempt,
                    max_retries=self.retry_config.max_retries,
                    sleep_time=sleep_time,
                    last_error=None,
                    last_status_code=last_status_code,
                )

                await asyncio.sleep(sleep_time)

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_exception = exc
                last_status_code = None

                # Determine if we should retry based on the exception
                should_retry, reason = self.decider.should_retry_exception(
                    exc, attempt, self.retry_config.max_retries
                )

                if not should_retry:
                    # Create appropriate error
                    if isinstance(exc, httpx.TimeoutException):
                        logger.debug(
                            f"{method} request to {url} timed out, {reason}"
                        )
                        error = HttpRequestError(
                            method=method,
                            url=url,
                            message=f"{method} request to {url} timed out ({attempt + 1} attempts)",
                            cause=exc,
                        )
                    else:
                        error_type = type(exc).__name__
                        logger.debug(
                            f"{method} request to {url} encountered {error_type}, {reason}"
                        )
                        error = HttpRequestError(
                            method=method,
                            url=url,
                            message=f"{method} request to {url} failed after {attempt + 1} attempts: {exc}",
                            cause=exc,
                        )

                    self.callbacks.invoke_on_failure(
                        url=url,
                        method=method,
                        attempt=attempt,
                        max_retries=self.retry_config.max_retries,
                        error=error,
                        status_code=None,
                        start_time=start_time,
                    )
                    raise error from exc

                # Should retry - calculate sleep time and continue
                sleep_time = self.strategy.get_sleep_time(attempt, None)

                self.callbacks.invoke_on_retry(
                    url=url,
                    method=method,
                    attempt=attempt,
                    max_retries=self.retry_config.max_retries,
                    sleep_time=sleep_time,
                    last_error=exc,
                    last_status_code=None,
                )

                await asyncio.sleep(sleep_time)

        # Should never reach here, but handle it just in case
        if last_exception:
            error = HttpRequestError(
                method=method,
                url=url,
                message=f"{method} request to {url} failed after {self.retry_config.max_retries + 1} attempts",
                cause=last_exception,
            )
            raise error from last_exception
        raise HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} failed after {self.retry_config.max_retries + 1} attempts",
        )
