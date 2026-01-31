r"""Unit tests for package initialization and metadata."""

from __future__ import annotations

import aresilient


def test_package_version_is_string() -> None:
    """Test that __version__ is a string."""
    assert isinstance(aresilient.__version__, str)


def test_package_version_not_empty() -> None:
    """Test that __version__ is not empty."""
    assert len(aresilient.__version__) > 0


def test_package_version_format() -> None:
    """Test that __version__ follows semantic versioning."""
    # Should have at least one dot (e.g., "0.0.0" or "0.0.1a0")
    assert "." in aresilient.__version__


def test_all_exports_defined() -> None:
    """Test that all items in __all__ are defined in the module."""
    for name in aresilient.__all__:
        assert hasattr(aresilient, name), f"{name} is in __all__ but not defined in module"


def test_all_exports_count() -> None:
    """Test that __all__ has the expected number of exports."""
    # 4 config constants + 1 exception + 1 version + 14 HTTP methods (sync+async) = 22
    assert len(aresilient.__all__) == 22


def test_constants_are_immutable_types() -> None:
    """Test that configuration constants are immutable types."""
    # These should be int, float, or tuple (immutable)
    assert isinstance(aresilient.DEFAULT_MAX_RETRIES, int)
    assert isinstance(aresilient.DEFAULT_BACKOFF_FACTOR, float)
    assert isinstance(aresilient.DEFAULT_TIMEOUT, float)
    assert isinstance(aresilient.RETRY_STATUS_CODES, tuple)


def test_exception_class_is_callable() -> None:
    """Test that HttpRequestError is a callable exception class."""
    assert callable(aresilient.HttpRequestError)
    # Test that it can be instantiated
    exc = aresilient.HttpRequestError(method="GET", url="http://test.com", message="test")
    assert isinstance(exc, Exception)


def test_all_request_functions_are_callable() -> None:
    """Test that all request functions are callable."""
    request_funcs = [
        aresilient.delete_with_automatic_retry,
        aresilient.delete_with_automatic_retry_async,
        aresilient.get_with_automatic_retry,
        aresilient.get_with_automatic_retry_async,
        aresilient.head_with_automatic_retry,
        aresilient.head_with_automatic_retry_async,
        aresilient.options_with_automatic_retry,
        aresilient.options_with_automatic_retry_async,
        aresilient.patch_with_automatic_retry,
        aresilient.patch_with_automatic_retry_async,
        aresilient.post_with_automatic_retry,
        aresilient.post_with_automatic_retry_async,
        aresilient.put_with_automatic_retry,
        aresilient.put_with_automatic_retry_async,
        aresilient.request_with_automatic_retry,
        aresilient.request_with_automatic_retry_async,
    ]

    for func in request_funcs:
        assert callable(func), f"{func.__name__} is not callable"
