# User Guide

This guide provides comprehensive instructions on how to use `aresilient` for making resilient HTTP
requests with automatic retry logic.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Async Usage](#async-usage)
- [Configuration Options](#configuration-options)
- [Context Manager API](#context-manager-api)
- [Advanced Usage](#advanced-usage)
- [Circuit Breaker Pattern](#circuit-breaker-pattern)
- [Custom Retry Predicates](#custom-retry-predicates)
- [Callbacks and Observability](#callbacks-and-observability)
- [Error Handling](#error-handling)
- [Custom HTTP Methods](#custom-http-methods)
- [Best Practices](#best-practices)

## Basic Usage

### Making GET Requests

The simplest way to make an HTTP GET request with automatic retry:

```python
from aresilient import get

# Basic GET request
response = get("https://api.example.com/users")
print(response.json())
```

### Making POST Requests

POST requests work similarly with support for JSON payloads and form data:

```python
from aresilient import post

# POST with JSON payload
response = post(
    "https://api.example.com/users",
    json={"name": "John Doe", "email": "john@example.com"},
)
print(response.status_code)

# POST with form data
response = post(
    "https://api.example.com/submit", data={"field1": "value1", "field2": "value2"}
)
```

### Other HTTP Methods

`aresilient` supports all common HTTP methods:

```python
from aresilient import (
    put,
    delete,
    patch,
)

# PUT request to update a resource
response = put("https://api.example.com/resource/123", json={"name": "updated"})

# DELETE request to remove a resource
response = delete("https://api.example.com/resource/123")

# PATCH request to partially update a resource
response = patch("https://api.example.com/resource/123", json={"status": "active"})
```

## Async Usage

`aresilient` provides asynchronous versions of all HTTP methods for use in async applications.
All async functions have the same parameters as their synchronous counterparts.

### Making Async GET Requests

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

### Making Async POST Requests

```python
import asyncio
from aresilient import post_async


async def create_user():
    response = await post_async(
        "https://api.example.com/users",
        json={"name": "Jane Doe", "email": "jane@example.com"},
    )
    return response.status_code


# Run the async function
status = asyncio.run(create_user())
print(f"Status: {status}")
```

### Other Async HTTP Methods

All HTTP methods have async versions with identical parameters and callback support:

```python
from aresilient import (
    put_async,
    delete_async,
    patch_async,
    head_async,
    options_async,
)
```

**Note**: All async functions support the same parameters as their synchronous counterparts,
including:

- `max_retries`, `backoff_strategy`, `jitter_factor`
- `status_forcelist`, `retry_if`
- `on_request`, `on_retry`, `on_success`, `on_failure` callbacks

### Using Async with httpx.AsyncClient

For better performance with multiple async requests, reuse an `httpx.AsyncClient`:

```python
import asyncio
import httpx
from aresilient import get_async, post_async


async def fetch_multiple_resources():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Make multiple concurrent requests
        users_task = get_async("https://api.example.com/users", client=client)
        posts_task = get_async("https://api.example.com/posts", client=client)

        # Wait for both requests to complete
        users, posts = await asyncio.gather(users_task, posts_task)

        return users.json(), posts.json()


# Run the async function
users_data, posts_data = asyncio.run(fetch_multiple_resources())
```

### Concurrent Async Requests

Process multiple URLs concurrently for better performance:

```python
import asyncio
from aresilient import get_async


async def fetch_all(urls):
    tasks = [get_async(url) for url in urls]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    return responses


# Fetch multiple URLs concurrently
urls = [
    "https://api.example.com/data1",
    "https://api.example.com/data2",
    "https://api.example.com/data3",
]
responses = asyncio.run(fetch_all(urls))
```

## Configuration Options

### Default Configuration

`aresilient` comes with sensible defaults:

```python
from aresilient import (
    DEFAULT_TIMEOUT,  # 10.0 seconds
    DEFAULT_MAX_RETRIES,  # 3 retries (4 total attempts)
    RETRY_STATUS_CODES,  # (429, 500, 502, 503, 504)
)

print(f"Timeout: {DEFAULT_TIMEOUT}")
print(f"Max retries: {DEFAULT_MAX_RETRIES}")
print(f"Retry on status codes: {RETRY_STATUS_CODES}")
```

### Customizing Timeout

Control how long to wait for a server response:

```python
from aresilient import get

# Short timeout for quick responses
response = get("https://api.example.com/health", timeout=5.0)  # 5 seconds

# Longer timeout for slow endpoints
response = get("https://api.example.com/slow-endpoint", timeout=60.0)  # 60 seconds
```

You can also use httpx.Timeout for fine-grained control:

```python
import httpx
from aresilient import get

# Different timeouts for different operations
timeout = httpx.Timeout(
    connect=5.0,  # 5 seconds to establish connection
    read=30.0,  # 30 seconds to read response
    write=10.0,  # 10 seconds to send request
    pool=5.0,  # 5 seconds to get connection from pool
)

response = get("https://api.example.com/data", timeout=timeout)
```

### Customizing Retry Behavior

Control how many times and how long between retries:

```python
from aresilient import get
from aresilient.backoff import ExponentialBackoff

# More aggressive retry
response = get(
    "https://api.example.com/data",
    max_retries=5,
    backoff_strategy=ExponentialBackoff(base_delay=0.5),  # Longer waits between retries
)

# Less aggressive retry
response = get(
    "https://api.example.com/data",
    max_retries=1,
    backoff_strategy=ExponentialBackoff(base_delay=0.1),  # Shorter waits between retries
)

# With jitter to prevent thundering herd
response = get(
    "https://api.example.com/data",
    max_retries=3,
    backoff_strategy=ExponentialBackoff(base_delay=0.5),
    jitter_factor=0.1,  # Add 10% random jitter
)

# No retry
response = get(
    "https://api.example.com/data", max_retries=0  # No retries, fail immediately
)
```

### Understanding Backoff Strategies

`aresilient` supports multiple backoff strategies to control the wait time between retry attempts.
By default, exponential backoff is used.

#### Exponential Backoff (Default)

The wait time between retries is calculated using the exponential backoff formula:

```
base_wait_time = base_delay * (2 ** attempt)
# If jitter_factor is set (e.g., 0.1 for 10% jitter):
jitter = random(0, jitter_factor) * base_wait_time
total_wait_time = base_wait_time + jitter
```

Where `attempt` is 0-indexed (0, 1, 2, ...).

##### Example with default `ExponentialBackoff(base_delay=0.3)` (no jitter):

- 1st retry: 0.3 * (2^0) = 0.3 seconds
- 2nd retry: 0.3 * (2^1) = 0.6 seconds
- 3rd retry: 0.3 * (2^2) = 1.2 seconds

##### Example with `ExponentialBackoff(base_delay=1.0)` and `jitter_factor=0.1`:

- 1st retry: 1.0-1.1 seconds (base 1.0s + up to 10% jitter)
- 2nd retry: 2.0-2.2 seconds (base 2.0s + up to 10% jitter)
- 3rd retry: 4.0-4.4 seconds (base 4.0s + up to 10% jitter)

**Note**: Jitter is optional (disabled by default with `jitter_factor=0`). When enabled, it's
randomized for each retry to prevent multiple clients from retrying simultaneously (thundering
herd problem). Set `jitter_factor=0.1` for 10% jitter, which is recommended for production use.

#### Using Different Backoff Strategies

You can use alternative backoff strategies by providing a `backoff_strategy` parameter:

```python
from aresilient import (
    get,
    LinearBackoff,
    FibonacciBackoff,
    ConstantBackoff,
    ExponentialBackoff,
)

# Linear backoff: 1s, 2s, 3s, 4s...
response = get(
    "https://api.example.com/data",
    backoff_strategy=LinearBackoff(base_delay=1.0, max_delay=10.0),
)

# Fibonacci backoff: 1s, 1s, 2s, 3s, 5s, 8s...
response = get(
    "https://api.example.com/data",
    backoff_strategy=FibonacciBackoff(base_delay=1.0, max_delay=10.0),
)

# Constant backoff: 2s, 2s, 2s, 2s...
response = get(
    "https://api.example.com/data",
    backoff_strategy=ConstantBackoff(delay=2.0),
)

# Explicit exponential backoff with custom settings
response = get(
    "https://api.example.com/data",
    backoff_strategy=ExponentialBackoff(base_delay=0.5, max_delay=30.0),
)
```

See the [Backoff Strategies](backoff_strategies.md) guide for detailed information about each
strategy and when to use them.

### Customizing Retryable Status Codes

By default, `aresilient` retries on status codes 429, 500, 502, 503, and 504. You can customize
this:

```python
from aresilient import get

# Only retry on rate limiting
response = get("https://api.example.com/data", status_forcelist=(429,))

# Retry on server errors and rate limiting
response = get(
    "https://api.example.com/data", status_forcelist=(429, 500, 502, 503, 504)
)

# Add custom status codes
response = get(
    "https://api.example.com/data",
    status_forcelist=(408, 429, 500, 502, 503, 504),  # Include 408 Request Timeout
)
```

### Retry-After Header Support

When a server returns a `Retry-After` header (commonly with 429 or 503 status codes), `aresilient`
automatically uses the server's suggested wait time instead of exponential backoff. This ensures
compliance with rate limiting and helps avoid overwhelming the server.

The `Retry-After` header supports two formats:

```python
# Server responds with: Retry-After: 120
# aresilient will wait 120 seconds before retrying

# Server responds with: Retry-After: Wed, 21 Oct 2015 07:28:00 GMT
# aresilient will wait until this time before retrying
```

The retry delay from the `Retry-After` header is used automatically - you don't need to configure
anything. This works with all HTTP methods (GET, POST, PUT, DELETE, PATCH).

**Note**: If `jitter_factor` is configured, jitter is still applied to server-specified
`Retry-After` values to prevent thundering herd issues when many clients receive the same retry
delay from a server.

### Max Total Time and Max Wait Time

Control the total time budget and maximum wait time for retries:

```python
from aresilient import get
from aresilient.backoff import ExponentialBackoff

# Limit total time for all retry attempts
response = get(
    "https://api.example.com/data",
    max_retries=10,
    max_total_time=30.0,  # Stop retrying after 30 seconds total
)

# Cap individual backoff delays
response = get(
    "https://api.example.com/data",
    max_retries=10,
    backoff_strategy=ExponentialBackoff(base_delay=2.0),
    max_wait_time=10.0,  # No single wait exceeds 10 seconds
)

# Combine both for strict SLA guarantees
response = get(
    "https://api.example.com/data",
    max_retries=10,
    backoff_strategy=ExponentialBackoff(base_delay=2.0),
    max_total_time=60.0,  # Total budget: 60 seconds
    max_wait_time=15.0,  # Max wait between retries: 15 seconds
)
```

**max_total_time** is useful when you have strict time budgets or SLA requirements. If the total
elapsed time (including all request attempts and backoff delays) exceeds this value, the retry
loop stops even if `max_retries` hasn't been reached.

**max_wait_time** caps individual backoff delays. This is particularly useful with exponential
backoff or when servers send very large `Retry-After` values. Without this cap, exponential
backoff could lead to very long waits (e.g., 64s, 128s, 256s).

## Context Manager API

The `ResilientClient` and `AsyncResilientClient` classes provide a context manager interface for
making multiple HTTP requests with shared retry configuration. This is more convenient and efficient
than passing the same parameters to every function call.

### Using ResilientClient (Sync)

```python
from aresilient import ResilientClient
from aresilient.backoff import LinearBackoff

# Create a client with shared configuration
with ResilientClient(
    max_retries=5,
    timeout=30.0,
    backoff_strategy=LinearBackoff(base_delay=1.0),
    jitter_factor=0.1,
) as client:
    # All requests use the shared configuration
    users = client.get("https://api.example.com/users")

    # Override configuration for specific requests
    posts = client.get(
        "https://api.example.com/posts",
        max_retries=3,  # Override max_retries for this request
    )

    # POST request
    result = client.post(
        "https://api.example.com/data",
        json={"key": "value"},
    )

    # PUT request
    updated = client.put(
        "https://api.example.com/resource/123",
        json={"status": "active"},
    )

    # DELETE request
    client.delete("https://api.example.com/resource/456")
```

### Using AsyncResilientClient (Async)

```python
import asyncio

from aresilient import AsyncResilientClient
from aresilient.backoff import ExponentialBackoff


async def fetch_all_data():
    async with AsyncResilientClient(
        max_retries=3,
        timeout=20.0,
        backoff_strategy=ExponentialBackoff(base_delay=0.5, max_delay=10.0),
    ) as client:
        # Concurrent async requests with shared configuration
        users_task = client.get("https://api.example.com/users")
        posts_task = client.get("https://api.example.com/posts")

        users, posts = await asyncio.gather(users_task, posts_task)

        # POST request
        result = await client.post(
            "https://api.example.com/submit",
            json={"data": "value"},
        )

        return users.json(), posts.json(), result.json()


data = asyncio.run(fetch_all_data())
```

### Supported Methods in Context Manager

Both `ResilientClient` and `AsyncResilientClient` support all HTTP methods:

- `client.get(url, **kwargs)` - GET request
- `client.post(url, **kwargs)` - POST request
- `client.put(url, **kwargs)` - PUT request
- `client.delete(url, **kwargs)` - DELETE request
- `client.patch(url, **kwargs)` - PATCH request
- `client.head(url, **kwargs)` - HEAD request
- `client.options(url, **kwargs)` - OPTIONS request
- `client.request(method, url, **kwargs)` - Custom method

### Benefits of Context Manager API

1. **Code Reusability**: Define retry configuration once, use for multiple requests
2. **Connection Pooling**: The underlying httpx client is reused, improving performance
3. **Cleaner Code**: Less repetition of configuration parameters
4. **Easy Override**: Per-request overrides of the default configuration
5. **Resource Management**: Automatic cleanup when exiting the context

### Context Manager with Callbacks

```python
from aresilient import ResilientClient


def log_retry(info):
    print(f"Retrying {info.url} after {info.wait_time:.2f}s")


def log_failure(info):
    print(f"Failed {info.url} after {info.attempt} attempts")


with ResilientClient(
    max_retries=3,
    on_retry=log_retry,
    on_failure=log_failure,
) as client:
    # All requests will use these callbacks
    response1 = client.get("https://api.example.com/data1")
    response2 = client.get("https://api.example.com/data2")
```

## Advanced Usage

### Using a Custom httpx Client

For advanced configurations like custom headers, authentication, or connection pooling:

```python
import httpx
from aresilient import get

# Create a client with custom headers
with httpx.Client(
    headers={"User-Agent": "MyApp/1.0", "Authorization": "Bearer your-token-here"}
) as client:
    response = get("https://api.example.com/protected", client=client)
    print(response.json())
```

### Reusing Client for Multiple Requests

When making multiple requests, reuse the same client for better performance:

```python
import httpx
from aresilient import get, post

with httpx.Client(headers={"Authorization": "Bearer token"}, timeout=30.0) as client:
    # Multiple requests using the same client
    users = get("https://api.example.com/users", client=client)

    posts = get("https://api.example.com/posts", client=client)

    result = post("https://api.example.com/data", client=client, json={"data": "value"})
```

### Passing Additional httpx Arguments

All `**kwargs` are passed directly to the underlying httpx methods:

```python
from aresilient import get, post

# GET with query parameters
response = get("https://api.example.com/search", params={"q": "python", "page": 1})

# GET with custom headers (without custom client)
response = get("https://api.example.com/data", headers={"X-Custom-Header": "value"})

# POST with files
with open("document.pdf", "rb") as f:
    response = post("https://api.example.com/upload", files={"file": f})

# POST with both data and files
response = post(
    "https://api.example.com/submit",
    data={"title": "My Document"},
    files={"attachment": open("file.txt", "rb")},
)
```

## Circuit Breaker Pattern

The circuit breaker pattern prevents cascading failures by failing fast when a service is
consistently unavailable. After a certain number of consecutive failures, the circuit "opens" and
immediately rejects requests without attempting them, giving the failing service time to recover.

### Understanding Circuit States

A circuit breaker has three states:

- **CLOSED**: Normal operation - requests are allowed through
- **OPEN**: After `failure_threshold` consecutive failures, the circuit opens and requests fail
  immediately without being attempted
- **HALF_OPEN**: After `recovery_timeout` seconds in OPEN state, one test request is allowed
  through to check if the service has recovered

### Basic Circuit Breaker Usage

```python
from aresilient import get
from aresilient.circuit_breaker import CircuitBreaker

# Create a circuit breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=5,  # Open after 5 consecutive failures
    recovery_timeout=60.0,  # Try again after 60 seconds
)

# Use with requests
try:
    response = get(
        "https://api.example.com/data",
        circuit_breaker=circuit_breaker,
    )
except Exception as e:
    print(f"Request failed: {e}")
```

### How Circuit Breaker Works

1. **Initially CLOSED**: All requests are attempted normally with retry logic
2. **After N consecutive failures**: Circuit opens (state becomes OPEN)
3. **While OPEN**: All requests fail immediately with `CircuitBreakerError`, no actual HTTP requests
   are made
4. **After recovery_timeout**: Circuit enters HALF_OPEN state
5. **In HALF_OPEN**: One test request is attempted
    - If successful: Circuit closes (back to CLOSED state)
    - If fails: Circuit reopens (back to OPEN state) for another recovery_timeout period

### Circuit Breaker with Multiple Endpoints

Share a circuit breaker across multiple endpoints:

```python
from aresilient import get
from aresilient.circuit_breaker import CircuitBreaker

# Shared circuit breaker for API service
api_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

# All requests to this API share the circuit breaker
response1 = get(
    "https://api.example.com/users",
    circuit_breaker=api_circuit,
)

response2 = get(
    "https://api.example.com/posts",
    circuit_breaker=api_circuit,
)
```

### Circuit Breaker with Context Manager

```python
from aresilient import ResilientClient
from aresilient.circuit_breaker import CircuitBreaker

# Create circuit breaker
circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

# Use with ResilientClient
with ResilientClient(
    max_retries=3,
    circuit_breaker=circuit,
) as client:
    # All requests share the circuit breaker
    response1 = client.get("https://api.example.com/data1")
    response2 = client.get("https://api.example.com/data2")
```

### Handling Circuit Breaker Errors

```python
from aresilient import get
from aresilient.circuit_breaker import CircuitBreaker, CircuitBreakerError

circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

try:
    response = get(
        "https://api.example.com/data",
        circuit_breaker=circuit,
    )
except CircuitBreakerError as e:
    print(f"Circuit breaker is open: {e}")
    # Service is down, use fallback or cached data
except Exception as e:
    print(f"Other error: {e}")
```

### Monitoring Circuit State

```python
from aresilient.circuit_breaker import CircuitBreaker, CircuitState

circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

# Check circuit state
if circuit.state == CircuitState.OPEN:
    print("Circuit is open - service is down")
elif circuit.state == CircuitState.CLOSED:
    print("Circuit is closed - service is healthy")
elif circuit.state == CircuitState.HALF_OPEN:
    print("Circuit is half-open - testing recovery")

# Access circuit metrics
print(f"Consecutive failures: {circuit.failure_count}")
```

### When to Use Circuit Breakers

Circuit breakers are most useful when:

1. **Calling external services**: Protect your application from external service outages
2. **Microservices architecture**: Prevent cascading failures across services
3. **Rate-limited APIs**: Avoid wasting attempts when you're blocked
4. **Expensive operations**: Save resources by not attempting doomed requests
5. **User-facing applications**: Fail fast and provide better user experience

### Circuit Breaker Best Practices

1. **Tune thresholds carefully**: Set `failure_threshold` based on expected failure patterns
2. **Appropriate recovery time**: Set `recovery_timeout` long enough for services to recover
3. **Monitor circuit state**: Log state transitions for observability
4. **Use with callbacks**: Combine with `on_failure` callbacks to track circuit opens
5. **Share circuits wisely**: Share circuit breakers for the same backend service, separate for
   different services

## Custom Retry Predicates

The `retry_if` parameter allows you to define custom logic for determining whether a request
should be retried based on the response content, headers, or business logic. This is more powerful
than `status_forcelist` alone.

### Basic Retry Predicate

```python
from aresilient import get


def should_retry(response, exception):
    """Custom retry logic.

    Args:
        response: httpx.Response or None if exception occurred
        exception: Exception or None if request succeeded

    Returns:
        True to retry, False to not retry
    """
    # Retry on exceptions
    if exception:
        return True

    # Retry on specific status codes
    if response.status_code in (429, 500, 502, 503, 504):
        return True

    # Don't retry on success
    return False


response = get(
    "https://api.example.com/data",
    retry_if=should_retry,
)
```

### Retry Based on Response Content

```python
from aresilient import get


def retry_on_error_field(response, exception):
    """Retry if response contains an error field."""
    # Always retry on exceptions
    if exception:
        return True

    # Don't retry on client errors (4xx except 429)
    if 400 <= response.status_code < 500 and response.status_code != 429:
        return False

    # Retry on server errors
    if response.status_code >= 500:
        return True

    # Check response body for application-level errors
    try:
        data = response.json()
        # Retry if API returned an error in the response
        if data.get("error") == "temporary_unavailable":
            return True
    except Exception:
        pass  # Can't parse JSON, use status code logic

    return False


response = get(
    "https://api.example.com/data",
    retry_if=retry_on_error_field,
    max_retries=5,
)
```

### Retry Based on Response Headers

```python
from aresilient import get


def retry_on_header(response, exception):
    """Retry based on custom response headers."""
    if exception:
        return True

    # Retry if server indicates the operation is still processing
    if response.headers.get("X-Processing") == "true":
        return True

    # Retry on rate limit
    if response.status_code == 429:
        return True

    # Retry on server errors
    if response.status_code >= 500:
        return True

    return False


response = get(
    "https://api.example.com/long-running-task",
    retry_if=retry_on_header,
    max_retries=10,
)
```

### Complex Business Logic

```python
from aresilient import post
import httpx


def complex_retry_logic(response, exception):
    """Complex retry logic for specific business requirements."""
    # Network errors and timeouts - always retry
    if isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)):
        return True

    # Other exceptions - don't retry
    if exception:
        return False

    # Success - don't retry
    if 200 <= response.status_code < 300:
        return False

    # Client errors (except specific ones) - don't retry
    if 400 <= response.status_code < 500:
        # Retry on rate limit and request timeout
        if response.status_code in (429, 408):
            return True
        return False

    # Server errors - check response content
    if response.status_code >= 500:
        try:
            error_data = response.json()
            # Don't retry on permanent errors
            if error_data.get("error_type") == "permanent":
                return False
            # Retry on transient errors
            if error_data.get("error_type") == "transient":
                return True
        except Exception:
            pass  # Can't parse, default to retry

        # Default: retry on 500-level errors
        return True

    return False


response = post(
    "https://api.example.com/process",
    json={"task": "data_processing"},
    retry_if=complex_retry_logic,
    max_retries=3,
)
```

### Combining retry_if with status_forcelist

When `retry_if` is provided, it takes precedence over `status_forcelist` for determining retry
behavior. However, you can reference `status_forcelist` logic within your predicate:

```python
from aresilient import get


def custom_with_defaults(response, exception):
    """Custom logic that falls back to default status codes."""
    if exception:
        return True

    # Custom logic first
    try:
        data = response.json()
        if data.get("retry_requested"):
            return True
    except Exception:
        pass

    # Fall back to common retry status codes
    return response.status_code in (429, 500, 502, 503, 504)


response = get(
    "https://api.example.com/data",
    retry_if=custom_with_defaults,
)
```

### Retry Predicate with Async

The `retry_if` predicate works identically with async functions:

```python
import asyncio
from aresilient import get_async


def should_retry_async(response, exception):
    """Note: Predicate itself is still synchronous."""
    if exception:
        return True
    return response.status_code >= 500


async def fetch_data():
    response = await get_async(
        "https://api.example.com/data",
        retry_if=should_retry_async,
    )
    return response.json()


data = asyncio.run(fetch_data())
```

### Use Cases for Custom Retry Predicates

1. **API-specific error codes**: Retry when API returns specific error codes in response body
2. **Polling operations**: Retry until resource is ready (based on response content)
3. **Idempotency checks**: Only retry idempotent operations
4. **Content validation**: Retry if response doesn't match expected schema
5. **Business rules**: Implement domain-specific retry logic
6. **Rate limiting**: Custom handling of rate limit responses with specific headers

### Best Practices for Retry Predicates

1. **Keep it simple**: Complex logic makes debugging harder
2. **Handle exceptions safely**: Wrap JSON parsing and other operations in try/except
3. **Document your logic**: Clearly explain why certain conditions trigger retries
4. **Test thoroughly**: Edge cases in retry logic can cause subtle bugs
5. **Consider performance**: The predicate is called for every response, keep it fast
6. **Default to safe behavior**: When in doubt, don't retry (especially for write operations)

## Callbacks and Observability

`aresilient` provides a comprehensive callback/event system for observability, enabling you to hook
into the retry lifecycle for logging, metrics collection, alerting, and custom behavior. This is
particularly useful for production applications where you need to monitor HTTP request patterns,
track retry rates, and integrate with your observability stack.

### Available Callbacks

The library provides four lifecycle hooks:

- **`on_request`**: Called before each request attempt (including the initial request)
- **`on_retry`**: Called before each retry (after backoff delay calculation)
- **`on_success`**: Called when a request succeeds
- **`on_failure`**: Called when all retries are exhausted and the request fails

All callbacks are optional and can be used independently or together. They work with both
synchronous and asynchronous functions.

### Callback Signatures

Each callback receives a dataclass with relevant information:

#### RequestInfo (for `on_request`)

```python
@dataclass
class RequestInfo:
    url: str  # The URL being requested
    method: str  # HTTP method (e.g., "GET", "POST")
    attempt: int  # Current attempt number (1-indexed, first attempt is 1)
    max_retries: int  # Maximum number of retry attempts configured
```

#### RetryInfo (for `on_retry`)

```python
@dataclass
class RetryInfo:
    url: str  # The URL being requested
    method: str  # HTTP method
    attempt: int  # Current attempt number (1-indexed, first retry is attempt 2)
    max_retries: int  # Maximum retry attempts configured
    wait_time: float  # Sleep time in seconds before this retry
    error: Exception | None  # Exception that triggered the retry (if any)
    status_code: int | None  # HTTP status code that triggered retry (if any)
```

#### ResponseInfo (for `on_success`)

```python
@dataclass
class ResponseInfo:
    url: str  # The URL that was requested
    method: str  # HTTP method
    attempt: int  # Attempt number that succeeded (1-indexed)
    max_retries: int  # Maximum retry attempts configured
    response: httpx.Response  # The successful HTTP response object
    total_time: float  # Total time spent on all attempts including backoff (seconds)
```

#### FailureInfo (for `on_failure`)

```python
@dataclass
class FailureInfo:
    url: str  # The URL that was requested
    method: str  # HTTP method
    attempt: int  # Final attempt number (1-indexed)
    max_retries: int  # Maximum retry attempts configured
    error: Exception  # The final exception that caused failure
    status_code: int | None  # Final HTTP status code (if any)
    total_time: float  # Total time spent on all attempts including backoff (seconds)
```

### Basic Logging Example

Track each phase of the request lifecycle:

```python
from aresilient import get


def log_request(info):
    print(
        f"[REQUEST] {info.method} {info.url} - Attempt {info.attempt}/{info.max_retries + 1}"
    )


def log_retry(info):
    reason = (
        f"status={info.status_code}"
        if info.status_code
        else f"error={type(info.error).__name__}"
    )
    print(
        f"[RETRY] {info.method} {info.url} - "
        f"Attempt {info.attempt}/{info.max_retries + 1}, "
        f"waiting {info.wait_time:.2f}s, reason={reason}"
    )


def log_success(info):
    print(
        f"[SUCCESS] {info.method} {info.url} - "
        f"Succeeded on attempt {info.attempt} "
        f"({info.total_time:.2f}s total, status={info.response.status_code})"
    )


def log_failure(info):
    reason = (
        f"status={info.status_code}"
        if info.status_code
        else f"error={type(info.error).__name__}"
    )
    print(
        f"[FAILURE] {info.method} {info.url} - "
        f"Failed after {info.attempt} attempts "
        f"({info.total_time:.2f}s total), reason={reason}"
    )


# Use callbacks for comprehensive logging
try:
    response = get(
        "https://api.example.com/data",
        max_retries=3,
        on_request=log_request,
        on_retry=log_retry,
        on_success=log_success,
        on_failure=log_failure,
    )
except Exception as e:
    pass  # Error already logged in on_failure
```

Example output:

```
[REQUEST] GET https://api.example.com/data - Attempt 1/4
[RETRY] GET https://api.example.com/data - Attempt 2/4, waiting 0.30s, reason=status=503
[REQUEST] GET https://api.example.com/data - Attempt 2/4
[RETRY] GET https://api.example.com/data - Attempt 3/4, waiting 0.60s, reason=status=503
[REQUEST] GET https://api.example.com/data - Attempt 3/4
[SUCCESS] GET https://api.example.com/data - Succeeded on attempt 3 (1.15s total, status=200)
```

### Metrics Collection Example

Track statistics across multiple requests:

```python
from aresilient import get


class RequestMetrics:
    """Collect metrics for HTTP requests with retries."""

    def __init__(self):
        self.total_requests = 0
        self.total_retries = 0
        self.successes = 0
        self.failures = 0
        self.total_time = 0.0
        self.retry_reasons = {}  # Track why retries happened

    def on_request(self, info):
        self.total_requests += 1

    def on_retry(self, info):
        self.total_retries += 1
        # Track retry reasons
        reason = info.status_code if info.status_code else type(info.error).__name__
        self.retry_reasons[reason] = self.retry_reasons.get(reason, 0) + 1

    def on_success(self, info):
        self.successes += 1
        self.total_time += info.total_time

    def on_failure(self, info):
        self.failures += 1
        self.total_time += info.total_time

    def summary(self):
        """Print a summary of collected metrics."""
        total_completed = self.successes + self.failures
        success_rate = (
            (self.successes / total_completed * 100) if total_completed > 0 else 0
        )
        avg_time = (self.total_time / total_completed) if total_completed > 0 else 0

        print(f"=== Request Metrics Summary ===")
        print(f"Total requests made: {self.total_requests}")
        print(f"Total retries: {self.total_retries}")
        print(f"Successes: {self.successes}")
        print(f"Failures: {self.failures}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Average time: {avg_time:.2f}s")
        print(f"Retry reasons: {self.retry_reasons}")


# Collect metrics across multiple requests
metrics = RequestMetrics()

urls = [
    "https://api.example.com/endpoint1",
    "https://api.example.com/endpoint2",
    "https://api.example.com/endpoint3",
]

for url in urls:
    try:
        response = get(
            url,
            on_request=metrics.on_request,
            on_retry=metrics.on_retry,
            on_success=metrics.on_success,
            on_failure=metrics.on_failure,
        )
    except Exception:
        pass  # Metrics already tracked

metrics.summary()
```

### Integration with Logging Frameworks

Integrate with Python's standard logging module:

```python
import logging
from aresilient import get

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("http_client")


def log_retry_event(info):
    """Log retry events with structured information."""
    logger.warning(
        "HTTP request retry",
        extra={
            "url": info.url,
            "method": info.method,
            "attempt": info.attempt,
            "max_retries": info.max_retries,
            "wait_time": info.wait_time,
            "status_code": info.status_code,
            "error": str(info.error) if info.error else None,
        },
    )


def log_failure_event(info):
    """Log failure events with full context."""
    logger.error(
        "HTTP request failed after retries",
        extra={
            "url": info.url,
            "method": info.method,
            "attempts": info.attempt,
            "total_time": info.total_time,
            "status_code": info.status_code,
            "error": str(info.error),
        },
    )


response = get(
    "https://api.example.com/data",
    on_retry=log_retry_event,
    on_failure=log_failure_event,
)
```

### Monitoring and Alerting

Send metrics to a monitoring system:

```python
from aresilient import get


class MonitoringClient:
    """Send metrics to your monitoring system (e.g., Prometheus, Datadog, CloudWatch)."""

    def __init__(self):
        # Initialize your metrics client here
        pass

    def increment_counter(self, metric_name, tags=None):
        """Increment a counter metric."""
        # Your implementation here
        pass

    def record_histogram(self, metric_name, value, tags=None):
        """Record a histogram/distribution value."""
        # Your implementation here
        pass


monitoring = MonitoringClient()


def track_retry(info):
    """Track retry events in monitoring system."""
    monitoring.increment_counter(
        "http.retries",
        tags={
            "method": info.method,
            "status_code": (
                str(info.status_code) if info.status_code else "network_error"
            ),
        },
    )


def track_success(info):
    """Track successful requests."""
    monitoring.increment_counter("http.success", tags={"method": info.method})
    monitoring.record_histogram(
        "http.duration", info.total_time, tags={"method": info.method}
    )


def track_failure(info):
    """Track failed requests."""
    monitoring.increment_counter(
        "http.failure",
        tags={
            "method": info.method,
            "status_code": (
                str(info.status_code) if info.status_code else "network_error"
            ),
        },
    )


response = get(
    "https://api.example.com/data",
    on_retry=track_retry,
    on_success=track_success,
    on_failure=track_failure,
)
```

### Async Callbacks

Callbacks work identically with async functions:

```python
import asyncio
from aresilient import get_async


async def async_log_retry(info):
    """Callbacks for async functions are still synchronous."""
    print(f"Retrying {info.url} after {info.wait_time:.2f}s")


async def fetch_data():
    response = await get_async("https://api.example.com/data", on_retry=async_log_retry)
    return response.json()


asyncio.run(fetch_data())
```

**Note**: Callbacks themselves are synchronous functions even when used with async HTTP methods. If
you need to perform async operations in callbacks (e.g., async logging), you'll need to handle that
separately.

### Custom Alerting on Failures

Send alerts when requests fail after all retries:

```python
from aresilient import post


def send_alert_on_failure(info):
    """Send an alert when a critical API request fails."""
    if "critical-api" in info.url:
        alert_message = (
            f"CRITICAL: API request failed!\n"
            f"URL: {info.url}\n"
            f"Method: {info.method}\n"
            f"Attempts: {info.attempt}\n"
            f"Total Time: {info.total_time:.2f}s\n"
            f"Error: {info.error}\n"
            f"Status Code: {info.status_code}"
        )
        # Send to your alerting system (PagerDuty, Slack, email, etc.)
        # send_slack_alert(alert_message)
        # send_email_alert(alert_message)
        print(alert_message)


try:
    response = post(
        "https://critical-api.example.com/important",
        json={"data": "value"},
        on_failure=send_alert_on_failure,
    )
except Exception:
    pass  # Alert already sent
```

### Combining Multiple Callbacks

You can use multiple callbacks together for comprehensive observability:

```python
from aresilient import get


class RequestObserver:
    """Comprehensive request observer combining logging, metrics, and alerting."""

    def __init__(self, logger, metrics, alerting):
        self.logger = logger
        self.metrics = metrics
        self.alerting = alerting

    def on_request(self, info):
        self.logger.debug(f"Starting {info.method} {info.url}")
        self.metrics.on_request(info)

    def on_retry(self, info):
        self.logger.warning(f"Retrying {info.method} {info.url}")
        self.metrics.on_retry(info)

    def on_success(self, info):
        self.logger.info(f"Success {info.method} {info.url} in {info.total_time:.2f}s")
        self.metrics.on_success(info)

    def on_failure(self, info):
        self.logger.error(f"Failed {info.method} {info.url}")
        self.metrics.on_failure(info)
        self.alerting.send_alert(info)


# Create observer with your components
observer = RequestObserver(logger, metrics, alerting)

# Use all callbacks
response = get(
    "https://api.example.com/data",
    on_request=observer.on_request,
    on_retry=observer.on_retry,
    on_success=observer.on_success,
    on_failure=observer.on_failure,
)
```

### Best Practices for Callbacks

1. **Keep callbacks lightweight**: Callbacks are called synchronously and will block the request
   flow. Avoid heavy computations or blocking I/O.

2. **Handle exceptions in callbacks**: If a callback raises an exception, it will propagate and
   potentially abort the request. Wrap callback code in try/except if needed.

3. **Use structured logging**: Include relevant context (URL, method, attempt number) in log
   messages for better debugging.

4. **Sample high-volume metrics**: For high-traffic applications, consider sampling metrics to
   reduce overhead.

5. **Separate concerns**: Use `on_retry` for retry-specific metrics, `on_success` for latency
   tracking, and `on_failure` for alerting.

## Error Handling

### Understanding HttpRequestError

`aresilient` raises `HttpRequestError` when a request fails after all retries:

```python
from aresilient import get, HttpRequestError

try:
    response = get("https://api.example.com/data")
except HttpRequestError as e:
    print(f"Request failed: {e}")
    print(f"Method: {e.method}")  # 'GET'
    print(f"URL: {e.url}")  # 'https://api.example.com/data'
    print(f"Status Code: {e.status_code}")  # e.g., 500
    if e.response:
        print(f"Response body: {e.response.text}")
```

### Common Error Scenarios

#### Timeout Errors

When a request times out after all retries:

```python
from aresilient import get, HttpRequestError

try:
    response = get("https://slow-api.example.com/data", timeout=1.0, max_retries=2)
except HttpRequestError as e:
    # status_code will be None for timeout errors
    if e.status_code is None:
        print("Request timed out")
```

#### Network Errors

When the connection fails (DNS errors, connection refused, etc.):

```python
from aresilient import get, HttpRequestError

try:
    response = get("https://nonexistent-domain.invalid")
except HttpRequestError as e:
    if e.status_code is None:
        print(f"Network error: {e}")
```

#### HTTP Error Responses

When the server returns an error status code:

```python
from aresilient import get, HttpRequestError

try:
    response = get("https://api.example.com/not-found")
except HttpRequestError as e:
    if e.status_code == 404:
        print("Resource not found")
    elif e.status_code == 401:
        print("Unauthorized")
    elif e.status_code == 403:
        print("Forbidden")
```

### Validating Responses

Check response status and content:

```python
from aresilient import get, HttpRequestError

try:
    response = get("https://api.example.com/data")

    # Response is automatically successful (2xx or 3xx)
    # if we get here
    data = response.json()

    # Additional validation if needed
    if "error" in data:
        print(f"API returned an error: {data['error']}")

except HttpRequestError as e:
    print(f"Request failed: {e}")
except ValueError as e:
    print(f"Invalid JSON response: {e}")
```

### Error Handling with Async

Error handling works the same way with async functions:

```python
import asyncio
from aresilient import get_async, HttpRequestError


async def fetch_with_error_handling():
    try:
        response = await get_async("https://api.example.com/data")
        return response.json()
    except HttpRequestError as e:
        print(f"Async request failed: {e}")
        print(f"Status Code: {e.status_code}")
        return None


result = asyncio.run(fetch_with_error_handling())
```

## Custom HTTP Methods

For HTTP methods not directly supported or for custom needs, use the
`request` and `request_async` functions.

### Synchronous Custom Requests

```python
import httpx
from aresilient import request

# Example: Using HEAD method
with httpx.Client() as client:
    response = request(
        url="https://api.example.com/resource",
        method="HEAD",
        request_func=client.head,
        max_retries=3,
    )
    print(f"Content-Length: {response.headers.get('content-length')}")

# Example: Using OPTIONS method
with httpx.Client() as client:
    response = request(
        url="https://api.example.com/resource",
        method="OPTIONS",
        request_func=client.options,
    )
    print(f"Allowed methods: {response.headers.get('allow')}")
```

### Async Custom Requests

```python
import asyncio
import httpx
from aresilient import request_async


async def make_custom_request():
    async with httpx.AsyncClient() as client:
        # Using HEAD method asynchronously
        response = await request_async(
            url="https://api.example.com/resource",
            method="HEAD",
            request_func=client.head,
            max_retries=3,
        )
        return response.headers.get("content-length")


content_length = asyncio.run(make_custom_request())
```

### Advanced Custom Request Example

```python
import httpx
from aresilient import request
from aresilient.backoff import ExponentialBackoff
from aresilient.core import ClientConfig


def custom_api_call():
    with httpx.Client(timeout=30.0) as client:
        # Custom request with specific retry configuration
        response = request(
            url="https://api.example.com/custom-endpoint",
            method="PATCH",
            request_func=client.patch,
            config=ClientConfig(
                max_retries=5,
                backoff_strategy=ExponentialBackoff(base_delay=1.0),
                status_forcelist=(429, 503),
            ),
            # Additional kwargs passed to client.patch
            json={"operation": "update", "value": 42},
            headers={"X-API-Version": "2.0"},
        )
        return response.json()
```

## Best Practices

### 1. Use Appropriate Timeouts

Set timeouts based on your expected response times:

```python
# Quick health check
response = get("https://api.example.com/health", timeout=5.0)

# Large data download
response = get("https://api.example.com/large-dataset", timeout=120.0)
```

### 2. Use Context Managers for Multiple Requests

When making multiple requests, use `ResilientClient` or `AsyncResilientClient` for better code
organization and connection pooling:

```python
from aresilient import ResilientClient

# Good: Use ResilientClient for multiple requests
with ResilientClient(max_retries=3, timeout=30.0) as client:
    for url in urls:
        response = client.get(url)
        process_response(response)

# Alternative: Reuse httpx client (more verbose)
import httpx
from aresilient import get

with httpx.Client() as client:
    for url in urls:
        response = get(url, client=client, max_retries=3)
        process_response(response)

# Bad: Creates new client for each request
from aresilient import get

for url in urls:
    response = get(url, max_retries=3)
    process_response(response)
```

### 3. Adjust Retry Strategy Based on Use Case

For user-facing operations, use fewer retries for faster failure:

```python
# User-facing: fail fast
response = get("https://api.example.com/user-data", max_retries=1, timeout=10.0)
```

For background jobs, use more retries:

```python
# Background job: be more resilient
from aresilient.backoff import ExponentialBackoff

response = get(
    "https://api.example.com/batch-process",
    max_retries=5,
    backoff_strategy=ExponentialBackoff(base_delay=1.0),
    timeout=60.0,
)
```

### 4. Handle Rate Limiting Gracefully

If you're hitting rate limits frequently, consider:

```python
# Increase backoff for rate-limited endpoints
from aresilient.backoff import ExponentialBackoff

response = get(
    "https://api.example.com/rate-limited",
    max_retries=5,
    backoff_strategy=ExponentialBackoff(base_delay=2.0),  # Longer waits
    status_forcelist=(429,),  # Only retry on rate limit
)
```

### 5. Use Async for I/O-Bound Operations

When making multiple HTTP requests, async can significantly improve performance:

```python
import asyncio
import httpx
from aresilient import get_async


async def fetch_all_data(urls):
    async with httpx.AsyncClient() as client:
        tasks = [get_async(url, client=client) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]


# Fetch 10 URLs concurrently instead of sequentially
urls = [f"https://api.example.com/item/{i}" for i in range(10)]
results = asyncio.run(fetch_all_data(urls))
```

### 6. Choose Between Sync and Async Based on Your Application

**Use synchronous functions when:**

- Your application is not using asyncio
- You're making single, occasional requests
- Your code is primarily synchronous
- You're writing simple scripts or command-line tools

**Use async functions when:**

- Your application already uses asyncio
- You need to make multiple concurrent requests
- You're building a web application (e.g., FastAPI, Sanic)
- Performance and scalability are critical

```python
# Synchronous example - simple script
from aresilient import get

response = get("https://api.example.com/data")
print(response.json())
```

```python
# Async example - FastAPI application
from fastapi import FastAPI
from aresilient import get_async

app = FastAPI()


@app.get("/fetch-data")
async def fetch_data():
    response = await get_async("https://api.example.com/data")
    return response.json()
```

### 7. Enable Debug Logging for Troubleshooting

`aresilient` uses Python's standard `logging` module to provide detailed debug information about
retries, backoff times, and errors. This can be helpful for troubleshooting issues or understanding
retry behavior.

```python
import logging
from aresilient import get

# Enable debug logging to see retry details
logging.basicConfig(level=logging.DEBUG)

# This will log:
# - Each retry attempt
# - Wait times between retries
# - Whether Retry-After header is being used
# - Success/failure of each attempt
response = get("https://api.example.com/data")
```

Example debug output:

```
DEBUG:aresilient.request:GET request to https://api.example.com/data failed with status 503 (attempt 1/4)
DEBUG:aresilient.utils:Waiting 0.30s before retry
DEBUG:aresilient.request:GET request to https://api.example.com/data succeeded on attempt 2
```

For production use, keep the default log level (INFO or WARNING) to avoid excessive logging.

### 8. Use Circuit Breakers for External Dependencies

Protect your application from cascading failures when calling external services:

```python
from aresilient import ResilientClient
from aresilient.circuit_breaker import CircuitBreaker

# Create circuit breakers for different services
payment_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
user_service_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

# Use with different endpoints
with ResilientClient(circuit_breaker=payment_circuit) as client:
    response = client.post(
        "https://payment-api.example.com/charge", json={"amount": 100}
    )

with ResilientClient(circuit_breaker=user_service_circuit) as client:
    response = client.get("https://user-api.example.com/profile")
```

### 9. Set Time Budgets for Strict SLAs

Use `max_total_time` when you have strict time constraints:

```python
from aresilient import get

# Critical user-facing operation with 5-second SLA
response = get(
    "https://api.example.com/critical-data",
    max_retries=10,  # Try many times...
    max_total_time=5.0,  # ...but stop after 5 seconds total
    max_wait_time=2.0,  # ...and don't wait more than 2s between attempts
)
```

### 10. Choose the Right Backoff Strategy

Select backoff strategies based on your use case:

```python
from aresilient import (
    get,
    ExponentialBackoff,
    LinearBackoff,
    ConstantBackoff,
)

# Exponential: Most services (default)
response = get(
    "https://api.example.com/data",
    backoff_strategy=ExponentialBackoff(base_delay=0.5, max_delay=30.0),
)

# Linear: Predictable recovery times
response = get(
    "https://api.example.com/stable-service",
    backoff_strategy=LinearBackoff(base_delay=1.0, max_delay=10.0),
)

# Constant: Testing or specific API requirements
response = get(
    "https://api.example.com/polling-endpoint",
    backoff_strategy=ConstantBackoff(delay=2.0),
)
```

### 11. Use Custom Retry Predicates for Complex Logic

When status codes aren't enough, use `retry_if` for custom logic:

```python
from aresilient import post


def should_retry_payment(response, exception):
    """Custom retry logic for payment processing."""
    if exception:
        return True  # Retry on network errors

    if response.status_code >= 500:
        return True  # Retry on server errors

    # Check for specific business conditions
    try:
        data = response.json()
        # Retry on temporary payment processor issues
        if data.get("error_code") in ("temporary_unavailable", "rate_limit"):
            return True
    except Exception:
        pass

    return False


response = post(
    "https://payment-api.example.com/charge",
    json={"amount": 100},
    retry_if=should_retry_payment,
)
```

## Additional Resources

- [Backoff Strategies](backoff_strategies.md) - Detailed guide on backoff strategies
- [API Reference](refs/index.md) - Complete API documentation
- [Get Started](get_started.md) - Installation and setup instructions
- [httpx Documentation](https://www.python-httpx.org/) - Learn more about the underlying library
