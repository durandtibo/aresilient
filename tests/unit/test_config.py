r"""Unit tests for configuration constants."""

from __future__ import annotations

from aresnet import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_STATUS_CODES,
)


######################################
#     Tests for Configuration       #
######################################


def test_default_timeout_is_positive_number() -> None:
    """Test that DEFAULT_TIMEOUT is a positive number."""
    assert isinstance(DEFAULT_TIMEOUT, (int, float))
    assert DEFAULT_TIMEOUT > 0


def test_default_timeout_value() -> None:
    """Test the DEFAULT_TIMEOUT value."""
    assert DEFAULT_TIMEOUT == 10.0


def test_default_max_retries_is_non_negative_integer() -> None:
    """Test that DEFAULT_MAX_RETRIES is a non-negative integer."""
    assert isinstance(DEFAULT_MAX_RETRIES, int)
    assert DEFAULT_MAX_RETRIES >= 0


def test_default_max_retries_value() -> None:
    """Test the DEFAULT_MAX_RETRIES value."""
    assert DEFAULT_MAX_RETRIES == 3


def test_default_backoff_factor_is_non_negative_number() -> None:
    """Test that DEFAULT_BACKOFF_FACTOR is a non-negative number."""
    assert isinstance(DEFAULT_BACKOFF_FACTOR, (int, float))
    assert DEFAULT_BACKOFF_FACTOR >= 0


def test_default_backoff_factor_value() -> None:
    """Test the DEFAULT_BACKOFF_FACTOR value."""
    assert DEFAULT_BACKOFF_FACTOR == 0.3


def test_retry_status_codes_is_tuple() -> None:
    """Test that RETRY_STATUS_CODES is a tuple."""
    assert isinstance(RETRY_STATUS_CODES, tuple)


def test_retry_status_codes_contains_integers() -> None:
    """Test that all elements in RETRY_STATUS_CODES are integers."""
    assert all(isinstance(code, int) for code in RETRY_STATUS_CODES)


def test_retry_status_codes_contains_valid_http_status_codes() -> None:
    """Test that all status codes are in the valid HTTP range."""
    assert all(100 <= code <= 599 for code in RETRY_STATUS_CODES)


def test_retry_status_codes_contains_expected_values() -> None:
    """Test that RETRY_STATUS_CODES contains the expected status codes."""
    assert 429 in RETRY_STATUS_CODES  # Too Many Requests
    assert 500 in RETRY_STATUS_CODES  # Internal Server Error
    assert 502 in RETRY_STATUS_CODES  # Bad Gateway
    assert 503 in RETRY_STATUS_CODES  # Service Unavailable
    assert 504 in RETRY_STATUS_CODES  # Gateway Timeout


def test_retry_status_codes_length() -> None:
    """Test that RETRY_STATUS_CODES has the expected length."""
    assert len(RETRY_STATUS_CODES) == 5


def test_retry_status_codes_exact_value() -> None:
    """Test the exact value of RETRY_STATUS_CODES."""
    assert RETRY_STATUS_CODES == (429, 500, 502, 503, 504)


def test_retry_status_codes_is_immutable() -> None:
    """Test that RETRY_STATUS_CODES is immutable (tuple)."""
    try:
        RETRY_STATUS_CODES[0] = 999  # type: ignore
        assert False, "RETRY_STATUS_CODES should be immutable"
    except TypeError:
        pass


def test_retry_status_codes_are_sorted() -> None:
    """Test that RETRY_STATUS_CODES are in ascending order."""
    assert RETRY_STATUS_CODES == tuple(sorted(RETRY_STATUS_CODES))


def test_retry_status_codes_has_no_duplicates() -> None:
    """Test that RETRY_STATUS_CODES has no duplicate values."""
    assert len(RETRY_STATUS_CODES) == len(set(RETRY_STATUS_CODES))
