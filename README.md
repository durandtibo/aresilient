# aresnet

<p align="center">
    <a href="https://github.com/durandtibo/aresnet/actions/workflows/ci.yaml">
        <img alt="CI" src="https://github.com/durandtibo/aresnet/actions/workflows/ci.yaml/badge.svg">
    </a>
    <a href="https://github.com/durandtibo/aresnet/actions/workflows/nightly-tests.yaml">
        <img alt="Nightly Tests" src="https://github.com/durandtibo/aresnet/actions/workflows/nightly-tests.yaml/badge.svg">
    </a>
    <a href="https://github.com/durandtibo/aresnet/actions/workflows/nightly-package.yaml">
        <img alt="Nightly Package Tests" src="https://github.com/durandtibo/aresnet/actions/workflows/nightly-package.yaml/badge.svg">
    </a>
    <a href="https://codecov.io/gh/durandtibo/aresnet">
        <img alt="Codecov" src="https://codecov.io/gh/durandtibo/aresnet/branch/main/graph/badge.svg">
    </a>
    <br/>
    <a href="https://durandtibo.github.io/aresnet/">
        <img alt="Documentation" src="https://github.com/durandtibo/aresnet/actions/workflows/docs.yaml/badge.svg">
    </a>
    <a href="https://durandtibo.github.io/aresnet/dev/">
        <img alt="Documentation" src="https://github.com/durandtibo/aresnet/actions/workflows/docs-dev.yaml/badge.svg">
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
    <a href="https://pypi.org/project/aresnet/">
        <img alt="PYPI version" src="https://img.shields.io/pypi/v/aresnet">
    </a>
    <a href="https://pypi.org/project/aresnet/">
        <img alt="Python" src="https://img.shields.io/pypi/pyversions/aresnet.svg">
    </a>
    <a href="https://opensource.org/licenses/BSD-3-Clause">
        <img alt="BSD-3-Clause" src="https://img.shields.io/pypi/l/aresnet">
    </a>
    <br/>
    <a href="https://pepy.tech/project/aresnet">
        <img  alt="Downloads" src="https://static.pepy.tech/badge/aresnet">
    </a>
    <a href="https://pepy.tech/project/aresnet">
        <img  alt="Monthly downloads" src="https://static.pepy.tech/badge/aresnet/month">
    </a>
    <br/>
</p>

## Overview

`aresnet` is a Python library that provides resilient HTTP request functionality with automatic
retry logic and exponential backoff. Built on top of the
modern [httpx](https://www.python-httpx.org/) library, it simplifies handling transient failures in
HTTP communications, making your applications more robust and fault-tolerant.

## Key Features

- **Automatic Retry Logic**: Automatically retries failed requests for configurable HTTP status
  codes (429, 500, 502, 503, 504 by default)
- **Exponential Backoff with Jitter**: Implements exponential backoff strategy with randomized
  jitter (up to 10%) to prevent thundering herd problems and avoid overwhelming servers
- **Retry-After Header Support**: Respects server-specified retry delays from `Retry-After` headers
  (supports both integer seconds and HTTP-date formats)
- **Complete HTTP Method Support**: Supports all common HTTP methods (GET, POST, PUT, DELETE, PATCH)
- **Async Support**: Fully supports asynchronous requests for high-performance applications
- **Built on httpx**: Leverages the modern, async-capable httpx library
- **Configurable**: Customize timeout, retry attempts, backoff factors, and retryable status codes
- **Enhanced Error Handling**: Detailed logging of specific error types (ConnectError, PoolTimeout, etc.)
- **Type-Safe**: Fully typed with comprehensive type hints
- **Well-Tested**: Extensive test coverage ensuring reliability

## Installation

```bash
uv pip install aresnet
```

The following is the corresponding `aresnet` versions and supported dependencies.

| `aresnet` | `httpx`       | `python` |
|-----------|---------------|----------|
| `main`    | `>=0.28,<1.0` | `>=3.10` |

## Quick Start

### Basic GET Request

```python
from aresnet import get_with_automatic_retry

# Simple GET request with automatic retry
response = get_with_automatic_retry("https://api.example.com/data")
print(response.json())
```

### Basic POST Request

```python
from aresnet import post_with_automatic_retry

# POST request with JSON payload
response = post_with_automatic_retry(
    "https://api.example.com/submit", json={"key": "value"}
)
print(response.status_code)
```

### Customizing Retry Behavior

```python
from aresnet import get_with_automatic_retry

# Custom retry configuration
response = get_with_automatic_retry(
    "https://api.example.com/data",
    max_retries=5,  # Retry up to 5 times
    backoff_factor=1.0,  # Exponential backoff factor
    timeout=30.0,  # 30 second timeout
    status_forcelist=(429, 503),  # Only retry on these status codes
)
```

### Using a Custom httpx Client

```python
import httpx
from aresnet import get_with_automatic_retry

# Use your own httpx.Client for advanced configuration
with httpx.Client(headers={"Authorization": "Bearer token"}) as client:
    response = get_with_automatic_retry(
        "https://api.example.com/protected", client=client
    )
```

### Other HTTP Methods

```python
from aresnet import (
    put_with_automatic_retry,
    delete_with_automatic_retry,
    patch_with_automatic_retry,
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
```

### Error Handling

```python
from aresnet import get_with_automatic_retry, HttpRequestError

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
from aresnet import get_with_automatic_retry_async


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
from aresnet import get_with_automatic_retry_async


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
jitter = random(0, 0.1) * base_wait_time
total_wait_time = base_wait_time + jitter
```

For example, with `backoff_factor=0.3`:

- 1st retry: 0.3-0.33 seconds (base 0.3s + up to 10% jitter)
- 2nd retry: 0.6-0.66 seconds (base 0.6s + up to 10% jitter)
- 3rd retry: 1.2-1.32 seconds (base 1.2s + up to 10% jitter)

**Note**: Jitter is randomized for each retry to prevent multiple clients from retrying
simultaneously (thundering herd problem).

### Retry-After Header Support

When a server returns a `Retry-After` header (commonly with 429 or 503 status codes), the library
automatically uses the server's suggested wait time instead of exponential backoff. This ensures
compliance with rate limiting and helps avoid overwhelming the server.

The `Retry-After` header supports two formats:
- **Integer seconds**: `Retry-After: 120` (wait 120 seconds)
- **HTTP-date**: `Retry-After: Wed, 21 Oct 2015 07:28:00 GMT` (wait until this time)

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

### Async Versions

All synchronous functions have async counterparts with identical parameters:

- `get_with_automatic_retry_async()` - Async version of GET
- `post_with_automatic_retry_async()` - Async version of POST
- `put_with_automatic_retry_async()` - Async version of PUT
- `delete_with_automatic_retry_async()` - Async version of DELETE
- `patch_with_automatic_retry_async()` - Async version of PATCH

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

:warning: While `aresnet` is in development stage, no API is guaranteed to be stable from one
release to the next.
In fact, it is very likely that the API will change multiple times before a stable 1.0.0 release.
In practice, this means that upgrading `aresnet` to a new version will possibly break any code
that was using the old version of `aresnet`.

## License

`aresnet` is licensed under BSD 3-Clause "New" or "Revised" license available
in [LICENSE](LICENSE) file.
