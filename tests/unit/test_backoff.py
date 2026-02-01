r"""Parametrized unit tests for backoff and jitter functionality.

This test module tests backoff and jitter behavior across all HTTP
methods using pytest parametrization.
"""

from __future__ import annotations

from unittest.mock import Mock, call, patch

import httpx
import pytest

from .helpers import HTTP_METHODS, HttpMethodTestCase

TEST_URL = "https://api.example.com/data"


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_exponential_backoff(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test exponential backoff timing."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client)
    client_method = Mock(side_effect=[mock_response_fail, mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    test_case.method_func(TEST_URL, client=mock_client, backoff_factor=2.0)

    # Should have slept twice (after 1st and 2nd failures)
    assert mock_sleep.call_args_list == [call(2.0), call(4.0)]


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_negative_backoff_factor(test_case: HttpMethodTestCase) -> None:
    """Test that negative backoff_factor raises ValueError."""
    with pytest.raises(ValueError, match=r"backoff_factor must be >= 0"):
        test_case.method_func(TEST_URL, backoff_factor=-1.0)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_with_jitter_factor(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that jitter_factor is applied during retries."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=500)
    mock_client = Mock(spec=httpx.Client)
    client_method = Mock(side_effect=[mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    with patch("aresilient.utils.random.uniform", return_value=0.05):
        response = test_case.method_func(
            TEST_URL, client=mock_client, backoff_factor=1.0, jitter_factor=0.1
        )

    assert response.status_code == test_case.status_code
    # Base sleep: 1.0 * 2^0 = 1.0
    # Jitter: 0.05 * 1.0 = 0.05
    # Total: 1.05
    mock_sleep.assert_called_once_with(1.05)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_zero_jitter_factor(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that zero jitter_factor results in no jitter."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_response_fail = Mock(spec=httpx.Response, status_code=500)
    mock_client = Mock(spec=httpx.Client)
    client_method = Mock(side_effect=[mock_response_fail, mock_response])
    setattr(mock_client, test_case.client_method, client_method)

    response = test_case.method_func(
        TEST_URL, client=mock_client, backoff_factor=1.0, jitter_factor=0.0
    )

    assert response.status_code == test_case.status_code
    # No jitter applied
    mock_sleep.assert_called_once_with(1.0)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_negative_jitter_factor(test_case: HttpMethodTestCase) -> None:
    """Test that negative jitter_factor raises ValueError."""
    with pytest.raises(ValueError, match=r"jitter_factor must be >= 0"):
        test_case.method_func(TEST_URL, jitter_factor=-0.1)
