r"""Unit tests for test utility functions in helpers.py.

This module tests the helper functions that are used to reduce
boilerplate in other test files.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from aresilient import get_with_automatic_retry, get_with_automatic_retry_async
from tests.helpers import (
    assert_successful_request,
    assert_successful_request_async,
    setup_mock_async_client_for_method,
    setup_mock_client_for_method,
)

TEST_URL = "https://api.example.com/data"


##################################################
#     Tests for setup_mock_client_for_method     #
##################################################


def test_setup_mock_client_for_method_default_status() -> None:
    """Test setup_mock_client_for_method with default status code."""
    client, response = setup_mock_client_for_method("get")

    # Verify the client is properly configured
    assert isinstance(client, Mock)
    assert hasattr(client, "get")

    # Verify the response
    assert isinstance(response, Mock)
    assert response.status_code == 200

    # Verify the method returns the response
    assert client.get() == response


def test_setup_mock_client_for_method_custom_status() -> None:
    """Test setup_mock_client_for_method with custom status code."""
    client, response = setup_mock_client_for_method("post", status_code=201)

    assert response.status_code == 201
    assert client.post() == response


def test_setup_mock_client_for_method_with_response_kwargs() -> None:
    """Test setup_mock_client_for_method with additional response
    kwargs."""
    client, response = setup_mock_client_for_method(
        "put", status_code=200, response_kwargs={"text": "Updated"}
    )

    assert response.status_code == 200
    assert response.text == "Updated"
    assert client.put() == response


@pytest.mark.parametrize(
    "method",
    ["get", "post", "put", "delete", "patch", "head", "options"],
)
def test_setup_mock_client_for_method_different_methods(method: str) -> None:
    """Test setup_mock_client_for_method works with different HTTP
    methods."""
    client, response = setup_mock_client_for_method(method, status_code=200)
    assert hasattr(client, method)
    client_method = getattr(client, method)
    assert client_method() == response


##########################################################
#     Tests for setup_mock_async_client_for_method     #
##########################################################


def test_setup_mock_async_client_for_method_default_status() -> None:
    """Test setup_mock_async_client_for_method with default status
    code."""
    client, response = setup_mock_async_client_for_method("get")

    # Verify the client is properly configured
    assert isinstance(client, Mock)
    assert hasattr(client, "get")
    assert hasattr(client, "aclose")
    assert isinstance(client.aclose, AsyncMock)

    # Verify the response
    assert isinstance(response, Mock)
    assert response.status_code == 200


def test_setup_mock_async_client_for_method_custom_status() -> None:
    """Test setup_mock_async_client_for_method with custom status
    code."""
    _client, response = setup_mock_async_client_for_method("post", status_code=201)

    assert response.status_code == 201


def test_setup_mock_async_client_for_method_with_response_kwargs() -> None:
    """Test setup_mock_async_client_for_method with additional response
    kwargs."""
    _client, response = setup_mock_async_client_for_method(
        "put", status_code=200, response_kwargs={"text": "Updated"}
    )

    assert response.status_code == 200
    assert response.text == "Updated"


@pytest.mark.parametrize("method", ["get", "post", "put", "delete", "patch", "head", "options"])
def test_setup_mock_async_client_for_method_different_methods(method: str) -> None:
    """Test setup_mock_async_client_for_method works with different HTTP
    methods."""
    client, _response = setup_mock_async_client_for_method(method, status_code=200)

    assert hasattr(client, method)
    assert hasattr(client, "aclose")


###############################################
#     Tests for assert_successful_request     #
###############################################


def test_assert_successful_request_default_status(mock_sleep: Mock) -> None:
    """Test assert_successful_request with default expected status."""
    client, _ = setup_mock_client_for_method("get", 200)

    response = assert_successful_request(get_with_automatic_retry, TEST_URL, client)

    assert response.status_code == 200
    client.get.assert_called_once_with(url=TEST_URL)
    mock_sleep.assert_not_called()


def test_assert_successful_request_custom_status(mock_sleep: Mock) -> None:
    """Test assert_successful_request with custom expected status."""
    # Use 200 which is a success status, so it doesn't trigger errors
    client, _ = setup_mock_client_for_method("get", 200)

    response = assert_successful_request(
        get_with_automatic_retry, TEST_URL, client, expected_status=200
    )

    assert response.status_code == 200
    mock_sleep.assert_not_called()


def test_assert_successful_request_with_kwargs(mock_sleep: Mock) -> None:
    """Test assert_successful_request with additional kwargs."""
    client, _ = setup_mock_client_for_method("get", 200)

    headers = {"X-Custom": "value"}
    response = assert_successful_request(
        get_with_automatic_retry, TEST_URL, client, headers=headers
    )

    assert response.status_code == 200
    client.get.assert_called_once_with(url=TEST_URL, headers=headers)
    mock_sleep.assert_not_called()


def test_assert_successful_request_status_mismatch(mock_sleep: Mock) -> None:
    """Test assert_successful_request fails when status doesn't
    match."""
    # Use 200 for the mock, but expect 201 to test the assertion
    client, _ = setup_mock_client_for_method("get", 200)

    with pytest.raises(AssertionError):
        assert_successful_request(get_with_automatic_retry, TEST_URL, client, expected_status=201)
    mock_sleep.assert_not_called()


def test_assert_successful_request_returns_response(mock_sleep: Mock) -> None:
    """Test assert_successful_request returns the response object."""
    client, mock_response = setup_mock_client_for_method("get", 200)

    response = assert_successful_request(get_with_automatic_retry, TEST_URL, client)

    assert response is mock_response
    mock_sleep.assert_not_called()


#####################################################
#     Tests for assert_successful_request_async     #
#####################################################


@pytest.mark.asyncio
async def test_assert_successful_request_async_default_status(mock_asleep: Mock) -> None:
    """Test assert_successful_request_async with default expected
    status."""
    client, _ = setup_mock_async_client_for_method("get", 200)

    response = await assert_successful_request_async(
        get_with_automatic_retry_async, TEST_URL, client
    )

    assert response.status_code == 200
    client.get.assert_called_once_with(url=TEST_URL)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_assert_successful_request_async_custom_status(mock_asleep: Mock) -> None:
    """Test assert_successful_request_async with custom expected
    status."""
    # Use 200 which is a success status, so it doesn't trigger errors
    client, _ = setup_mock_async_client_for_method("get", 200)

    response = await assert_successful_request_async(
        get_with_automatic_retry_async, TEST_URL, client, expected_status=200
    )

    assert response.status_code == 200
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_assert_successful_request_async_with_kwargs(mock_asleep: Mock) -> None:
    """Test assert_successful_request_async with additional kwargs."""
    client, _ = setup_mock_async_client_for_method("get", 200)

    headers = {"X-Custom": "value"}
    response = await assert_successful_request_async(
        get_with_automatic_retry_async, TEST_URL, client, headers=headers
    )

    assert response.status_code == 200
    client.get.assert_called_once_with(url=TEST_URL, headers=headers)
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_assert_successful_request_async_status_mismatch(mock_asleep: Mock) -> None:
    """Test assert_successful_request_async fails when status doesn't
    match."""
    # Use 200 for the mock, but expect 201 to test the assertion
    client, _ = setup_mock_async_client_for_method("get", 200)

    with pytest.raises(AssertionError):
        await assert_successful_request_async(
            get_with_automatic_retry_async, TEST_URL, client, expected_status=201
        )
    mock_asleep.assert_not_called()


@pytest.mark.asyncio
async def test_assert_successful_request_async_returns_response(mock_asleep: Mock) -> None:
    """Test assert_successful_request_async returns the response
    object."""
    client, mock_response = setup_mock_async_client_for_method("get", 200)

    response = await assert_successful_request_async(
        get_with_automatic_retry_async, TEST_URL, client
    )

    assert response is mock_response
    mock_asleep.assert_not_called()
