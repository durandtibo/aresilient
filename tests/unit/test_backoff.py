r"""Parametrized unit tests for backoff and jitter functionality.

This test module tests backoff and jitter behavior across all HTTP
methods using pytest parametrization.
"""

from __future__ import annotations

from unittest.mock import Mock, call, patch

import httpx
import pytest

from aresilient.backoff import ExponentialBackoff
from aresilient.core import ClientConfig
from tests.helpers import (
    HTTP_METHODS,
    HttpMethodTestCase,
    create_mock_client_with_side_effect,
    create_mock_response,
)

TEST_URL = "https://api.example.com/data"


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_exponential_backoff(
    test_case: HttpMethodTestCase, mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test exponential backoff timing."""
    mock_response = create_mock_response(status_code=test_case.status_code)
    mock_client, _ = create_mock_client_with_side_effect(
        test_case.client_method, [mock_response_fail, mock_response_fail, mock_response]
    )

    test_case.method_func(
        TEST_URL,
        client=mock_client,
        config=ClientConfig(backoff_strategy=ExponentialBackoff(base_delay=2.0)),
    )

    # Should have slept twice (after 1st and 2nd failures)
    assert mock_sleep.call_args_list == [call(2.0), call(4.0)]


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_negative_backoff_factor(test_case: HttpMethodTestCase) -> None:
    """Test that negative base_delay in ExponentialBackoff raises
    ValueError."""
    with pytest.raises(ValueError, match=r"base_delay must be non-negative"):
        test_case.method_func(
            TEST_URL, config=ClientConfig(backoff_strategy=ExponentialBackoff(base_delay=-1.0))
        )


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_with_jitter_factor(
    test_case: HttpMethodTestCase, mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that jitter_factor is applied during retries."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client, _ = create_mock_client_with_side_effect(
        test_case.client_method, [mock_response_fail, mock_response]
    )

    with patch("aresilient.utils.sleep.random.uniform", return_value=0.05):
        response = test_case.method_func(
            TEST_URL,
            client=mock_client,
            config=ClientConfig(
                backoff_strategy=ExponentialBackoff(base_delay=1.0), jitter_factor=0.1
            ),
        )

    assert response.status_code == test_case.status_code
    # Base sleep: 1.0 * 2^0 = 1.0
    # Jitter: 0.05 * 1.0 = 0.05
    # Total: 1.05
    mock_sleep.assert_called_once_with(1.05)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_zero_jitter_factor(
    test_case: HttpMethodTestCase, mock_sleep: Mock, mock_response_fail: httpx.Response
) -> None:
    """Test that zero jitter_factor results in no jitter."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client, _ = create_mock_client_with_side_effect(
        test_case.client_method, [mock_response_fail, mock_response]
    )

    response = test_case.method_func(
        TEST_URL,
        client=mock_client,
        config=ClientConfig(backoff_strategy=ExponentialBackoff(base_delay=1.0), jitter_factor=0.0),
    )

    assert response.status_code == test_case.status_code
    # No jitter applied
    mock_sleep.assert_called_once_with(1.0)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_negative_jitter_factor(test_case: HttpMethodTestCase) -> None:
    """Test that negative jitter_factor raises ValueError."""
    with pytest.raises(ValueError, match=r"jitter_factor must be >= 0"):
        test_case.method_func(TEST_URL, config=ClientConfig(jitter_factor=-0.1))
