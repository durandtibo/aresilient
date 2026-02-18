r"""Callback manager for orchestrating retry lifecycle events.

This module provides the CallbackManager class that handles invocation
of user-defined callbacks at various points in the retry lifecycle.
"""

from __future__ import annotations

__all__ = ["CallbackManager"]

import time
from typing import TYPE_CHECKING

from aresilient.callbacks import (
    FailureInfo,
    invoke_on_request,
    invoke_on_retry,
    invoke_on_success,
)

if TYPE_CHECKING:
    import httpx

    from aresilient.retry.config import CallbackConfig


class CallbackManager:
    """Manages callback invocations during the retry lifecycle.

    This class coordinates the invocation of user-defined callbacks at various
    points in the HTTP request retry lifecycle, including before requests,
    after success, before retries, and on failures.

    Attributes:
        callbacks: Configuration containing callback functions for lifecycle events.
    """

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
            self.callbacks.on_failure(
                FailureInfo(
                    url=url,
                    method=method,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=error,
                    status_code=status_code,
                    total_time=time.time() - start_time,
                )
            )
