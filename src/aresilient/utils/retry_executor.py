r"""Class-based retry executor using Strategy Pattern.

This module implements Approach 5 from the REQUEST_FUNCTION_SIMPLIFICATION.md
design document.
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
from aresilient.utils.callbacks import invoke_on_request, invoke_on_retry, invoke_on_success

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger: logging.Logger = logging.getLogger(__name__)


def _create_error_from_exception(
    exc: Exception,
    url: str,
    method: str,
    attempt: int,
) -> HttpRequestError:
    """Create appropriate error from exception."""
    if isinstance(exc, httpx.TimeoutException):
        return HttpRequestError(
            method=method,
            url=url,
            message=f"{method} request to {url} timed out ({attempt + 1} attempts)",
            cause=exc,
        )
    return HttpRequestError(
        method=method,
        url=url,
        message=f"{method} request to {url} failed after {attempt + 1} attempts: {exc}",
        cause=exc,
    )


def _create_final_error_from_response(
    url: str,
    method: str,
    response: httpx.Response | None,
    status_code: int | None,
    max_retries: int,
) -> HttpRequestError:
    """Create final error after all retries exhausted."""
    if response is not None:
        return HttpRequestError(
            method=method,
            url=url,
            message=(
                f"{method} request to {url} failed with status "
                f"{response.status_code} after {max_retries + 1} attempts"
            ),
            status_code=response.status_code,
            response=response,
        )
    return HttpRequestError(
        method=method,
        url=url,
        message=f"{method} request to {url} failed after {max_retries + 1} attempts",
        status_code=status_code,
    )


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int
    backoff_factor: float
    status_forcelist: tuple[int, ...]
    jitter_factor: float
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None


@dataclass
class CallbackConfig:
    """Configuration for callbacks."""

    on_request: Callable | None
    on_retry: Callable | None
    on_success: Callable | None
    on_failure: Callable | None


class RetryStrategy:
    """Strategy for calculating retry delays."""

    def __init__(self, backoff_factor: float, jitter_factor: float) -> None:
        self.backoff_factor = backoff_factor
        self.jitter_factor = jitter_factor

    def calculate_delay(
        self,
        attempt: int,
        response: httpx.Response | None = None,
    ) -> float:
        """Calculate delay before next retry."""
        return calculate_sleep_time(
            attempt,
            self.backoff_factor,
            self.jitter_factor,
            response,
        )


class RetryDecider:
    """Decides whether a request should be retried."""

    def __init__(
        self,
        status_forcelist: tuple[int, ...],
        retry_if: Callable | None,
    ) -> None:
        self.status_forcelist = status_forcelist
        self.retry_if = retry_if

    def should_retry_response(
        self,
        response: httpx.Response,
        attempt: int,  # noqa: ARG002
        max_retries: int,  # noqa: ARG002
    ) -> tuple[bool, str]:
        """Determine if response should trigger retry."""
        # Success case
        if response.status_code < 400:
            if self.retry_if is not None and self.retry_if(response, None):
                return (True, "retry_if predicate")
            return (False, "success")

        # Error case - check retry_if or status_forcelist
        if self.retry_if is not None:
            should_retry = self.retry_if(response, None)
            return (should_retry, "retry_if predicate")

        # Check status code
        is_retryable = response.status_code in self.status_forcelist
        return (is_retryable, f"status {response.status_code}")

    def should_retry_exception(
        self,
        exception: Exception,
        attempt: int,
        max_retries: int,
    ) -> tuple[bool, str]:
        """Determine if exception should trigger retry."""
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
        self.callbacks = callbacks

    def on_request(self, url: str, method: str, attempt: int, max_retries: int) -> None:
        """Invoke on_request callback."""
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
        """Invoke on_retry callback."""
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
        """Invoke on_success callback."""
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
        """Invoke on_failure callback."""
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
    ) -> None:
        self.config = retry_config
        self.strategy = RetryStrategy(
            retry_config.backoff_factor,
            retry_config.jitter_factor,
        )
        self.decider = RetryDecider(
            retry_config.status_forcelist,
            retry_config.retry_if,
        )
        self.callbacks = CallbackManager(callback_config)

    def execute(
        self,
        url: str,
        method: str,
        request_func: Callable[..., httpx.Response],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request with retry logic."""
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
                    response, attempt, self.config.max_retries
                )

                if not should_retry:
                    # Check if this is a success or non-retryable error
                    if response.status_code < 400:
                        # True success
                        if attempt > 0:
                            logger.debug(
                                f"{method} request to {url} succeeded on attempt {attempt + 1}"
                            )
                        self.callbacks.on_success(
                            url,
                            method,
                            attempt,
                            self.config.max_retries,
                            response,
                            start_time,
                        )
                        return response
                    # Non-retryable error - raise immediately
                    logger.debug(
                        f"{method} request to {url} failed with non-retryable status "
                        f"{response.status_code}"
                    )
                    error = HttpRequestError(
                        method=method,
                        url=url,
                        message=(
                            f"{method} request to {url} failed with status {response.status_code}"
                        ),
                        status_code=response.status_code,
                        response=response,
                    )
                    self.callbacks.on_failure(
                        url,
                        method,
                        attempt,
                        self.config.max_retries,
                        error,
                        response.status_code,
                        start_time,
                    )
                    raise error

                # Mark for retry
                last_status_code = response.status_code
                logger.debug(
                    f"{method} request to {url} failed with status {response.status_code}, "
                    f"will retry ({reason}) (attempt {attempt + 1}/{self.config.max_retries + 1})"
                )

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc

                # Evaluate exception
                should_retry, reason = self.decider.should_retry_exception(
                    exc, attempt, self.config.max_retries
                )

                if not should_retry:
                    # Create and raise final error
                    error = _create_error_from_exception(exc, url, method, attempt)
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

                logger.debug(
                    f"{method} request to {url} encountered {type(exc).__name__}, "
                    f"will retry ({reason}) (attempt {attempt + 1}/{self.config.max_retries + 1})"
                )

            # Sleep before retry (if not last attempt)
            if attempt < self.config.max_retries:
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

        # All retries exhausted - create and raise final error
        error = _create_final_error_from_response(
            url, method, response, last_status_code, self.config.max_retries
        )
        self.callbacks.on_failure(
            url,
            method,
            self.config.max_retries,
            self.config.max_retries,
            error,
            last_status_code,
            start_time,
        )
        raise error


class AsyncRetryExecutor:
    """Executes async HTTP requests with automatic retry logic."""

    def __init__(
        self,
        retry_config: RetryConfig,
        callback_config: CallbackConfig,
    ) -> None:
        self.config = retry_config
        self.strategy = RetryStrategy(
            retry_config.backoff_factor,
            retry_config.jitter_factor,
        )
        self.decider = RetryDecider(
            retry_config.status_forcelist,
            retry_config.retry_if,
        )
        self.callbacks = CallbackManager(callback_config)

    async def execute(
        self,
        url: str,
        method: str,
        request_func: Callable[..., Awaitable[httpx.Response]],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute async request with retry logic."""
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
                    response, attempt, self.config.max_retries
                )

                if not should_retry:
                    # Check if this is a success or non-retryable error
                    if response.status_code < 400:
                        # True success
                        if attempt > 0:
                            logger.debug(
                                f"{method} request to {url} succeeded on attempt {attempt + 1}"
                            )
                        self.callbacks.on_success(
                            url,
                            method,
                            attempt,
                            self.config.max_retries,
                            response,
                            start_time,
                        )
                        return response
                    # Non-retryable error - raise immediately
                    logger.debug(
                        f"{method} request to {url} failed with non-retryable status "
                        f"{response.status_code}"
                    )
                    error = HttpRequestError(
                        method=method,
                        url=url,
                        message=(
                            f"{method} request to {url} failed with status {response.status_code}"
                        ),
                        status_code=response.status_code,
                        response=response,
                    )
                    self.callbacks.on_failure(
                        url,
                        method,
                        attempt,
                        self.config.max_retries,
                        error,
                        response.status_code,
                        start_time,
                    )
                    raise error

                # Mark for retry
                last_status_code = response.status_code
                logger.debug(
                    f"{method} request to {url} failed with status {response.status_code}, "
                    f"will retry ({reason}) (attempt {attempt + 1}/{self.config.max_retries + 1})"
                )

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc

                # Evaluate exception
                should_retry, reason = self.decider.should_retry_exception(
                    exc, attempt, self.config.max_retries
                )

                if not should_retry:
                    # Create and raise final error
                    error = _create_error_from_exception(exc, url, method, attempt)
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

                logger.debug(
                    f"{method} request to {url} encountered {type(exc).__name__}, "
                    f"will retry ({reason}) (attempt {attempt + 1}/{self.config.max_retries + 1})"
                )

            # Sleep before retry (if not last attempt)
            if attempt < self.config.max_retries:
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

        # All retries exhausted - create and raise final error
        error = _create_final_error_from_response(
            url, method, response, last_status_code, self.config.max_retries
        )
        self.callbacks.on_failure(
            url,
            method,
            self.config.max_retries,
            self.config.max_retries,
            error,
            last_status_code,
            start_time,
        )
        raise error
