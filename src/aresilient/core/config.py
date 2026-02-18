r"""Configuration dataclass and defaults for ResilientClient.

This module provides configuration constants and a dataclass-based
configuration object for the ResilientClient and AsyncResilientClient
context manager classes.
"""

from __future__ import annotations

__all__ = [
    "ClientConfig",
    "DEFAULT_BACKOFF_FACTOR",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "RETRY_STATUS_CODES",
]

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

from aresilient.core.validation import validate_retry_params

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from aresilient.backoff import BackoffStrategy
    from aresilient.callbacks import FailureInfo, RequestInfo, ResponseInfo, RetryInfo
    from aresilient.circuit_breaker import CircuitBreaker


# Default timeout in seconds for HTTP requests
# This is a reasonable default for most API calls
DEFAULT_TIMEOUT = 10.0

# Default maximum number of retry attempts
# Total attempts = max_retries + 1 (initial attempt)
DEFAULT_MAX_RETRIES = 3

# Default backoff factor for exponential backoff
# Wait time = backoff_factor * (2 ** attempt)
# With 0.3: 1st retry waits 0.3s, 2nd waits 0.6s, 3rd waits 1.2s
DEFAULT_BACKOFF_FACTOR = 0.3

# HTTP status codes that should trigger automatic retry
# 429: Too Many Requests - Rate limiting
# 500: Internal Server Error - Temporary server issue
# 502: Bad Gateway - Upstream server error
# 503: Service Unavailable - Server overloaded or down
# 504: Gateway Timeout - Upstream server timeout
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


@dataclass
class ClientConfig:
    """Configuration for ResilientClient retry behavior.

    This dataclass encapsulates retry-related configuration parameters
    for a ResilientClient or AsyncResilientClient instance. It provides
    validation, merging, and conversion to dictionary format.

    Note:
        The timeout parameter is NOT included in this config as it is used
        directly by httpx.Client/AsyncClient, not by aresilient's retry logic.

    Args:
        max_retries: Maximum number of retry attempts for failed requests. Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries. Must be >= 0.
        status_forcelist: Tuple of HTTP status codes that should trigger a retry.
        jitter_factor: Factor for adding random jitter to backoff delays. Must be >= 0.
        retry_if: Optional custom predicate function to determine whether to retry.
        backoff_strategy: Optional custom backoff strategy instance.
        max_total_time: Optional maximum total time budget in seconds for all retry
            attempts. Must be > 0 if provided.
        max_wait_time: Optional maximum backoff delay cap in seconds. Must be > 0 if provided.
        circuit_breaker: Optional circuit breaker instance for advanced failure handling.
        on_request: Optional callback called before each request attempt.
        on_retry: Optional callback called before each retry (after backoff).
        on_success: Optional callback called when request succeeds.
        on_failure: Optional callback called when all retries are exhausted.

    Example:
        ```pycon
        >>> from aresilient.core.config import ClientConfig
        >>> config = ClientConfig()  # Use defaults
        >>> config.max_retries
        3
        >>> config = ClientConfig(max_retries=5)
        >>> config.max_retries
        5
        >>> merged = config.merge(max_retries=10)  # Override specific parameters
        >>> merged.max_retries
        10
        >>> config.max_retries  # Original unchanged
        5

        ```
    """

    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR
    status_forcelist: tuple[int, ...] = field(default_factory=lambda: RETRY_STATUS_CODES)
    jitter_factor: float = 0.0
    retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None = None
    backoff_strategy: BackoffStrategy | None = None
    max_total_time: float | None = None
    max_wait_time: float | None = None
    circuit_breaker: CircuitBreaker | None = None
    on_request: Callable[[RequestInfo], None] | None = None
    on_retry: Callable[[RetryInfo], None] | None = None
    on_success: Callable[[ResponseInfo], None] | None = None
    on_failure: Callable[[FailureInfo], None] | None = None

    def __post_init__(self) -> None:
        """Validate configuration parameters after initialization.

        Raises:
            ValueError: If any parameter fails validation.
        """
        # Note: timeout validation is not needed here as it's handled separately
        # by the client when creating httpx.Client/AsyncClient
        validate_retry_params(
            max_retries=self.max_retries,
            backoff_factor=self.backoff_factor,
            jitter_factor=self.jitter_factor,
            max_total_time=self.max_total_time,
            max_wait_time=self.max_wait_time,
        )

    def merge(self, **overrides: Any) -> ClientConfig:
        """Create a new config with specified parameters overridden.

        This method creates a new ClientConfig instance with the same values
        as the current instance, except for the parameters specified in
        overrides. Only non-None override values are applied.

        Args:
            **overrides: Keyword arguments for parameters to override.
                Only non-None values will override the current config.

        Returns:
            A new ClientConfig instance with overrides applied.

        Example:
            ```pycon
            >>> from aresilient.core.config import ClientConfig
            >>> config = ClientConfig(max_retries=3)
            >>> new_config = config.merge(max_retries=5)
            >>> new_config.max_retries
            5
            >>> config.max_retries  # Original unchanged
            3

            ```
        """
        # Filter out None values to preserve original config values
        filtered_overrides = {k: v for k, v in overrides.items() if v is not None}
        return replace(self, **filtered_overrides)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary format.

        This method converts the ClientConfig to a dictionary suitable for
        passing as keyword arguments to retry functions.

        Returns:
            Dictionary with retry configuration parameters.

        Example:
            ```pycon
            >>> from aresilient.core.config import ClientConfig
            >>> config = ClientConfig(max_retries=5)
            >>> params = config.to_dict()
            >>> params["max_retries"]
            5

            ```
        """
        return {
            "max_retries": self.max_retries,
            "backoff_factor": self.backoff_factor,
            "status_forcelist": self.status_forcelist,
            "jitter_factor": self.jitter_factor,
            "retry_if": self.retry_if,
            "backoff_strategy": self.backoff_strategy,
            "max_total_time": self.max_total_time,
            "max_wait_time": self.max_wait_time,
            "circuit_breaker": self.circuit_breaker,
            "on_request": self.on_request,
            "on_retry": self.on_retry,
            "on_success": self.on_success,
            "on_failure": self.on_failure,
        }
