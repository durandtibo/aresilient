r"""Retry decision logic for determining whether to retry requests.

This module provides the RetryDecider class that encapsulates the logic
for deciding whether a request should be retried based on response
status codes, exceptions, and custom predicates.
"""

from __future__ import annotations

__all__ = ["RetryDecider"]

import logging
from typing import TYPE_CHECKING

from aresilient.core.retry_logic import (
    should_retry_exception as _should_retry_exception,
    should_retry_response as _should_retry_response,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

logger: logging.Logger = logging.getLogger(__name__)


class RetryDecider:
    """Decides whether a request should be retried based on responses
    and exceptions.

    This class encapsulates the retry decision logic, evaluating HTTP responses
    and exceptions against configured status codes and custom predicates.

    Attributes:
        status_forcelist: Tuple of HTTP status codes that should trigger retries.
        retry_if: Optional custom predicate for retry decisions.
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
        return _should_retry_response(
            response=response,
            url=url,
            method=method,
            status_forcelist=self.status_forcelist,
            retry_if=self.retry_if,
        )

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
        return _should_retry_exception(
            exception=exception,
            attempt=attempt,
            max_retries=max_retries,
            retry_if=self.retry_if,
        )
