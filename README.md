# aresilient

<p align="center">
    <a href="https://github.com/durandtibo/aresilient/actions/workflows/ci.yaml">
        <img alt="CI" src="https://github.com/durandtibo/aresilient/actions/workflows/ci.yaml/badge.svg">
    </a>
    <a href="https://github.com/durandtibo/aresilient/actions/workflows/nightly-tests.yaml">
        <img alt="Nightly Tests" src="https://github.com/durandtibo/aresilient/actions/workflows/nightly-tests.yaml/badge.svg">
    </a>
    <a href="https://github.com/durandtibo/aresilient/actions/workflows/nightly-package.yaml">
        <img alt="Nightly Package Tests" src="https://github.com/durandtibo/aresilient/actions/workflows/nightly-package.yaml/badge.svg">
    </a>
    <a href="https://codecov.io/gh/durandtibo/aresilient">
        <img alt="Codecov" src="https://codecov.io/gh/durandtibo/aresilient/branch/main/graph/badge.svg">
    </a>
    <br/>
    <a href="https://durandtibo.github.io/aresilient/">
        <img alt="Documentation" src="https://github.com/durandtibo/aresilient/actions/workflows/docs.yaml/badge.svg">
    </a>
    <a href="https://durandtibo.github.io/aresilient/dev/">
        <img alt="Documentation" src="https://github.com/durandtibo/aresilient/actions/workflows/docs-dev.yaml/badge.svg">
    </a>
    <br/>
    <a href="https://github.com/psf/black">
        <img  alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg">
    </a>
    <a href="https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings">
        <img  alt="Doc style: google" src="https://img.shields.io/badge/%20style-google-3666d6.svg">
    </a>
    <a href="https://github.com/astral-sh/ruff">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" style="max-width:100%;">
    </a>
    <a href="https://github.com/guilatrova/tryceratops">
        <img  alt="Doc style: google" src="https://img.shields.io/badge/try%2Fexcept%20style-tryceratops%20%F0%9F%A6%96%E2%9C%A8-black">
    </a>
    <br/>
    <a href="https://pypi.org/project/aresilient/">
        <img alt="PYPI version" src="https://img.shields.io/pypi/v/aresilient">
    </a>
    <a href="https://pypi.org/project/aresilient/">
        <img alt="Python" src="https://img.shields.io/pypi/pyversions/aresilient.svg">
    </a>
    <a href="https://opensource.org/licenses/BSD-3-Clause">
        <img alt="BSD-3-Clause" src="https://img.shields.io/pypi/l/aresilient">
    </a>
    <br/>
    <a href="https://pepy.tech/project/aresilient">
        <img  alt="Downloads" src="https://static.pepy.tech/badge/aresilient">
    </a>
    <a href="https://pepy.tech/project/aresilient">
        <img  alt="Monthly downloads" src="https://static.pepy.tech/badge/aresilient/month">
    </a>
    <br/>
</p>

## Overview

`aresilient` is a Python library that provides resilient HTTP request functionality with automatic
retry logic and exponential backoff. Built on top of the
modern [httpx](https://www.python-httpx.org/) library, it simplifies handling transient failures in
HTTP communications, making your applications more robust and fault-tolerant.

## Key Features

- **Automatic Retry Logic**: Automatically retries failed requests for configurable HTTP status
  codes (429, 500, 502, 503, 504 by default)
- **Exponential Backoff with Optional Jitter**: Implements exponential backoff strategy with
  optional randomized jitter to prevent thundering herd problems and avoid overwhelming servers
- **Retry-After Header Support**: Respects server-specified retry delays from `Retry-After` headers
  (supports both integer seconds and HTTP-date formats)
- **Complete HTTP Method Support**: Supports all common HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- **Async Support**: Fully supports asynchronous requests for high-performance applications
- **Built on httpx**: Leverages the modern, async-capable httpx library
- **Configurable**: Customize timeout, retry attempts, backoff factors, jitter, and retryable status codes
- **Enhanced Error Handling**: Comprehensive error handling with detailed exception information
  including HTTP status codes and response objects
- **Type-Safe**: Fully typed with comprehensive type hints
- **Well-Tested**: Extensive test coverage ensuring reliability

## Installation

```bash
uv pip install aresilient
```

The following is the corresponding `aresilient` versions and supported dependencies.

| `aresilient` | `httpx`       | `python` |
|-----------|---------------|----------|
| `main`    | `>=0.28,<1.0` | `>=3.10` |

## Quick Start

### Basic GET Request

```python
from aresilient import get_with_automatic_retry

# Simple GET request with automatic retry
response = get_with_automatic_retry("https://api.example.com/data")
print(response.json())
```

### Basic POST Request

```python
from aresilient import post_with_automatic_retry

# POST request with JSON payload
response = post_with_automatic_retry(
    "https://api.example.com/submit", json={"key": "value"}
)
print(response.status_code)
```

### Customizing Retry Behavior

```python
from aresilient import get_with_automatic_retry

# Custom retry configuration
response = get_with_automatic_retry(
    "https://api.example.com/data",
    max_retries=5,  # Retry up to 5 times
    backoff_factor=1.0,  # Exponential backoff factor
    jitter_factor=0.1,  # Add 10% jitter to prevent thundering herd
    timeout=30.0,  # 30 second timeout
    status_forcelist=(429, 503),  # Only retry on these status codes
)
```

### Using a Custom httpx Client

```python
import httpx
from aresilient import get_with_automatic_retry

# Use your own httpx.Client for advanced configuration
with httpx.Client(headers={"Authorization": "Bearer token"}) as client:
    response = get_with_automatic_retry(
        "https://api.example.com/protected", client=client
    )
```

### Other HTTP Methods

```python
from aresilient import (
    put_with_automatic_retry,
    delete_with_automatic_retry,
    patch_with_automatic_retry,
    head_with_automatic_retry,
    options_with_automatic_retry,
)

# PUT request to update a resource
response = put_with_automatic_retry(
    "https://api.example.com/resource/123", json={"name": "updated"}
)

# DELETE request to remove a resource
response = delete_with_automatic_retry("https://api.example.com/resource/123")

# PATCH request to partially update a resource
response = patch_with_automatic_retry(
    "https://api.example.com/resource/123", json={"status": "active"}
)

# HEAD request to check resource existence and get metadata
response = head_with_automatic_retry("https://api.example.com/large-file.zip")
if response.status_code == 200:
    print(f"File size: {response.headers.get('Content-Length')} bytes")

# OPTIONS request to discover allowed methods
response = options_with_automatic_retry("https://api.example.com/resource")
print(f"Allowed methods: {response.headers.get('Allow')}")
```

### Error Handling

```python
from aresilient import get_with_automatic_retry, HttpRequestError

try:
    response = get_with_automatic_retry("https://api.example.com/data")
except HttpRequestError as e:
    print(f"Request failed: {e}")
    print(f"Method: {e.method}")
    print(f"URL: {e.url}")
    print(f"Status Code: {e.status_code}")
```

### Using Async

All HTTP methods have async versions for concurrent request processing:

```python
import asyncio
from aresilient import get_with_automatic_retry_async


async def fetch_data():
    response = await get_with_automatic_retry_async("https://api.example.com/data")
    return response.json()


# Run the async function
data = asyncio.run(fetch_data())
print(data)
```

### Concurrent Async Requests

Process multiple requests concurrently for better performance:

```python
import asyncio
from aresilient import get_with_automatic_retry_async


async def fetch_multiple():
    urls = [
        "https://api.example.com/data1",
        "https://api.example.com/data2",
        "https://api.example.com/data3",
    ]
    tasks = [get_with_automatic_retry_async(url) for url in urls]
    responses = await asyncio.gather(*tasks)
    return [r.json() for r in responses]


# Fetch multiple URLs concurrently
results = asyncio.run(fetch_multiple())
```

### Custom Retry Predicates

You can define custom logic to determine whether to retry a request based on the response or exception using the `retry_if` parameter. This is useful when you need to retry based on response content, headers, or business logic beyond just status codes.

```python
from aresilient import get_with_automatic_retry


def should_retry(response, exception):
    """Custom predicate to decide if request should be retried.

    Args:
        response: The HTTP response object (or None if an exception occurred)
        exception: The exception that occurred (or None if response received)

    Returns:
        True to retry, False to not retry
    """
    # Retry if response contains specific error message
    if response and "rate limit" in response.text.lower():
        return True

    # Retry on connection errors
    if isinstance(exception, ConnectionError):
        return True

    # Retry on server errors (5xx status codes)
    if response and response.status_code >= 500:
        return True

    return False


# Use the custom retry predicate
response = get_with_automatic_retry(
    "https://api.example.com/data", retry_if=should_retry, max_retries=5
)
```

**Note**: When `retry_if` is provided, it takes precedence over `status_forcelist` for determining retry behavior. The predicate is called with:
- `response` and `exception` parameters (at least one will be non-None)
- Should return `True` to retry, `False` to not retry

Common use cases for custom retry predicates:
- Retry on specific error messages in response body
- Retry on empty responses with 200 status
- Retry based on custom headers
- Retry on business logic conditions (e.g., "insufficient funds" that will be replenished)

```python
# Example: Retry on empty response
def retry_on_empty_response(response, exception):
    if response and response.status_code == 200 and not response.text.strip():
        return True  # Retry empty successful responses
    return False


# Example: Complex business logic
def retry_on_business_error(response, exception):
    if response and response.status_code == 400:
        try:
            data = response.json()
            # Retry if error is temporary
            if data.get("error") in ["insufficient_funds", "try_again_later"]:
                return True
        except:
            pass
    return False
```

## Configuration

### Default Settings

- **Timeout**: 10.0 seconds
- **Max Retries**: 3 (4 total attempts including the initial request)
- **Backoff Factor**: 0.3
- **Retryable Status Codes**: 429 (Too Many Requests), 500 (Internal Server Error), 502 (Bad
  Gateway), 503 (Service Unavailable), 504 (Gateway Timeout)

### Exponential Backoff Formula

The wait time between retries is calculated as:

```
base_wait_time = backoff_factor * (2 ** retry_number)
# If jitter_factor is set (e.g., 0.1 for 10% jitter):
jitter = random(0, jitter_factor) * base_wait_time
total_wait_time = base_wait_time + jitter
```

For example, with `backoff_factor=0.3` and `jitter_factor=0.1`:

- 1st retry: 0.3-0.33 seconds (base 0.3s + up to 10% jitter)
- 2nd retry: 0.6-0.66 seconds (base 0.6s + up to 10% jitter)
- 3rd retry: 1.2-1.32 seconds (base 1.2s + up to 10% jitter)

**Note**: Jitter is optional (disabled by default with `jitter_factor=0`). When enabled, it's
randomized for each retry to prevent multiple clients from retrying simultaneously (thundering
herd problem). Set `jitter_factor=0.1` for 10% jitter, which is recommended for production use.

### Retry-After Header Support

When a server returns a `Retry-After` header (commonly with 429 or 503 status codes), the library
automatically uses the server's suggested wait time instead of exponential backoff. This ensures
compliance with rate limiting and helps avoid overwhelming the server.

The `Retry-After` header supports two formats:
- **Integer seconds**: `Retry-After: 120` (wait 120 seconds)
- **HTTP-date**: `Retry-After: Wed, 21 Oct 2015 07:28:00 GMT` (wait until this time)

**Note**: If `jitter_factor` is configured, jitter is still applied to server-specified
`Retry-After` values to prevent thundering herd issues when many clients receive the same retry
delay from a server.

## API Reference

### `get_with_automatic_retry()`

Performs an HTTP GET request with automatic retry logic.

**Parameters:**

- `url` (str): The URL to send the request to
- `client` (httpx.Client | None): Optional httpx client to use
- `timeout` (float | httpx.Timeout): Request timeout in seconds
- `max_retries` (int): Maximum number of retry attempts
- `backoff_factor` (float): Exponential backoff factor
- `status_forcelist` (tuple[int, ...]): HTTP status codes that trigger a retry
- `jitter_factor` (float): Factor for adding random jitter to backoff delays (0.0-1.0, default: 0.0)
- `retry_if` (Callable[[httpx.Response | None, Exception | None], bool] | None): Custom predicate function to determine whether to retry. If provided, takes precedence over `status_forcelist`. Called with `(response, exception)` and should return `True` to retry, `False` otherwise.
- `**kwargs`: Additional arguments passed to `httpx.Client.get()`

**Returns:** `httpx.Response`

**Raises:**

- `HttpRequestError`: If the request fails after all retries
- `ValueError`: If parameters are invalid

### `post_with_automatic_retry()`

Performs an HTTP POST request with automatic retry logic.

**Parameters:**

- `url` (str): The URL to send the request to
- `client` (httpx.Client | None): Optional httpx client to use
- `timeout` (float | httpx.Timeout): Request timeout in seconds
- `max_retries` (int): Maximum number of retry attempts
- `backoff_factor` (float): Exponential backoff factor
- `status_forcelist` (tuple[int, ...]): HTTP status codes that trigger a retry
- `**kwargs`: Additional arguments passed to `httpx.Client.post()`

**Returns:** `httpx.Response`

**Raises:**

- `HttpRequestError`: If the request fails after all retries
- `ValueError`: If parameters are invalid

### `put_with_automatic_retry()`

Performs an HTTP PUT request with automatic retry logic.

**Parameters:**

- `url` (str): The URL to send the request to
- `client` (httpx.Client | None): Optional httpx client to use
- `timeout` (float | httpx.Timeout): Request timeout in seconds
- `max_retries` (int): Maximum number of retry attempts
- `backoff_factor` (float): Exponential backoff factor
- `status_forcelist` (tuple[int, ...]): HTTP status codes that trigger a retry
- `**kwargs`: Additional arguments passed to `httpx.Client.put()`

**Returns:** `httpx.Response`

**Raises:**

- `HttpRequestError`: If the request fails after all retries
- `ValueError`: If parameters are invalid

### `delete_with_automatic_retry()`

Performs an HTTP DELETE request with automatic retry logic.

**Parameters:**

- `url` (str): The URL to send the request to
- `client` (httpx.Client | None): Optional httpx client to use
- `timeout` (float | httpx.Timeout): Request timeout in seconds
- `max_retries` (int): Maximum number of retry attempts
- `backoff_factor` (float): Exponential backoff factor
- `status_forcelist` (tuple[int, ...]): HTTP status codes that trigger a retry
- `**kwargs`: Additional arguments passed to `httpx.Client.delete()`

**Returns:** `httpx.Response`

**Raises:**

- `HttpRequestError`: If the request fails after all retries
- `ValueError`: If parameters are invalid

### `patch_with_automatic_retry()`

Performs an HTTP PATCH request with automatic retry logic.

**Parameters:**

- `url` (str): The URL to send the request to
- `client` (httpx.Client | None): Optional httpx client to use
- `timeout` (float | httpx.Timeout): Request timeout in seconds
- `max_retries` (int): Maximum number of retry attempts
- `backoff_factor` (float): Exponential backoff factor
- `status_forcelist` (tuple[int, ...]): HTTP status codes that trigger a retry
- `**kwargs`: Additional arguments passed to `httpx.Client.patch()`

**Returns:** `httpx.Response`

**Raises:**

- `HttpRequestError`: If the request fails after all retries
- `ValueError`: If parameters are invalid

### `head_with_automatic_retry()`

Performs an HTTP HEAD request with automatic retry logic.

**Parameters:**

- `url` (str): The URL to send the request to
- `client` (httpx.Client | None): Optional httpx client to use
- `timeout` (float | httpx.Timeout): Request timeout in seconds
- `max_retries` (int): Maximum number of retry attempts
- `backoff_factor` (float): Exponential backoff factor
- `status_forcelist` (tuple[int, ...]): HTTP status codes that trigger a retry
- `**kwargs`: Additional arguments passed to `httpx.Client.head()`

**Returns:** `httpx.Response`

**Raises:**

- `HttpRequestError`: If the request fails after all retries
- `ValueError`: If parameters are invalid

**Use cases:** HEAD requests retrieve only headers without the response body, making them useful for checking resource existence, metadata (Content-Length, Last-Modified, ETag), and performing lightweight validation.

### `options_with_automatic_retry()`

Performs an HTTP OPTIONS request with automatic retry logic.

**Parameters:**

- `url` (str): The URL to send the request to
- `client` (httpx.Client | None): Optional httpx client to use
- `timeout` (float | httpx.Timeout): Request timeout in seconds
- `max_retries` (int): Maximum number of retry attempts
- `backoff_factor` (float): Exponential backoff factor
- `status_forcelist` (tuple[int, ...]): HTTP status codes that trigger a retry
- `**kwargs`: Additional arguments passed to `httpx.Client.options()`

**Returns:** `httpx.Response`

**Raises:**

- `HttpRequestError`: If the request fails after all retries
- `ValueError`: If parameters are invalid

**Use cases:** OPTIONS requests are used for CORS preflight requests, discovering allowed HTTP methods via the Allow header, and querying server capabilities.

### Async Versions

All synchronous functions have async counterparts with identical parameters:

- `get_with_automatic_retry_async()` - Async version of GET
- `post_with_automatic_retry_async()` - Async version of POST
- `put_with_automatic_retry_async()` - Async version of PUT
- `delete_with_automatic_retry_async()` - Async version of DELETE
- `patch_with_automatic_retry_async()` - Async version of PATCH
- `head_with_automatic_retry_async()` - Async version of HEAD
- `options_with_automatic_retry_async()` - Async version of OPTIONS

These functions work exactly like their synchronous counterparts but must be awaited and use
`httpx.AsyncClient` instead of `httpx.Client`.

### Low-Level Functions

For custom HTTP methods or advanced use cases:

- `request_with_automatic_retry()` - Generic synchronous request with retry logic
- `request_with_automatic_retry_async()` - Generic async request with retry logic

These functions allow you to specify any HTTP method (e.g., HEAD, OPTIONS) and provide your own
request function from an httpx client.

### `HttpRequestError`

Exception raised when an HTTP request fails.

**Attributes:**

- `method` (str): HTTP method used
- `url` (str): URL that was requested
- `status_code` (int | None): HTTP status code (if available)
- `response` (httpx.Response | None): Full response object (if available)

## Contributing

Please check the instructions in [CONTRIBUTING.md](CONTRIBUTING.md).

## API stability

:warning: While `aresilient` is in development stage, no API is guaranteed to be stable from one
release to the next.
In fact, it is very likely that the API will change multiple times before a stable 1.0.0 release.
In practice, this means that upgrading `aresilient` to a new version will possibly break any code
that was using the old version of `aresilient`.

## License

`aresilient` is licensed under BSD 3-Clause "New" or "Revised" license available
in [LICENSE](LICENSE) file.
