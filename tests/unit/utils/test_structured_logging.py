from __future__ import annotations

import json
import logging
from io import StringIO

import pytest

from aresilient.utils.structured_logging import (
    StructuredFormatter,
    clear_correlation_id,
    get_correlation_id,
    log_structured,
    set_correlation_id,
)

##############################################
#     Tests for correlation ID management    #
##############################################


def test_get_correlation_id_initially_none() -> None:
    """Test that correlation ID is initially None."""
    clear_correlation_id()  # Ensure clean state
    assert get_correlation_id() is None


def test_set_and_get_correlation_id() -> None:
    """Test setting and getting correlation ID."""
    set_correlation_id("test-123")
    assert get_correlation_id() == "test-123"
    clear_correlation_id()


def test_clear_correlation_id() -> None:
    """Test clearing correlation ID."""
    set_correlation_id("test-456")
    assert get_correlation_id() == "test-456"
    clear_correlation_id()
    assert get_correlation_id() is None


def test_correlation_id_different_values() -> None:
    """Test setting different correlation IDs."""
    set_correlation_id("first-id")
    assert get_correlation_id() == "first-id"

    set_correlation_id("second-id")
    assert get_correlation_id() == "second-id"

    clear_correlation_id()


##############################################
#     Tests for StructuredFormatter          #
##############################################


def test_structured_formatter_basic_log() -> None:
    """Test that StructuredFormatter produces valid JSON."""
    # Setup logger with structured formatter
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_basic")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        # Log a message
        logger.info("Test message")

        # Parse and validate JSON output
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["message"] == "Test message"
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_basic"
        assert "timestamp" in log_data
        assert "module" in log_data
        assert "function" in log_data
        assert "line" in log_data
    finally:
        logger.removeHandler(handler)


def test_structured_formatter_with_correlation_id() -> None:
    """Test that StructuredFormatter includes correlation ID."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_correlation")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        # Set correlation ID
        set_correlation_id("request-789")

        # Log a message
        logger.info("Request started")

        # Parse and validate JSON output
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["message"] == "Request started"
        assert log_data["correlation_id"] == "request-789"
    finally:
        logger.removeHandler(handler)
        clear_correlation_id()


def test_structured_formatter_without_correlation_id() -> None:
    """Test that StructuredFormatter works without correlation ID."""
    clear_correlation_id()  # Ensure no correlation ID

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_no_correlation")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        # Log a message
        logger.info("No correlation")

        # Parse and validate JSON output
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["message"] == "No correlation"
        assert "correlation_id" not in log_data
    finally:
        logger.removeHandler(handler)


def test_structured_formatter_with_extra_fields() -> None:
    """Test that StructuredFormatter includes extra fields."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_extra")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        # Log with extra fields
        logger.info("Request completed", extra={"status_code": 200, "duration_ms": 150})

        # Parse and validate JSON output
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["message"] == "Request completed"
        assert log_data["status_code"] == 200
        assert log_data["duration_ms"] == 150
    finally:
        logger.removeHandler(handler)


def test_structured_formatter_different_log_levels() -> None:
    """Test StructuredFormatter with different log levels."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_levels")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        # Log at different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Parse all log entries
        output_lines = stream.getvalue().strip().split("\n")
        assert len(output_lines) == 4

        levels = [json.loads(line)["level"] for line in output_lines]
        assert levels == ["DEBUG", "INFO", "WARNING", "ERROR"]
    finally:
        logger.removeHandler(handler)


def test_structured_formatter_with_exception() -> None:
    """Test that StructuredFormatter includes exception information."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_exception")
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)

    try:
        # Log with exception
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.error("An error occurred", exc_info=True)

        # Parse and validate JSON output
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["message"] == "An error occurred"
        assert "exception" in log_data
        assert "ValueError: Test error" in log_data["exception"]
    finally:
        logger.removeHandler(handler)


def test_structured_formatter_timestamp_format() -> None:
    """Test that StructuredFormatter uses ISO 8601 timestamp."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_timestamp")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        # Log a message
        logger.info("Timestamp test")

        # Parse and validate JSON output
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        # Check timestamp format (ISO 8601 with milliseconds)
        timestamp = log_data["timestamp"]
        assert "T" in timestamp
        assert timestamp.endswith("Z")
        # Format: YYYY-MM-DDTHH:MM:SS.MMMZ
        assert len(timestamp) == 24
    finally:
        logger.removeHandler(handler)


##############################################
#     Tests for log_structured helper        #
##############################################


def test_log_structured_with_extra_fields() -> None:
    """Test log_structured helper function."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_helper")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        # Use log_structured helper
        log_structured(
            logger,
            logging.INFO,
            "Request completed",
            url="https://api.example.com",
            status_code=200,
            duration_ms=150,
        )

        # Parse and validate JSON output
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["message"] == "Request completed"
        assert log_data["url"] == "https://api.example.com"
        assert log_data["status_code"] == 200
        assert log_data["duration_ms"] == 150
    finally:
        logger.removeHandler(handler)


def test_log_structured_respects_log_level() -> None:
    """Test that log_structured respects logger's log level."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger("test_level_filter")
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)

    try:
        # These should not appear (below WARNING level)
        log_structured(logger, logging.DEBUG, "Debug message")
        log_structured(logger, logging.INFO, "Info message")

        # This should appear
        log_structured(logger, logging.WARNING, "Warning message")

        # Check output
        output = stream.getvalue().strip()
        assert output  # Should have output
        log_data = json.loads(output)
        assert log_data["message"] == "Warning message"
    finally:
        logger.removeHandler(handler)
