# Home

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
- **Multiple Backoff Strategies**: Choose from Exponential (default), Linear, Fibonacci, or Constant
  backoff, or implement your own custom strategy
- **Optional Jitter**: Add randomized jitter to prevent thundering herd problems and avoid
  overwhelming servers
- **Retry-After Header Support**: Respects server-specified retry delays from `Retry-After` headers
  (supports both integer seconds and HTTP-date formats)
- **Circuit Breaker Pattern**: Prevent cascading failures with built-in circuit breaker support
  (CLOSED, OPEN, HALF_OPEN states)
- **Context Manager API**: Manage multiple requests with shared configuration using ResilientClient
  and AsyncResilientClient
- **Complete HTTP Method Support**: Supports all common HTTP methods (GET, POST, PUT, DELETE, PATCH,
  HEAD, OPTIONS)
- **Full Async Support**: Fully supports asynchronous requests for high-performance applications
- **Built on httpx**: Leverages the modern, async-capable httpx library
- **Advanced Configuration**: Customize timeout, retry attempts, backoff strategies, jitter,
  retryable
  status codes, max total time, and max wait time
- **Custom Retry Predicates**: Define custom logic for retry decisions based on response content,
  headers, or business rules using the `retry_if` parameter
- **Callbacks for Observability**: Built-in callback system for logging, metrics, and alerting
  (on_request, on_retry, on_success, on_failure)
- **Type-Safe**: Fully typed with comprehensive type hints
- **Well-Tested**: Extensive test coverage ensuring reliability

## Quick Examples

### Basic GET Request

```python
from aresilient import get

# Simple GET request with automatic retry
response = get("https://api.example.com/data")
print(response.json())
```

### Basic POST Request

```python
from aresilient import post

# POST request with JSON payload
response = post("https://api.example.com/submit", json={"key": "value"})
print(response.status_code)
```

### Customizing Retry Behavior

```python
from aresilient import get

# Custom retry configuration
response = get(
    "https://api.example.com/data",
    max_retries=5,  # Retry up to 5 times
    backoff_factor=1.0,  # Exponential backoff factor
    timeout=30.0,  # 30 second timeout
    status_forcelist=(429, 503),  # Only retry on these status codes
)
```

### Using Different Backoff Strategies

```python
from aresilient import get
from aresilient.backoff import FibonacciBackoff, LinearBackoff

# Linear backoff (1s, 2s, 3s, 4s...)
response = get(
    "https://api.example.com/data",
    backoff_strategy=LinearBackoff(base_delay=1.0, max_delay=10.0),
)

# Fibonacci backoff (1s, 1s, 2s, 3s, 5s, 8s...)
response = get(
    "https://api.example.com/data",
    backoff_strategy=FibonacciBackoff(base_delay=1.0, max_delay=10.0),
)
```

### Using Context Manager for Multiple Requests

```python
from aresilient import ResilientClient

# Manage multiple requests with shared configuration
with ResilientClient(max_retries=5, timeout=30.0) as client:
    response1 = client.get("https://api.example.com/users")
    response2 = client.post("https://api.example.com/data", json={"key": "value"})
    response3 = client.put(
        "https://api.example.com/resource/123", json={"status": "active"}
    )
```

### Using Circuit Breaker

```python
from aresilient import get
from aresilient.circuit_breaker import CircuitBreaker

# Prevent cascading failures with circuit breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=5,  # Open circuit after 5 consecutive failures
    recovery_timeout=60.0,  # Try again after 60 seconds
)

response = get(
    "https://api.example.com/data",
    circuit_breaker=circuit_breaker,
)
```

### Using Async

```python
import asyncio
from aresilient import get_async


async def fetch_data():
    response = await get_async("https://api.example.com/data")
    return response.json()


# Run the async function
data = asyncio.run(fetch_data())
print(data)
```

### Async with Multiple Requests

```python
import asyncio
from aresilient import get_async


async def fetch_multiple():
    urls = [
        "https://api.example.com/data1",
        "https://api.example.com/data2",
        "https://api.example.com/data3",
    ]
    tasks = [get_async(url) for url in urls]
    responses = await asyncio.gather(*tasks)
    return [r.json() for r in responses]


# Fetch multiple URLs concurrently
results = asyncio.run(fetch_multiple())
```

## Installation

Install using `uv` (recommended):

```bash
uv pip install aresilient
```

Or using `pip`:

```bash
pip install aresilient
```

## API stability

:warning: While `aresilient` is in development stage, no API is guaranteed to be stable from one
release to the next.
In fact, it is very likely that the API will change multiple times before a stable 1.0.0 release.
In practice, this means that upgrading `aresilient` to a new version will possibly break any code
that was using the old version of `aresilient`.

## License

`aresilient` is licensed under BSD 3-Clause "New" or "Revised" license available
in [LICENSE](https://github.com/durandtibo/aresilient/blob/main/LICENSE) file.
