r"""Unit tests for package initialization and metadata."""

from __future__ import annotations

import pytest

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
    # 3 classes (AsyncResilientClient, HttpRequestError, ResilientClient)
    # + 1 version (__version__)
    # + 16 HTTP method functions (8 sync + 8 async)
    # = 20
    assert len(aresilient.__all__) == 20


def test_exception_class_is_callable() -> None:
    """Test that HttpRequestError is a callable exception class."""
    assert callable(aresilient.HttpRequestError)
    # Test that it can be instantiated
    exc = aresilient.HttpRequestError(method="GET", url="http://test.com", message="test")
    assert isinstance(exc, Exception)


@pytest.mark.parametrize(
    "func_name",
    [
        "delete",
        "delete_async",
        "get",
        "get_async",
        "head",
        "head_async",
        "options",
        "options_async",
        "patch",
        "patch_async",
        "post",
        "post_async",
        "put",
        "put_async",
        "request",
        "request_async",
    ],
)
def test_all_request_functions_are_callable(func_name: str) -> None:
    """Test that all request functions are callable."""
    func = getattr(aresilient, func_name)
    assert callable(func), f"{func_name} is not callable"


def test_resilient_client_class_is_available() -> None:
    """Test that ResilientClient class is available."""
    assert hasattr(aresilient, "ResilientClient")
    assert callable(aresilient.ResilientClient)


def test_async_resilient_client_class_is_available() -> None:
    """Test that AsyncResilientClient class is available."""
    assert hasattr(aresilient, "AsyncResilientClient")
    assert callable(aresilient.AsyncResilientClient)
