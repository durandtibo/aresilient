r"""Contain utility functions for HTTP requests."""

from __future__ import annotations

__all__ = ["validate_retry_params"]


def validate_retry_params(max_retries: int, backoff_factor: float) -> None:
    """Validate retry parameters.

    Args:
        max_retries: Maximum number of retry attempts for failed requests.
            Must be >= 0.
        backoff_factor: Factor for exponential backoff between retries.
            Must be >= 0.

    Raises:
        ValueError: If max_retries or backoff_factor are negative.

    Example:
        ```pycon
        >>> from aresnet.utils import validate_retry_params
        >>> validate_retry_params(max_retries=3, backoff_factor=0.5)
        >>> validate_retry_params(max_retries=-1, backoff_factor=0.5)  # doctest: +SKIP
        Traceback (most recent call last):
            ...
        ValueError: max_retries must be >= 0, got -1

        ```
    """
    if max_retries < 0:
        msg = f"max_retries must be >= 0, got {max_retries}"
        raise ValueError(msg)
    if backoff_factor < 0:
        msg = f"backoff_factor must be >= 0, got {backoff_factor}"
        raise ValueError(msg)
