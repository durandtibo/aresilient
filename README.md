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
- **Multiple Backoff Strategies**: Choose from Exponential (default), Linear, Fibonacci, Constant,
  or implement your own custom backoff strategy for fine-tuned retry behavior
- **Circuit Breaker Pattern**: Prevent cascading failures by automatically stopping requests to
  failing services and allowing time for recovery
- **Optional Jitter**: Add randomized jitter to backoff delays to prevent thundering herd problems
  and avoid overwhelming servers
- **Retry-After Header Support**: Respects server-specified retry delays from `Retry-After` headers
  (supports both integer seconds and HTTP-date formats)
- **Complete HTTP Method Support**: Supports all common HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- **Async Support**: Fully supports asynchronous requests for high-performance applications
- **Built on httpx**: Leverages the modern, async-capable httpx library
- **Configurable**: Customize timeout, retry attempts, backoff strategies, jitter, and retryable status codes
- **Enhanced Error Handling**: Comprehensive error handling with detailed exception information
  including HTTP status codes and response objects
- **Callbacks for Observability**: Built-in callback system for logging, metrics, and alerting
  (on_request, on_retry, on_success, on_failure)
- **Custom Retry Predicates**: Define custom logic for retry decisions based on response content or business rules
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

### Backoff Strategies

`aresilient` supports multiple backoff strategies including exponential (default), linear, Fibonacci,
and constant backoff. You can also implement custom strategies. See the
[Backoff Strategies](https://durandtibo.github.io/aresilient/backoff_strategies/) documentation
for detailed examples and guidance.

```python
from aresilient import get_with_automatic_retry, LinearBackoff

# Use linear backoff instead of exponential
response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=LinearBackoff(base_delay=1.0),  # 1s, 2s, 3s, 4s...
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

### Callbacks and Observability

`aresilient` provides a callback/event system for observability, enabling you to hook into the retry lifecycle for logging, metrics, alerting, and custom behavior.

#### Available Callbacks

- **`on_request`**: Called before each request attempt
- **`on_retry`**: Called before each retry (after backoff delay)
- **`on_success`**: Called when a request succeeds
- **`on_failure`**: Called when all retries are exhausted

#### Example: Logging Retries

```python
from aresilient import get_with_automatic_retry


def log_request(info):
    print(
        f"Attempting {info.method} {info.url} (attempt {info.attempt}/{info.max_retries + 1})"
    )


def log_retry(info):
    print(
        f"Retrying {info.method} {info.url} after {info.wait_time:.2f}s "
        f"(attempt {info.attempt}/{info.max_retries + 1}), "
        f"status={info.status_code}, error={info.error}"
    )


def log_success(info):
    print(
        f"Success! {info.method} {info.url} on attempt {info.attempt} "
        f"({info.total_time:.2f}s total)"
    )


def log_failure(info):
    print(
        f"Failed! {info.method} {info.url} after {info.attempt} attempts "
        f"({info.total_time:.2f}s total), final error: {info.error}"
    )


# Use callbacks to monitor request behavior
response = get_with_automatic_retry(
    "https://api.example.com/data",
    on_request=log_request,
    on_retry=log_retry,
    on_success=log_success,
    on_failure=log_failure,
)
```

#### Example: Metrics Collection

```python
from aresilient import get_with_automatic_retry


class MetricsCollector:
    def __init__(self):
        self.retry_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_time = 0.0

    def on_retry(self, info):
        self.retry_count += 1

    def on_success(self, info):
        self.success_count += 1
        self.total_time += info.total_time

    def on_failure(self, info):
        self.failure_count += 1
        self.total_time += info.total_time


metrics = MetricsCollector()

# Make multiple requests with metrics collection
for url in urls:
    try:
        response = get_with_automatic_retry(
            url,
            on_retry=metrics.on_retry,
            on_success=metrics.on_success,
            on_failure=metrics.on_failure,
        )
    except Exception:
        pass  # Metrics already recorded in on_failure

print(f"Total retries: {metrics.retry_count}")
print(f"Successes: {metrics.success_count}")
print(f"Failures: {metrics.failure_count}")
print(
    f"Average time: {metrics.total_time / (metrics.success_count + metrics.failure_count):.2f}s"
)
```

#### Callback Information

Each callback receives a dataclass with relevant information:

**`RequestInfo`** (for `on_request`):
- `url`: The URL being requested
- `method`: HTTP method (e.g., "GET", "POST")
- `attempt`: Current attempt number (1-indexed)
- `max_retries`: Maximum retry attempts configured

**`RetryInfo`** (for `on_retry`):
- `url`: The URL being requested
- `method`: HTTP method
- `attempt`: Current attempt number (1-indexed)
- `max_retries`: Maximum retry attempts configured
- `wait_time`: Sleep time in seconds before this retry
- `error`: Exception that triggered the retry (if any)
- `status_code`: HTTP status code that triggered retry (if any)

**`ResponseInfo`** (for `on_success`):
- `url`: The URL that was requested
- `method`: HTTP method
- `attempt`: Attempt number that succeeded (1-indexed)
- `max_retries`: Maximum retry attempts configured
- `response`: The successful HTTP response object
- `total_time`: Total time spent on all attempts (seconds)

**`FailureInfo`** (for `on_failure`):
- `url`: The URL that was requested
- `method`: HTTP method
- `attempt`: Final attempt number (1-indexed)
- `max_retries`: Maximum retry attempts configured
- `error`: The final exception that caused failure
- `status_code`: Final HTTP status code (if any)
- `total_time`: Total time spent on all attempts (seconds)

All callbacks work with both synchronous and async functions.

### Circuit Breaker Pattern

The circuit breaker pattern helps prevent cascading failures by automatically stopping requests to a failing service after a threshold of consecutive failures is reached. The circuit breaker has three states:

- **CLOSED**: Normal operation, requests are allowed
- **OPEN**: After N consecutive failures, requests fail fast without being attempted
- **HALF_OPEN**: After a recovery timeout, one test request is allowed to check if the service has recovered

#### Basic Usage

```python
from aresilient import CircuitBreaker, CircuitBreakerError, get_with_automatic_retry

# Create a circuit breaker instance
circuit_breaker = CircuitBreaker(
    failure_threshold=5,  # Open circuit after 5 consecutive failures
    recovery_timeout=60.0,  # Try again after 60 seconds
)

# Use the circuit breaker with requests
try:
    response = get_with_automatic_retry(
        "https://api.example.com/data",
        circuit_breaker=circuit_breaker,
    )
except CircuitBreakerError:
    # Circuit is open, service is unavailable
    print("Service is temporarily unavailable, please try again later")
```

#### Sharing Circuit Breaker Across Requests

A single circuit breaker instance can be shared across multiple requests to protect a specific service:

```python
from aresilient import CircuitBreaker, get_with_automatic_retry

# Create a shared circuit breaker for a specific API
api_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

# Use it for multiple endpoints of the same service
for endpoint in ["/users", "/posts", "/comments"]:
    try:
        response = get_with_automatic_retry(
            f"https://api.example.com{endpoint}",
            circuit_breaker=api_circuit_breaker,
        )
        process_response(response)
    except CircuitBreakerError:
        print(f"Service unavailable for {endpoint}")
```

#### Advanced Configuration

```python
from aresilient import CircuitBreaker, HttpRequestError


def on_state_change(old_state, new_state):
    """Called when circuit breaker state changes."""
    print(f"Circuit breaker: {old_state.value} -> {new_state.value}")


# Circuit breaker with custom configuration
circuit_breaker = CircuitBreaker(
    failure_threshold=3,  # Lower threshold for faster detection
    recovery_timeout=30.0,  # Shorter recovery window
    expected_exception=HttpRequestError,  # Only count specific exceptions
    on_state_change=on_state_change,  # Monitor state changes
)
```

#### Monitoring Circuit State

```python
from aresilient import CircuitBreaker, CircuitState

circuit_breaker = CircuitBreaker(failure_threshold=5)

# Check current state
print(f"State: {circuit_breaker.state}")  # CircuitState.CLOSED
print(f"Failures: {circuit_breaker.failure_count}")  # 0

# Manually reset if needed (use with caution)
if circuit_breaker.state == CircuitState.OPEN:
    circuit_breaker.reset()
```

#### Benefits

- **Prevent Cascading Failures**: Stop making requests to a failing service before it becomes completely overwhelmed
- **Fail Fast**: Immediately return errors when the circuit is open instead of waiting for timeouts
- **Automatic Recovery Testing**: Automatically tests if the service has recovered after the timeout
- **Protect Multiple Services**: Use different circuit breakers for different backend services
- **Graceful Degradation**: Handle circuit breaker errors to provide fallback functionality

## Configuration

### Default Settings

- **Timeout**: 10.0 seconds
- **Max Retries**: 3 (4 total attempts including the initial request)
- **Backoff Factor**: 0.3
- **Retryable Status Codes**: 429 (Too Many Requests), 500 (Internal Server Error), 502 (Bad
  Gateway), 503 (Service Unavailable), 504 (Gateway Timeout)

### Backoff Strategies

By default, the library uses **exponential backoff**, where the wait time between retries doubles
with each attempt. You can choose from several built-in strategies or implement your own:

- **ExponentialBackoff** (default): `base_delay * (2 ** attempt)` - Doubles delay each retry
- **LinearBackoff**: `base_delay * (attempt + 1)` - Increases delay linearly
- **FibonacciBackoff**: `base_delay * fib(attempt + 1)` - Fibonacci sequence delays
- **ConstantBackoff**: Fixed delay for all retries

All strategies support an optional `max_delay` parameter to cap the maximum wait time.

#### Default Exponential Backoff Formula

When not using a custom backoff strategy, the wait time is calculated as:

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
- `on_request` (Callable[[RequestInfo], None] | None): Callback called before each request attempt
- `on_retry` (Callable[[RetryInfo], None] | None): Callback called before each retry
- `on_success` (Callable[[ResponseInfo], None] | None): Callback called when request succeeds
- `on_failure` (Callable[[FailureInfo], None] | None): Callback called when all retries are exhausted
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
- `jitter_factor` (float): Factor for adding random jitter to backoff delays (0.0-1.0, default: 0.0)
- `retry_if` (Callable[[httpx.Response | None, Exception | None], bool] | None): Custom predicate function to determine whether to retry
- `on_request` (Callable[[RequestInfo], None] | None): Callback called before each request attempt
- `on_retry` (Callable[[RetryInfo], None] | None): Callback called before each retry
- `on_success` (Callable[[ResponseInfo], None] | None): Callback called when request succeeds
- `on_failure` (Callable[[FailureInfo], None] | None): Callback called when all retries are exhausted
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
- `jitter_factor` (float): Factor for adding random jitter to backoff delays (0.0-1.0, default: 0.0)
- `retry_if` (Callable[[httpx.Response | None, Exception | None], bool] | None): Custom predicate function to determine whether to retry
- `on_request` (Callable[[RequestInfo], None] | None): Callback called before each request attempt
- `on_retry` (Callable[[RetryInfo], None] | None): Callback called before each retry
- `on_success` (Callable[[ResponseInfo], None] | None): Callback called when request succeeds
- `on_failure` (Callable[[FailureInfo], None] | None): Callback called when all retries are exhausted
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
- `jitter_factor` (float): Factor for adding random jitter to backoff delays (0.0-1.0, default: 0.0)
- `retry_if` (Callable[[httpx.Response | None, Exception | None], bool] | None): Custom predicate function to determine whether to retry
- `on_request` (Callable[[RequestInfo], None] | None): Callback called before each request attempt
- `on_retry` (Callable[[RetryInfo], None] | None): Callback called before each retry
- `on_success` (Callable[[ResponseInfo], None] | None): Callback called when request succeeds
- `on_failure` (Callable[[FailureInfo], None] | None): Callback called when all retries are exhausted
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
- `jitter_factor` (float): Factor for adding random jitter to backoff delays (0.0-1.0, default: 0.0)
- `retry_if` (Callable[[httpx.Response | None, Exception | None], bool] | None): Custom predicate function to determine whether to retry
- `on_request` (Callable[[RequestInfo], None] | None): Callback called before each request attempt
- `on_retry` (Callable[[RetryInfo], None] | None): Callback called before each retry
- `on_success` (Callable[[ResponseInfo], None] | None): Callback called when request succeeds
- `on_failure` (Callable[[FailureInfo], None] | None): Callback called when all retries are exhausted
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
- `jitter_factor` (float): Factor for adding random jitter to backoff delays (0.0-1.0, default: 0.0)
- `retry_if` (Callable[[httpx.Response | None, Exception | None], bool] | None): Custom predicate function to determine whether to retry
- `on_request` (Callable[[RequestInfo], None] | None): Callback called before each request attempt
- `on_retry` (Callable[[RetryInfo], None] | None): Callback called before each retry
- `on_success` (Callable[[ResponseInfo], None] | None): Callback called when request succeeds
- `on_failure` (Callable[[FailureInfo], None] | None): Callback called when all retries are exhausted
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
- `jitter_factor` (float): Factor for adding random jitter to backoff delays (0.0-1.0, default: 0.0)
- `retry_if` (Callable[[httpx.Response | None, Exception | None], bool] | None): Custom predicate function to determine whether to retry
- `on_request` (Callable[[RequestInfo], None] | None): Callback called before each request attempt
- `on_retry` (Callable[[RetryInfo], None] | None): Callback called before each retry
- `on_success` (Callable[[ResponseInfo], None] | None): Callback called when request succeeds
- `on_failure` (Callable[[FailureInfo], None] | None): Callback called when all retries are exhausted
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
