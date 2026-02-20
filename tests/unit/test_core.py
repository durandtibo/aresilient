r"""Parametrized unit tests for core functionality in all HTTP method
wrappers.

This test module uses pytest parametrization to test core functionality
across all HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
in a consistent and maintainable way. Tests that are common to all
methods are defined here to reduce duplication.

Method-specific tests remain in their respective test files:
- test_get.py: GET-specific tests (e.g., params support)
- test_post.py: POST-specific tests (e.g., data/form submission)
- test_put.py: PUT-specific tests
- test_delete.py: DELETE-specific tests
- test_patch.py: PATCH-specific tests
- test_head.py: HEAD-specific tests (e.g., response body handling)
- test_options.py: OPTIONS-specific tests

Retry, backoff, and recovery tests are in their respective specialized files:
- test_retry.py: Retry mechanism tests
- test_backoff.py: Backoff strategy tests
- test_recovery.py: Error recovery and specific exception tests
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from aresilient import HttpRequestError
from aresilient.core import ClientConfig
from tests.helpers import (
    HTTP_METHODS,
    HttpMethodTestCase,
    setup_mock_client_for_method,
)

TEST_URL = "https://api.example.com/data"


############################################################
#     Parametrized Tests for Core HTTP Method Features     #
############################################################


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_successful_request_with_custom_client(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test successful request with custom client."""
    mock_client, _ = setup_mock_client_for_method(test_case.client_method, test_case.status_code)

    response = test_case.method_func(TEST_URL, client=mock_client)

    assert response.status_code == test_case.status_code
    client_method = getattr(mock_client, test_case.client_method)
    client_method.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_successful_request_with_default_client(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test successful request on first attempt with default client."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)

    with patch(f"httpx.Client.{test_case.client_method}", return_value=mock_response):
        response = test_case.method_func(TEST_URL)

    assert response.status_code == test_case.status_code
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_request_with_json_payload(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test request with JSON data."""
    mock_client, _ = setup_mock_client_for_method(test_case.client_method, test_case.status_code)

    response = test_case.method_func(TEST_URL, json={"key": "value"}, client=mock_client)

    assert response.status_code == test_case.status_code
    client_method = getattr(mock_client, test_case.client_method)
    client_method.assert_called_once_with(url=TEST_URL, json={"key": "value"})
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_timeout_exception(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test handling of timeout exception."""
    mock_client = Mock(spec=httpx.Client)
    client_method = Mock(side_effect=httpx.TimeoutException("Request timeout"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=rf"{test_case.method_name} request to https://api.example.com/data timed out \(1 attempts\)",
    ):
        test_case.method_func(TEST_URL, client=mock_client, config=ClientConfig(max_retries=0))

    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_request_error(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test handling of general request errors."""
    mock_client = Mock(spec=httpx.Client)
    client_method = Mock(side_effect=httpx.RequestError("Connection failed"))
    setattr(mock_client, test_case.client_method, client_method)

    with pytest.raises(
        HttpRequestError,
        match=(
            rf"{test_case.method_name} request to https://api.example.com/data failed after 1 attempts: "
            r"Connection failed"
        ),
    ):
        test_case.method_func(TEST_URL, client=mock_client, config=ClientConfig(max_retries=0))

    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_negative_max_retries(test_case: HttpMethodTestCase) -> None:
    """Test that negative max_retries raises ValueError via
    ClientConfig."""
    with pytest.raises(ValueError, match=r"max_retries must be >= 0"):
        test_case.method_func(TEST_URL, config=ClientConfig(max_retries=-1))


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_negative_timeout(test_case: HttpMethodTestCase) -> None:
    """Test that negative timeout raises ValueError."""
    with pytest.raises(ValueError, match=r"timeout must be > 0"):
        test_case.method_func(TEST_URL, timeout=-1.0)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_zero_timeout(test_case: HttpMethodTestCase) -> None:
    """Test that zero timeout raises ValueError."""
    with pytest.raises(ValueError, match=r"timeout must be > 0"):
        test_case.method_func(TEST_URL, timeout=0.0)


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_client_close_when_owns_client(test_case: HttpMethodTestCase) -> None:
    """Test that client is closed when created internally."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    with patch("httpx.Client", return_value=mock_client):
        test_case.method_func(TEST_URL)

    mock_client.close.assert_called_once()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_client_not_closed_when_provided(test_case: HttpMethodTestCase) -> None:
    """Test that external client is not closed."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    test_case.method_func(TEST_URL, client=mock_client)

    mock_client.close.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_custom_timeout(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test custom timeout parameter."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    with patch("httpx.Client") as mock_client_class:
        mock_client_class.return_value = mock_client
        test_case.method_func(TEST_URL, timeout=30.0)

    mock_client_class.assert_called_once_with(timeout=30.0)
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_with_httpx_timeout_object(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test request with httpx.Timeout object."""
    timeout_config = httpx.Timeout(10.0, connect=5.0)
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)

    with patch("httpx.Client") as mock_client_class:
        mock_client_instance = Mock()
        setattr(mock_client_instance, test_case.client_method, Mock(return_value=mock_response))
        mock_client_instance.close = Mock()
        mock_client_class.return_value = mock_client_instance
        response = test_case.method_func(TEST_URL, timeout=timeout_config)

    mock_client_class.assert_called_once_with(timeout=timeout_config)
    assert response.status_code == test_case.status_code
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
@pytest.mark.parametrize("status_code", [200, 201, 202, 204, 206])
def test_successful_2xx_status_codes(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
    status_code: int,
) -> None:
    """Test that various 2xx status codes are considered successful."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    response = test_case.method_func(TEST_URL, client=mock_client)

    assert response.status_code == status_code
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
@pytest.mark.parametrize("status_code", [301, 302, 303, 304, 307, 308])
def test_successful_3xx_status_codes(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
    status_code: int,
) -> None:
    """Test that 3xx redirect status codes are considered successful."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    response = test_case.method_func(TEST_URL, client=mock_client)

    assert response.status_code == status_code
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_with_headers(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test request with custom headers."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    response = test_case.method_func(
        TEST_URL,
        client=mock_client,
        headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
    )

    assert response.status_code == test_case.status_code
    client_method = getattr(mock_client, test_case.client_method)
    client_method.assert_called_once_with(
        url=TEST_URL,
        headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
    )
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_error_message_includes_url(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that error message includes the URL."""
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    with pytest.raises(
        HttpRequestError,
        match=(
            rf"{test_case.method_name} request to https://api.example.com/data failed with status 503 "
            r"after 1 attempts"
        ),
    ):
        test_case.method_func(TEST_URL, client=mock_client, config=ClientConfig(max_retries=0))

    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_client_close_on_exception(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that client is closed even when exception occurs."""
    mock_client = Mock(spec=httpx.Client)
    client_method = Mock(side_effect=httpx.TimeoutException("Timeout"))
    setattr(mock_client, test_case.client_method, client_method)

    with (
        patch("httpx.Client", return_value=mock_client),
        pytest.raises(
            HttpRequestError,
            match=rf"{test_case.method_name} request to https://api.example.com/data timed out \(1 attempts\)",
        ),
    ):
        test_case.method_func(TEST_URL, config=ClientConfig(max_retries=0))

    mock_client.close.assert_called_once()
    mock_sleep.assert_not_called()


####################################################
#     Tests for ClientConfig parameter support     #
####################################################


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_successful_request_with_config(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test successful request using ClientConfig."""
    config = ClientConfig(max_retries=2)
    mock_client, _ = setup_mock_client_for_method(test_case.client_method, test_case.status_code)

    response = test_case.method_func(TEST_URL, client=mock_client, config=config)

    assert response.status_code == test_case.status_code
    client_method = getattr(mock_client, test_case.client_method)
    client_method.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_config_values_are_used(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that config values are respected when request fails."""
    config = ClientConfig(max_retries=0)
    mock_response = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    with pytest.raises(
        HttpRequestError,
        match=(
            rf"{test_case.method_name} request to https://api.example.com/data failed with status 503 "
            r"after 1 attempts"
        ),
    ):
        test_case.method_func(TEST_URL, client=mock_client, config=config)

    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_config_none_uses_defaults(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that config=None uses default values (same as not passing
    config)."""
    mock_client, _ = setup_mock_client_for_method(test_case.client_method, test_case.status_code)

    response = test_case.method_func(TEST_URL, client=mock_client, config=None)

    assert response.status_code == test_case.status_code
    mock_sleep.assert_not_called()


##############################################################
#     Tests for individual retry parameter support           #
##############################################################


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_individual_max_retries_param(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that max_retries can be passed directly without ClientConfig."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_response_ok = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(
        mock_client,
        test_case.client_method,
        Mock(side_effect=[mock_response_fail, mock_response_ok]),
    )

    response = test_case.method_func(TEST_URL, client=mock_client, max_retries=1)

    assert response.status_code == test_case.status_code
    assert getattr(mock_client, test_case.client_method).call_count == 2


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_individual_max_retries_overrides_config(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that direct max_retries parameter overrides config value."""
    mock_response_fail = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response_fail))

    # config says max_retries=3 but we override with max_retries=0
    with pytest.raises(HttpRequestError):
        test_case.method_func(
            TEST_URL, client=mock_client, config=ClientConfig(max_retries=3), max_retries=0
        )

    # Only 1 attempt (no retries)
    assert getattr(mock_client, test_case.client_method).call_count == 1
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_individual_jitter_factor_param(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that jitter_factor can be passed directly without ClientConfig."""
    mock_client, _ = setup_mock_client_for_method(test_case.client_method, test_case.status_code)

    response = test_case.method_func(TEST_URL, client=mock_client, jitter_factor=0.0)

    assert response.status_code == test_case.status_code
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_individual_status_forcelist_param(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test that status_forcelist can be passed directly without ClientConfig."""
    # 503 is in the default forcelist but we override with only (500,)
    mock_response_503 = Mock(spec=httpx.Response, status_code=503)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response_503))

    # With status_forcelist=(500,), 503 is NOT retryable → immediate failure
    with pytest.raises(HttpRequestError):
        test_case.method_func(
            TEST_URL,
            client=mock_client,
            max_retries=3,
            status_forcelist=(500,),
        )

    # Should only have made one attempt (503 not retryable with our custom list)
    assert getattr(mock_client, test_case.client_method).call_count == 1
    mock_sleep.assert_not_called()
