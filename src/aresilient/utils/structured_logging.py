r"""Structured logging utilities for machine-readable log output.

This module provides utilities for structured logging with JSON formatting,
correlation IDs, and consistent field names. This is useful for log aggregation
systems like ELK, Splunk, or CloudWatch Logs.

The structured logging system is opt-in and can be enabled by configuring
Python's logging system to use the provided formatter.

Example:
    Enable structured logging for aresilient:

    ```python
    import logging
    from aresilient.utils.structured_logging import StructuredFormatter

    # Configure handler with structured formatter
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())

    # Apply to aresilient logger
    logger = logging.getLogger("aresilient")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    ```

    Use correlation IDs to track related requests:

    ```python
    from aresilient import get_with_automatic_retry
    from aresilient.utils.structured_logging import set_correlation_id, clear_correlation_id

    # Set correlation ID for request tracking
    set_correlation_id("request-123")
    try:
        response = get_with_automatic_retry("https://api.example.com/data")
    finally:
        clear_correlation_id()
    ```

"""

from __future__ import annotations

__all__ = [
    "StructuredFormatter",
    "get_correlation_id",
    "set_correlation_id",
    "clear_correlation_id",
    "log_structured",
]

import contextvars
import json
import logging
import time
from typing import Any

# Context variable for correlation ID (thread-safe)
_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def get_correlation_id() -> str | None:
    """Get the current correlation ID.

    Returns:
        The current correlation ID, or None if not set.

    Example:
        ```pycon
        >>> from aresilient.utils.structured_logging import (
        ...     get_correlation_id,
        ...     set_correlation_id,
        ... )
        >>> get_correlation_id()  # Initially None
        >>> set_correlation_id("req-123")
        >>> get_correlation_id()
        'req-123'

        ```
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context.

    The correlation ID is used to track related log entries across multiple
    operations. It is stored in a context variable, making it thread-safe
    and async-safe.

    Args:
        correlation_id: The correlation ID to set (e.g., request ID, trace ID).

    Example:
        ```pycon
        >>> from aresilient.utils.structured_logging import (
        ...     get_correlation_id,
        ...     set_correlation_id,
        ... )
        >>> set_correlation_id("request-456")
        >>> get_correlation_id()
        'request-456'

        ```
    """
    _correlation_id.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context.

    Example:
        ```pycon
        >>> from aresilient.utils.structured_logging import (
        ...     clear_correlation_id,
        ...     get_correlation_id,
        ...     set_correlation_id,
        ... )
        >>> set_correlation_id("request-789")
        >>> get_correlation_id()
        'request-789'
        >>> clear_correlation_id()
        >>> get_correlation_id()  # Returns None after clearing

        ```
    """
    _correlation_id.set(None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    This formatter outputs log records as JSON objects with consistent field
    names. It automatically includes correlation IDs if set, and preserves
    any extra fields added to the log record.

    Standard fields in the JSON output:
        - timestamp: ISO 8601 timestamp
        - level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - logger: Logger name
        - message: Log message
        - correlation_id: Optional correlation/trace ID
        - module: Module name where log originated
        - function: Function name where log originated
        - line: Line number where log originated
        - thread: Thread name
        - process: Process ID

    Any additional fields added via `extra` parameter in logging calls will
    be included in the JSON output.

    Example:
        ```pycon
        >>> import logging
        >>> from io import StringIO
        >>> from aresilient.utils.structured_logging import StructuredFormatter
        >>> # Create a logger with structured formatter
        >>> stream = StringIO()
        >>> handler = logging.StreamHandler(stream)
        >>> handler.setFormatter(StructuredFormatter())
        >>> logger = logging.getLogger("test_logger")
        >>> logger.addHandler(handler)
        >>> logger.setLevel(logging.INFO)
        >>> # Log a message
        >>> logger.info("Test message", extra={"request_id": "123"})
        >>> output = stream.getvalue()
        >>> "Test message" in output
        True
        >>> "request_id" in output
        True

        ```
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON-formatted log string.
        """
        # Build base log structure
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.threadName,
            "process": record.process,
        }

        # Add correlation ID if set
        correlation_id = get_correlation_id()
        if correlation_id is not None:
            log_data["correlation_id"] = correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from the log record
        # These are fields added via the 'extra' parameter in logging calls
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "msecs",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "sinfo",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
            }:
                log_data[key] = value

        return json.dumps(log_data)

    def formatTime(
        self, record: logging.LogRecord, datefmt: str | None = None
    ) -> str:
        """Format timestamp as ISO 8601.

        Args:
            record: The log record.
            datefmt: Optional date format (ignored, always uses ISO 8601).

        Returns:
            ISO 8601 formatted timestamp.
        """
        # Use ISO 8601 format with millisecond precision
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + f".{int(record.msecs):03d}Z"


def log_structured(
    logger: logging.Logger,
    level: int,
    message: str,
    **extra: Any,
) -> None:
    """Log a message with structured data.

    This is a convenience function for logging with extra structured fields.
    The extra fields will be included in JSON output when using
    StructuredFormatter.

    Args:
        logger: Logger to use.
        level: Log level (e.g., logging.INFO).
        message: Log message.
        **extra: Additional structured fields to include in the log.

    Example:
        ```pycon
        >>> import logging
        >>> from io import StringIO
        >>> from aresilient.utils.structured_logging import (
        ...     StructuredFormatter,
        ...     log_structured,
        ... )
        >>> # Setup
        >>> stream = StringIO()
        >>> handler = logging.StreamHandler(stream)
        >>> handler.setFormatter(StructuredFormatter())
        >>> logger = logging.getLogger("test_structured")
        >>> logger.addHandler(handler)
        >>> logger.setLevel(logging.DEBUG)
        >>> # Log with structured data
        >>> log_structured(
        ...     logger,
        ...     logging.INFO,
        ...     "Request completed",
        ...     url="https://api.example.com",
        ...     status_code=200,
        ...     duration_ms=150,
        ... )
        >>> output = stream.getvalue()
        >>> "Request completed" in output
        True
        >>> "status_code" in output
        True

        ```
    """
    logger.log(level, message, extra=extra)
