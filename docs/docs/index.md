# Home

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
- **Exponential Backoff with Optional Jitter**: Implements exponential backoff strategy with
  optional randomized jitter to prevent thundering herd problems and avoid overwhelming servers
- **Retry-After Header Support**: Respects server-specified retry delays from `Retry-After` headers
  (supports both integer seconds and HTTP-date formats)
- **Complete HTTP Method Support**: Supports all common HTTP methods (GET, POST, PUT, DELETE, PATCH)
- **Async Support**: Fully supports asynchronous requests for high-performance applications
- **Built on httpx**: Leverages the modern, async-capable httpx library
- **Configurable**: Customize timeout, retry attempts, backoff factors, jitter, and retryable status codes
- **Type-Safe**: Fully typed with comprehensive type hints
- **Well-Tested**: Extensive test coverage ensuring reliability

## Quick Examples

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

### Using Async

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

### Async with Multiple Requests

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

## Installation

Install using `uv` (recommended):

```bash
uv pip install aresnet
```

Or using `pip`:

```bash
pip install aresnet
```

## API stability

:warning: While `aresnet` is in development stage, no API is guaranteed to be stable from one
release to the next.
In fact, it is very likely that the API will change multiple times before a stable 1.0.0 release.
In practice, this means that upgrading `aresnet` to a new version will possibly break any code
that was using the old version of `aresnet`.

## License

`aresnet` is licensed under BSD 3-Clause "New" or "Revised" license available
in [LICENSE](https://github.com/durandtibo/aresnet/blob/main/LICENSE) file.
