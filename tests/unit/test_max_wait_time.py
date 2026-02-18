r"""Parametrized unit tests for max_wait_time functionality.

This test module tests max_wait_time behavior across all HTTP methods
using pytest parametrization.
"""

from __future__ import annotations

from unittest.mock import Mock, call

import httpx
import pytest

from aresilient.core import ClientConfig
from tests.helpers import HTTP_METHODS, HttpMethodTestCase

TEST_URL = "https://api.example.com/data"


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_max_wait_time_caps_backoff(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that max_wait_time caps the backoff delay."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client)
    # Fail 3 times, then succeed
    client_method = Mock(
        side_effect=[mock_response_fail, mock_response_fail, mock_response_fail, mock_response]
    )
    setattr(mock_client, test_case.client_method, client_method)

    response = test_case.method_func(
        TEST_URL,
        client=mock_client,
        config=ClientConfig(max_retries=5, backoff_factor=2.0, max_wait_time=5.0),
    )

    assert response.status_code == test_case.status_code
    # Expected: 2.0, 4.0, 5.0 (third capped at 5.0 instead of 8.0)
    assert mock_sleep.call_args_list == [call(2.0), call(4.0), call(5.0)]


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_max_wait_time_with_retry_after_header(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that max_wait_time caps Retry-After header values."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    # Create a response with Retry-After header suggesting long wait
    mock_response_fail = Mock(spec=httpx.Response, status_code=429)
    mock_response_fail.headers = {"Retry-After": "10"}  # Server suggests 10s wait
    mock_client = Mock(spec=httpx.Client)
    client_method = Mock(side_effect=[mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    response = test_case.method_func(
        TEST_URL,
        client=mock_client,
        config=ClientConfig(max_retries=3, max_wait_time=3.0),
    )

    assert response.status_code == test_case.status_code
    # Should cap Retry-After value from 10s to 3s
    mock_sleep.assert_called_once_with(3.0)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_max_wait_time_below_backoff(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that max_wait_time does not affect smaller backoff
    values."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client)
    client_method = Mock(side_effect=[mock_response_fail, mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    response = test_case.method_func(
        TEST_URL,
        client=mock_client,
        config=ClientConfig(max_retries=3, backoff_factor=0.5, max_wait_time=10.0),
    )

    assert response.status_code == test_case.status_code
    # Should use original backoff values since they're below the cap
    assert mock_sleep.call_args_list == [call(0.5), call(1.0)]


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_negative_max_wait_time(test_case: HttpMethodTestCase) -> None:
    """Test that negative max_wait_time raises ValueError."""
    with pytest.raises(ValueError, match=r"max_wait_time must be > 0"):
        test_case.method_func(TEST_URL, config=ClientConfig(max_wait_time=-1.0))


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_zero_max_wait_time(test_case: HttpMethodTestCase) -> None:
    """Test that zero max_wait_time raises ValueError."""
    with pytest.raises(ValueError, match=r"max_wait_time must be > 0"):
        test_case.method_func(TEST_URL, config=ClientConfig(max_wait_time=0.0))


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_max_wait_time_none(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that max_wait_time=None allows uncapped backoff."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client)
    client_method = Mock(
        side_effect=[mock_response_fail, mock_response_fail, mock_response_fail, mock_response]
    )
    setattr(mock_client, test_case.client_method, client_method)

    response = test_case.method_func(
        TEST_URL,
        client=mock_client,
        config=ClientConfig(max_retries=5, backoff_factor=2.0, max_wait_time=None),
    )

    assert response.status_code == test_case.status_code
    # Should use exponential backoff without capping
    assert mock_sleep.call_args_list == [call(2.0), call(4.0), call(8.0)]
