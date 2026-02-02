r"""Retry executor implementation using class-based composition.

This module implements the retry execution logic using a class-based design
with strategy pattern, as described in Approach 5 of the design document.
It provides clean separation of concerns through:
- RetryStrategy: Calculates retry delays
- RetryDecider: Determines whether to retry
- CallbackManager: Manages callback invocations
- RetryExecutor: Orchestrates synchronous retry execution
- AsyncRetryExecutor: Orchestrates asynchronous retry execution
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
from aresilient.config import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    RETRY_STATUS_CODES,
)
from aresilient.exceptions import HttpRequestError
from aresilient.utils.callbacks import (
    invoke_on_request,
    invoke_on_retry,
    invoke_on_success,
)
from aresilient.utils.exceptions import raise_final_error

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from aresilient.backoff.strategy import BackoffStrategy
    from aresilient.callbacks import RequestInfo, ResponseInfo, RetryInfo
    from aresilient.circuit_breaker import CircuitBreaker

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Factor for exponential backoff between retries.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        jitter_factor: Factor for adding random jitter to backoff delays.
        retry_if: Optional custom predicate to determine retry.
        backoff_strategy: Optional custom backoff strategy.
        max_total_time: Optional maximum total time budget for all retries.
        max_wait_time: Optional maximum backoff delay cap.
        circuit_breaker: Optional circuit breaker for fail-fast behavior.
    """

    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES
    jitter_factor: float = 0.0
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None = None
    backoff_strategy: BackoffStrategy | None = None
    max_total_time: float | None = None
    max_wait_time: float | None = None
    circuit_breaker: CircuitBreaker | None = None


@dataclass
class CallbackConfig:
    """Configuration for callbacks.

    Attributes:
        on_request: Optional callback invoked before each request attempt.
        on_retry: Optional callback invoked before each retry.
        on_success: Optional callback invoked when request succeeds.
        on_failure: Optional callback invoked when all retries are exhausted.
    """

    on_request: Callable[[RequestInfo], None] | None = None
    on_retry: Callable[[RetryInfo], None] | None = None
    on_success: Callable[[ResponseInfo], None] | None = None
    on_failure: Callable[[FailureInfo], None] | None = None


class RetryStrategy:
    """Strategy for calculating retry delays.

    This class encapsulates the logic for calculating how long to wait
    before the next retry attempt.
    """

    def __init__(
        self,
        backoff_factor: float,
        jitter_factor: float,
        backoff_strategy: BackoffStrategy | None,
        max_wait_time: float | None,
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
            attempt: The current attempt number (0-indexed).
            response: Optional response object (for Retry-After header).

        Returns:
            The calculated delay in seconds.
        """
        return calculate_sleep_time(
            attempt,
            self.backoff_factor,
            self.jitter_factor,
            response,
            backoff_strategy=self.backoff_strategy,
            max_wait_time=self.max_wait_time,
        )


class RetryDecider:
    """Decides whether a request should be retried.

    This class encapsulates the logic for determining if a response or
    exception should trigger a retry.
    """

    def __init__(
        self,
        status_forcelist: tuple[int, ...],
        retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None,
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
        attempt: int,  # noqa: ARG002
        max_retries: int,  # noqa: ARG002
    ) -> tuple[bool, str]:
        """Determine if response should trigger retry.

        Args:
            response: The HTTP response object.
            attempt: The current attempt number (0-indexed).
            max_retries: Maximum number of retry attempts.

        Returns:
            Tuple of (should_retry, reason).

        Raises:
            HttpRequestError: If response has error status and should not be retried.
        """
        # Success case (status < 400)
        if response.status_code < 400:
            if self.retry_if is not None and self.retry_if(response, None):
                return (True, "retry_if predicate for success response")
            return (False, "success")

        # Error case (status >= 400)
        # If retry_if is provided, use it
        if self.retry_if is not None:
            should_retry = self.retry_if(response, None)
            if not should_retry:
                # retry_if returned False, raise error immediately
                # Note: method and url will be filled in by executor
                raise HttpRequestError(
                    method="",
                    url="",
                    message=f"failed with status {response.status_code} (retry_if returned False)",
                    status_code=response.status_code,
                    response=response,
                )
            return (True, "retry_if predicate for error response")

        # No retry_if, check status code
        if response.status_code not in self.status_forcelist:
            # Non-retryable status code
            # Note: method and url will be filled in by executor
            raise HttpRequestError(
                method="",
                url="",
                message=f"failed with status {response.status_code}",
                status_code=response.status_code,
                response=response,
            )

        # Retryable status code
        return (True, f"retryable status {response.status_code}")

    def should_retry_exception(
        self,
        exception: Exception,
        attempt: int,
        max_retries: int,
    ) -> tuple[bool, str]:
        """Determine if exception should trigger retry.

        Args:
            exception: The exception that occurred.
            attempt: The current attempt number (0-indexed).
            max_retries: Maximum number of retry attempts.

        Returns:
            Tuple of (should_retry, reason).

        Raises:
            HttpRequestError: If exception should not be retried.
        """
        # If retry_if is provided, use it
        if self.retry_if is not None:
            should_retry = self.retry_if(None, exception)
            if not should_retry or attempt >= max_retries:
                # retry_if returned False or max retries exhausted
                # Note: method and url will be filled in by executor
                if isinstance(exception, httpx.TimeoutException):
                    raise HttpRequestError(
                        method="",
                        url="",
                        message=f"timed out ({attempt + 1} attempts, retry_if returned False)",
                        cause=exception,
                    ) from exception
                raise HttpRequestError(
                    method="",
                    url="",
                    message=f"failed after {attempt + 1} attempts (retry_if returned False): {exception}",
                    cause=exception,
                ) from exception
            return (True, "retry_if predicate for exception")

        # No retry_if, check if we have retries left
        if attempt >= max_retries:
            # Max retries exhausted
            # Note: method and url will be filled in by executor
            if isinstance(exception, httpx.TimeoutException):
                raise HttpRequestError(
                    method="",
                    url="",
                    message=f"timed out ({max_retries + 1} attempts)",
                    cause=exception,
                ) from exception
            raise HttpRequestError(
                method="",
                url="",
                message=f"failed after {max_retries + 1} attempts: {exception}",
                cause=exception,
            ) from exception

        # Should retry
        return (True, f"{type(exception).__name__}")


class CallbackManager:
    """Manages callback invocations.

    This class encapsulates the logic for invoking callbacks at various
    points in the retry lifecycle.
    """

    def __init__(self, callbacks: CallbackConfig) -> None:
        """Initialize callback manager.

        Args:
            callbacks: Configuration for callbacks.
        """
        self.callbacks = callbacks

    def on_request(self, url: str, method: str, attempt: int, max_retries: int) -> None:
        """Invoke on_request callback.

        Args:
            url: The URL being requested.
            method: The HTTP method.
            attempt: The current attempt number (0-indexed).
            max_retries: Maximum number of retry attempts.
        """
        if self.callbacks.on_request is not None:
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
            attempt: The current attempt number (0-indexed).
            max_retries: Maximum number of retry attempts.
            sleep_time: The wait time before retry.
            error: The exception that triggered the retry (if any).
            status_code: The HTTP status code that triggered the retry (if any).
        """
        if self.callbacks.on_retry is not None:
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
            attempt: The attempt number that succeeded (0-indexed).
            max_retries: Maximum number of retry attempts.
            response: The successful HTTP response object.
            start_time: The timestamp when the request started.
        """
        if self.callbacks.on_success is not None:
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
            attempt: The final attempt number (0-indexed).
            max_retries: Maximum number of retry attempts.
            error: The final exception that caused the failure.
            status_code: The final HTTP status code (if any).
            start_time: The timestamp when the request started.
        """
        if self.callbacks.on_failure is not None:
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
    """Executes HTTP requests with automatic retry logic.

    This class orchestrates the retry execution process using the strategy,
    decider, and callback manager components.
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

    def _handle_response(
        self,
        response: httpx.Response,
        url: str,
        method: str,
        attempt: int,
        start_time: float,
    ) -> bool:
        """Handle response and determine if should retry.

        Args:
            response: The HTTP response object.
            url: The URL that was requested.
            method: The HTTP method.
            attempt: The current attempt number (0-indexed).
            start_time: The timestamp when the request started.

        Returns:
            True if should retry, False if successful.

        Raises:
            HttpRequestError: If non-retryable error.
        """
        try:
            should_retry, reason = self.decider.should_retry_response(
                response, attempt, self.config.max_retries
            )
        except HttpRequestError as err:
            # Non-retryable status code or retry_if returned False
            # Fill in url/method and update message
            err.url = url
            err.method = method
            if not err.args[0].startswith(f"{method} request to"):
                err.args = (f"{method} request to {url} {err.args[0]}",)

            if self.config.circuit_breaker is not None:
                self.config.circuit_breaker.record_failure(err)

            self.callbacks.on_failure(
                url,
                method,
                attempt,
                self.config.max_retries,
                err,
                response.status_code,
                start_time,
            )
            raise

        if not should_retry:
            # Success!
            if self.config.circuit_breaker is not None:
                self.config.circuit_breaker.record_success()
            self.callbacks.on_success(
                url,
                method,
                attempt,
                self.config.max_retries,
                response,
                start_time,
            )
            return False

        # Should retry
        logger.debug(f"{method} to {url}: will retry ({reason})")
        return True

    def _handle_exception(
        self,
        exc: Exception,
        url: str,
        method: str,
        attempt: int,
        start_time: float,
    ) -> tuple[bool, str]:
        """Handle exception and determine if should retry.

        Args:
            exc: The exception that occurred.
            url: The URL that was requested.
            method: The HTTP method.
            attempt: The current attempt number (0-indexed).
            start_time: The timestamp when the request started.

        Returns:
            Tuple of (should_retry, reason).

        Raises:
            HttpRequestError: If non-retryable error.
        """
        try:
            should_retry, reason = self.decider.should_retry_exception(
                exc, attempt, self.config.max_retries
            )
        except HttpRequestError as err:
            # Non-retryable exception or retry_if returned False or max retries
            # Fill in url/method and update message
            err.url = url
            err.method = method
            if not err.args[0].startswith(f"{method} request to"):
                err.args = (f"{method} request to {url} {err.args[0]}",)

            if self.config.circuit_breaker is not None:
                self.config.circuit_breaker.record_failure(err)

            self.callbacks.on_failure(
                url,
                method,
                attempt,
                self.config.max_retries,
                err,
                None,
                start_time,
            )
            raise

        return should_retry, reason

    def execute(
        self,
        url: str,
        method: str,
        request_func: Callable[..., httpx.Response],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request with retry logic.

        Args:
            url: The URL to send the request to.
            method: The HTTP method name (e.g., "GET", "POST").
            request_func: The function to call to make the request.
            **kwargs: Additional arguments to pass to request_func.

        Returns:
            The HTTP response object.

        Raises:
            HttpRequestError: If all retries are exhausted or non-retryable error.
            CircuitBreakerError: If circuit breaker is open.
        """
        start_time = time.time()
        last_error: Exception | None = None
        last_status_code: int | None = None
        response: httpx.Response | None = None

        for attempt in range(self.config.max_retries + 1):
            # Check max_total_time budget
            if self.config.max_total_time is not None and time.time() - start_time >= self.config.max_total_time:
                if response is not None:
                    raise_final_error(
                        url=url,
                        method=method,
                        max_retries=self.config.max_retries,
                        response=response,
                        on_failure=self.callbacks.callbacks.on_failure,
                        start_time=start_time,
                    )
                error = HttpRequestError(
                    method=method,
                    url=url,
                    message=f"{method} request to {url} exceeded time budget ({self.config.max_total_time:.1f}s)",
                )
                self.callbacks.on_failure(
                    url, method, attempt, self.config.max_retries, error, last_status_code, start_time
                )
                raise error

            # Check circuit breaker
            if self.config.circuit_breaker is not None:
                self.config.circuit_breaker.check()

            try:
                # Attempt request
                self.callbacks.on_request(url, method, attempt, self.config.max_retries)
                response = request_func(url=url, **kwargs)

                # Handle response
                if not self._handle_response(response, url, method, attempt, start_time):
                    return response

                # Mark for retry - this means the status was retryable
                last_status_code = response.status_code
                # Record circuit breaker failure for retryable errors
                if self.config.circuit_breaker is not None:
                    error = HttpRequestError(
                        method=method,
                        url=url,
                        message=f"{method} request to {url} failed with status {response.status_code}",
                        status_code=response.status_code,
                        response=response,
                    )
                    self.config.circuit_breaker.record_failure(error)

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc
                _, reason = self._handle_exception(exc, url, method, attempt, start_time)
                logger.debug(f"{method} to {url}: will retry ({reason})")

            # Sleep before retry (if not last attempt)
            if attempt < self.config.max_retries:
                sleep_time = self.strategy.calculate_delay(attempt, response)
                self.callbacks.on_retry(
                    url, method, attempt, self.config.max_retries, sleep_time, last_error, last_status_code
                )
                time.sleep(sleep_time)

        # All retries exhausted
        if response is not None:
            raise_final_error(
                url=url,
                method=method,
                max_retries=self.config.max_retries,
                response=response,
                on_failure=self.callbacks.callbacks.on_failure,
                start_time=start_time,
            )

        # This should not happen in practice
        error = HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} failed after {self.config.max_retries + 1} attempts",
        )
        self.callbacks.on_failure(
            url, method, self.config.max_retries, self.config.max_retries, error, last_status_code, start_time
        )
        raise error  # pragma: no cover


class AsyncRetryExecutor:
    """Executes async HTTP requests with automatic retry logic.

    This class orchestrates the async retry execution process using the
    strategy, decider, and callback manager components.
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

    def _handle_response(
        self,
        response: httpx.Response,
        url: str,
        method: str,
        attempt: int,
        start_time: float,
    ) -> bool:
        """Handle response and determine if should retry.

        Args:
            response: The HTTP response object.
            url: The URL that was requested.
            method: The HTTP method.
            attempt: The current attempt number (0-indexed).
            start_time: The timestamp when the request started.

        Returns:
            True if should retry, False if successful.

        Raises:
            HttpRequestError: If non-retryable error.
        """
        try:
            should_retry, reason = self.decider.should_retry_response(
                response, attempt, self.config.max_retries
            )
        except HttpRequestError as err:
            # Non-retryable status code or retry_if returned False
            # Fill in url/method and update message
            err.url = url
            err.method = method
            if not err.args[0].startswith(f"{method} request to"):
                err.args = (f"{method} request to {url} {err.args[0]}",)

            if self.config.circuit_breaker is not None:
                self.config.circuit_breaker.record_failure(err)

            self.callbacks.on_failure(
                url,
                method,
                attempt,
                self.config.max_retries,
                err,
                response.status_code,
                start_time,
            )
            raise

        if not should_retry:
            # Success!
            if self.config.circuit_breaker is not None:
                self.config.circuit_breaker.record_success()
            self.callbacks.on_success(
                url,
                method,
                attempt,
                self.config.max_retries,
                response,
                start_time,
            )
            return False

        # Should retry
        logger.debug(f"{method} to {url}: will retry ({reason})")
        return True

    def _handle_exception(
        self,
        exc: Exception,
        url: str,
        method: str,
        attempt: int,
        start_time: float,
    ) -> tuple[bool, str]:
        """Handle exception and determine if should retry.

        Args:
            exc: The exception that occurred.
            url: The URL that was requested.
            method: The HTTP method.
            attempt: The current attempt number (0-indexed).
            start_time: The timestamp when the request started.

        Returns:
            Tuple of (should_retry, reason).

        Raises:
            HttpRequestError: If non-retryable error.
        """
        try:
            should_retry, reason = self.decider.should_retry_exception(
                exc, attempt, self.config.max_retries
            )
        except HttpRequestError as err:
            # Non-retryable exception or retry_if returned False or max retries
            # Fill in url/method and update message
            err.url = url
            err.method = method
            if not err.args[0].startswith(f"{method} request to"):
                err.args = (f"{method} request to {url} {err.args[0]}",)

            if self.config.circuit_breaker is not None:
                self.config.circuit_breaker.record_failure(err)

            self.callbacks.on_failure(
                url,
                method,
                attempt,
                self.config.max_retries,
                err,
                None,
                start_time,
            )
            raise

        return should_retry, reason

    async def execute(
        self,
        url: str,
        method: str,
        request_func: Callable[..., Coroutine[Any, Any, httpx.Response]],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute async request with retry logic.

        Args:
            url: The URL to send the request to.
            method: The HTTP method name (e.g., "GET", "POST").
            request_func: The async function to call to make the request.
            **kwargs: Additional arguments to pass to request_func.

        Returns:
            The HTTP response object.

        Raises:
            HttpRequestError: If all retries are exhausted or non-retryable error.
            CircuitBreakerError: If circuit breaker is open.
        """
        start_time = time.time()
        last_error: Exception | None = None
        last_status_code: int | None = None
        response: httpx.Response | None = None

        for attempt in range(self.config.max_retries + 1):
            # Check max_total_time budget
            if self.config.max_total_time is not None and time.time() - start_time >= self.config.max_total_time:
                if response is not None:
                    raise_final_error(
                        url=url,
                        method=method,
                        max_retries=self.config.max_retries,
                        response=response,
                        on_failure=self.callbacks.callbacks.on_failure,
                        start_time=start_time,
                    )
                error = HttpRequestError(
                    method=method,
                    url=url,
                    message=f"{method} request to {url} exceeded time budget ({self.config.max_total_time:.1f}s)",
                )
                self.callbacks.on_failure(
                    url, method, attempt, self.config.max_retries, error, last_status_code, start_time
                )
                raise error

            # Check circuit breaker
            if self.config.circuit_breaker is not None:
                self.config.circuit_breaker.check()

            try:
                # Attempt request
                self.callbacks.on_request(url, method, attempt, self.config.max_retries)
                response = await request_func(url=url, **kwargs)

                # Handle response
                if not self._handle_response(response, url, method, attempt, start_time):
                    return response

                # Mark for retry - this means the status was retryable
                last_status_code = response.status_code
                # Record circuit breaker failure for retryable errors
                if self.config.circuit_breaker is not None:
                    error = HttpRequestError(
                        method=method,
                        url=url,
                        message=f"{method} request to {url} failed with status {response.status_code}",
                        status_code=response.status_code,
                        response=response,
                    )
                    self.config.circuit_breaker.record_failure(error)

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc
                _, reason = self._handle_exception(exc, url, method, attempt, start_time)
                logger.debug(f"{method} to {url}: will retry ({reason})")

            # Sleep before retry (if not last attempt)
            if attempt < self.config.max_retries:
                sleep_time = self.strategy.calculate_delay(attempt, response)
                self.callbacks.on_retry(
                    url, method, attempt, self.config.max_retries, sleep_time, last_error, last_status_code
                )
                await asyncio.sleep(sleep_time)

        # All retries exhausted
        if response is not None:
            raise_final_error(
                url=url,
                method=method,
                max_retries=self.config.max_retries,
                response=response,
                on_failure=self.callbacks.callbacks.on_failure,
                start_time=start_time,
            )

        # This should not happen in practice
        error = HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} failed after {self.config.max_retries + 1} attempts",
        )
        self.callbacks.on_failure(
            url, method, self.config.max_retries, self.config.max_retries, error, last_status_code, start_time
        )
        raise error  # pragma: no cover
