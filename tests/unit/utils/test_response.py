from __future__ import annotations

from unittest.mock import Mock

import httpx
import pytest

from aresilient.exceptions import HttpRequestError
from aresilient.utils import handle_response

TEST_URL = "https://api.example.com/data"


#####################################
#     Tests for handle_response     #
#####################################


def test_handle_response_retryable_status() -> None:
    """Test that retryable status codes don't raise an exception."""
    mock_response = Mock(spec=httpx.Response, status_code=503)

    # Should not raise for status in forcelist
    handle_response(mock_response, TEST_URL, method="GET", status_forcelist=(503, 500))


def test_handle_response_non_retryable_status() -> None:
    """Test that non-retryable status codes raise HttpRequestError."""
    mock_response = Mock(spec=httpx.Response, status_code=404)

    with pytest.raises(HttpRequestError, match=r"failed with status 404") as exc_info:
        handle_response(mock_response, TEST_URL, method="GET", status_forcelist=(503, 500))

    error = exc_info.value
    assert error.method == "GET"
    assert error.url == TEST_URL
    assert error.status_code == 404
    assert error.response == mock_response


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
def test_handle_response_various_non_retryable_codes(status_code: int) -> None:
    """Test various non-retryable status codes."""
    mock_response = Mock(spec=httpx.Response, status_code=status_code)

    with pytest.raises(HttpRequestError, match=rf"failed with status {status_code}") as exc_info:
        handle_response(mock_response, TEST_URL, method="POST", status_forcelist=(500, 503))

    assert exc_info.value.status_code == status_code
