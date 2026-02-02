r"""Retry decision logic for determining whether to retry requests.

This module provides the RetryDecider class that encapsulates the logic
for deciding whether a request should be retried based on response status
codes, exceptions, and custom predicates.
"""

from __future__ import annotations

__all__ = ["RetryDecider"]

import logging
from typing import TYPE_CHECKING

import httpx

from aresilient.exceptions import HttpRequestError

if TYPE_CHECKING:
    from collections.abc import Callable

logger: logging.Logger = logging.getLogger(__name__)


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
