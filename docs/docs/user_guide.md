# User Guide

This guide provides comprehensive instructions on how to use `aresnet` for making resilient HTTP
requests with automatic retry logic.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Async Usage](#async-usage)
- [Configuration Options](#configuration-options)
- [Advanced Usage](#advanced-usage)
- [Error Handling](#error-handling)
- [Custom HTTP Methods](#custom-http-methods)
- [Best Practices](#best-practices)

## Basic Usage

### Making GET Requests

The simplest way to make an HTTP GET request with automatic retry:

```python
from aresnet import get_with_automatic_retry

# Basic GET request
response = get_with_automatic_retry("https://api.example.com/users")
print(response.json())
```

### Making POST Requests

POST requests work similarly with support for JSON payloads and form data:

```python
from aresnet import post_with_automatic_retry

# POST with JSON payload
response = post_with_automatic_retry(
    "https://api.example.com/users",
    json={"name": "John Doe", "email": "john@example.com"},
)
print(response.status_code)

# POST with form data
response = post_with_automatic_retry(
    "https://api.example.com/submit", data={"field1": "value1", "field2": "value2"}
)
```

### Other HTTP Methods

`aresnet` supports all common HTTP methods:

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

## Async Usage

`aresnet` provides asynchronous versions of all HTTP methods for use in async applications.
All async functions have the same parameters as their synchronous counterparts.

### Making Async GET Requests

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

### Making Async POST Requests

```python
import asyncio
from aresnet import post_with_automatic_retry_async


async def create_user():
    response = await post_with_automatic_retry_async(
        "https://api.example.com/users",
        json={"name": "Jane Doe", "email": "jane@example.com"},
    )
    return response.status_code


# Run the async function
status = asyncio.run(create_user())
print(f"Status: {status}")
```

### Other Async HTTP Methods

All HTTP methods have async versions:

```python
from aresnet import (
    put_with_automatic_retry_async,
    delete_with_automatic_retry_async,
    patch_with_automatic_retry_async,
)
```

### Using Async with httpx.AsyncClient

For better performance with multiple async requests, reuse an `httpx.AsyncClient`:

```python
import asyncio
import httpx
from aresnet import get_with_automatic_retry_async, post_with_automatic_retry_async


async def fetch_multiple_resources():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Make multiple concurrent requests
        users_task = get_with_automatic_retry_async(
            "https://api.example.com/users", client=client
        )
        posts_task = get_with_automatic_retry_async(
            "https://api.example.com/posts", client=client
        )

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
from aresnet import get_with_automatic_retry_async


async def fetch_all(urls):
    tasks = [get_with_automatic_retry_async(url) for url in urls]
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

`aresnet` comes with sensible defaults:

```python
from aresnet import (
    DEFAULT_TIMEOUT,  # 10.0 seconds
    DEFAULT_MAX_RETRIES,  # 3 retries (4 total attempts)
    DEFAULT_BACKOFF_FACTOR,  # 0.3 seconds
    RETRY_STATUS_CODES,  # (429, 500, 502, 503, 504)
)

print(f"Timeout: {DEFAULT_TIMEOUT}")
print(f"Max retries: {DEFAULT_MAX_RETRIES}")
print(f"Backoff factor: {DEFAULT_BACKOFF_FACTOR}")
print(f"Retry on status codes: {RETRY_STATUS_CODES}")
```

### Customizing Timeout

Control how long to wait for a server response:

```python
from aresnet import get_with_automatic_retry

# Short timeout for quick responses
response = get_with_automatic_retry(
    "https://api.example.com/health", timeout=5.0  # 5 seconds
)

# Longer timeout for slow endpoints
response = get_with_automatic_retry(
    "https://api.example.com/slow-endpoint", timeout=60.0  # 60 seconds
)
```

You can also use httpx.Timeout for fine-grained control:

```python
import httpx
from aresnet import get_with_automatic_retry

# Different timeouts for different operations
timeout = httpx.Timeout(
    connect=5.0,  # 5 seconds to establish connection
    read=30.0,  # 30 seconds to read response
    write=10.0,  # 10 seconds to send request
    pool=5.0,  # 5 seconds to get connection from pool
)

response = get_with_automatic_retry("https://api.example.com/data", timeout=timeout)
```

### Customizing Retry Behavior

Control how many times and how long between retries:

```python
from aresnet import get_with_automatic_retry

# More aggressive retry
response = get_with_automatic_retry(
    "https://api.example.com/data",
    max_retries=5,  # Retry up to 5 times
    backoff_factor=0.5,  # Longer waits between retries
)

# Less aggressive retry
response = get_with_automatic_retry(
    "https://api.example.com/data",
    max_retries=1,  # Only retry once
    backoff_factor=0.1,  # Shorter waits between retries
)

# No retry
response = get_with_automatic_retry(
    "https://api.example.com/data", max_retries=0  # No retries, fail immediately
)
```

### Understanding Exponential Backoff

The wait time between retries is calculated using the exponential backoff formula:

```
wait_time = backoff_factor * (2 ** attempt)
```

Where `attempt` is 0-indexed (0, 1, 2, ...).

#### Example with default `backoff_factor=0.3`:

- 1st retry: 0.3 * (2^0) = 0.3 seconds
- 2nd retry: 0.3 * (2^1) = 0.6 seconds
- 3rd retry: 0.3 * (2^2) = 1.2 seconds

#### Example with `backoff_factor=1.0`:

- 1st retry: 1.0 * (2^0) = 1.0 seconds
- 2nd retry: 1.0 * (2^1) = 2.0 seconds
- 3rd retry: 1.0 * (2^2) = 4.0 seconds

### Customizing Retryable Status Codes

By default, `aresnet` retries on status codes 429, 500, 502, 503, and 504. You can customize this:

```python
from aresnet import get_with_automatic_retry

# Only retry on rate limiting
response = get_with_automatic_retry(
    "https://api.example.com/data", status_forcelist=(429,)
)

# Retry on server errors and rate limiting
response = get_with_automatic_retry(
    "https://api.example.com/data", status_forcelist=(429, 500, 502, 503, 504)
)

# Add custom status codes
response = get_with_automatic_retry(
    "https://api.example.com/data",
    status_forcelist=(408, 429, 500, 502, 503, 504),  # Include 408 Request Timeout
)
```

### Retry-After Header Support

When a server returns a `Retry-After` header (commonly with 429 or 503 status codes), `aresnet`
automatically uses the server's suggested wait time instead of exponential backoff. This ensures
compliance with rate limiting and helps avoid overwhelming the server.

The `Retry-After` header supports two formats:

```python
# Server responds with: Retry-After: 120
# aresnet will wait 120 seconds before retrying

# Server responds with: Retry-After: Wed, 21 Oct 2015 07:28:00 GMT
# aresnet will wait until this time before retrying
```

The retry delay from the `Retry-After` header is used automatically - you don't need to configure
anything. This works with all HTTP methods (GET, POST, PUT, DELETE, PATCH).

## Advanced Usage

### Using a Custom httpx Client

For advanced configurations like custom headers, authentication, or connection pooling:

```python
import httpx
from aresnet import get_with_automatic_retry

# Create a client with custom headers
with httpx.Client(
    headers={"User-Agent": "MyApp/1.0", "Authorization": "Bearer your-token-here"}
) as client:
    response = get_with_automatic_retry(
        "https://api.example.com/protected", client=client
    )
    print(response.json())
```

### Reusing Client for Multiple Requests

When making multiple requests, reuse the same client for better performance:

```python
import httpx
from aresnet import get_with_automatic_retry, post_with_automatic_retry

with httpx.Client(headers={"Authorization": "Bearer token"}, timeout=30.0) as client:
    # Multiple requests using the same client
    users = get_with_automatic_retry("https://api.example.com/users", client=client)

    posts = get_with_automatic_retry("https://api.example.com/posts", client=client)

    result = post_with_automatic_retry(
        "https://api.example.com/data", client=client, json={"data": "value"}
    )
```

### Passing Additional httpx Arguments

All `**kwargs` are passed directly to the underlying httpx methods:

```python
from aresnet import get_with_automatic_retry, post_with_automatic_retry

# GET with query parameters
response = get_with_automatic_retry(
    "https://api.example.com/search", params={"q": "python", "page": 1}
)

# GET with custom headers (without custom client)
response = get_with_automatic_retry(
    "https://api.example.com/data", headers={"X-Custom-Header": "value"}
)

# POST with files
with open("document.pdf", "rb") as f:
    response = post_with_automatic_retry(
        "https://api.example.com/upload", files={"file": f}
    )

# POST with both data and files
response = post_with_automatic_retry(
    "https://api.example.com/submit",
    data={"title": "My Document"},
    files={"attachment": open("file.txt", "rb")},
)
```

## Error Handling

### Understanding HttpRequestError

`aresnet` raises `HttpRequestError` when a request fails after all retries:

```python
from aresnet import get_with_automatic_retry, HttpRequestError

try:
    response = get_with_automatic_retry("https://api.example.com/data")
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
from aresnet import get_with_automatic_retry, HttpRequestError

try:
    response = get_with_automatic_retry(
        "https://slow-api.example.com/data", timeout=1.0, max_retries=2
    )
except HttpRequestError as e:
    # status_code will be None for timeout errors
    if e.status_code is None:
        print("Request timed out")
```

#### Network Errors

When the connection fails (DNS errors, connection refused, etc.):

```python
from aresnet import get_with_automatic_retry, HttpRequestError

try:
    response = get_with_automatic_retry("https://nonexistent-domain.invalid")
except HttpRequestError as e:
    if e.status_code is None:
        print(f"Network error: {e}")
```

#### HTTP Error Responses

When the server returns an error status code:

```python
from aresnet import get_with_automatic_retry, HttpRequestError

try:
    response = get_with_automatic_retry("https://api.example.com/not-found")
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
from aresnet import get_with_automatic_retry, HttpRequestError

try:
    response = get_with_automatic_retry("https://api.example.com/data")

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
from aresnet import get_with_automatic_retry_async, HttpRequestError


async def fetch_with_error_handling():
    try:
        response = await get_with_automatic_retry_async("https://api.example.com/data")
        return response.json()
    except HttpRequestError as e:
        print(f"Async request failed: {e}")
        print(f"Status Code: {e.status_code}")
        return None


result = asyncio.run(fetch_with_error_handling())
```

## Custom HTTP Methods

For HTTP methods not directly supported or for custom needs, use the
`request_with_automatic_retry` and `request_with_automatic_retry_async` functions.

### Synchronous Custom Requests

```python
import httpx
from aresnet import request_with_automatic_retry

# Example: Using HEAD method
with httpx.Client() as client:
    response = request_with_automatic_retry(
        url="https://api.example.com/resource",
        method="HEAD",
        request_func=client.head,
        max_retries=3,
    )
    print(f"Content-Length: {response.headers.get('content-length')}")

# Example: Using OPTIONS method
with httpx.Client() as client:
    response = request_with_automatic_retry(
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
from aresnet import request_with_automatic_retry_async


async def make_custom_request():
    async with httpx.AsyncClient() as client:
        # Using HEAD method asynchronously
        response = await request_with_automatic_retry_async(
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
from aresnet import request_with_automatic_retry


def custom_api_call():
    with httpx.Client(timeout=30.0) as client:
        # Custom request with specific retry configuration
        response = request_with_automatic_retry(
            url="https://api.example.com/custom-endpoint",
            method="PATCH",
            request_func=client.patch,
            max_retries=5,
            backoff_factor=1.0,
            status_forcelist=(429, 503),
            # Additional kwargs passed to client.patch
            json={"operation": "update", "value": 42},
            headers={"X-API-Version": "2.0"},
        )
        return response.json()
```

### Advanced: Using Jitter with Low-Level Functions

The low-level `request_with_automatic_retry` and `request_with_automatic_retry_async` functions
support an optional `jitter_factor` parameter to add randomized jitter to backoff delays. This
helps prevent the "thundering herd" problem where multiple clients retry simultaneously.

```python
import httpx
from aresnet import request_with_automatic_retry

with httpx.Client() as client:
    response = request_with_automatic_retry(
        url="https://api.example.com/data",
        method="GET",
        request_func=client.get,
        max_retries=5,
        backoff_factor=1.0,
        jitter_factor=0.1,  # Add 10% random jitter to backoff delays
    )
```

With `jitter_factor=0.1`, the wait time calculation becomes:

```
base_wait_time = backoff_factor * (2 ** retry_number)
jitter = random(0, 0.1) * base_wait_time
total_wait_time = base_wait_time + jitter
```

For example, with `backoff_factor=1.0` and `jitter_factor=0.1`:
- 1st retry: 1.0-1.1 seconds (base 1.0s + up to 10% jitter)
- 2nd retry: 2.0-2.2 seconds (base 2.0s + up to 10% jitter)
- 3rd retry: 4.0-4.4 seconds (base 4.0s + up to 10% jitter)

**Important Notes:**
- Jitter is only available in the low-level `request_with_automatic_retry` and
  `request_with_automatic_retry_async` functions
- Jitter is applied to both exponential backoff and `Retry-After` header values
- A `jitter_factor` of 0.1 (10% jitter) is recommended for production use to prevent thundering
  herd issues
- Set `jitter_factor=0` (default) to disable jitter

## Best Practices

### 1. Use Appropriate Timeouts

Set timeouts based on your expected response times:

```python
# Quick health check
response = get_with_automatic_retry("https://api.example.com/health", timeout=5.0)

# Large data download
response = get_with_automatic_retry(
    "https://api.example.com/large-dataset", timeout=120.0
)
```

### 2. Reuse HTTP Clients

When making multiple requests, reuse the client to benefit from connection pooling:

```python
import httpx
from aresnet import get_with_automatic_retry

# Good: Reuse client
with httpx.Client() as client:
    for url in urls:
        response = get_with_automatic_retry(url, client=client)
        process_response(response)

# Bad: Creates new client for each request
for url in urls:
    response = get_with_automatic_retry(url)
    process_response(response)
```

### 3. Adjust Retry Strategy Based on Use Case

For user-facing operations, use fewer retries for faster failure:

```python
# User-facing: fail fast
response = get_with_automatic_retry(
    "https://api.example.com/user-data", max_retries=1, timeout=10.0
)
```

For background jobs, use more retries:

```python
# Background job: be more resilient
response = get_with_automatic_retry(
    "https://api.example.com/batch-process",
    max_retries=5,
    backoff_factor=1.0,
    timeout=60.0,
)
```

### 4. Handle Rate Limiting Gracefully

If you're hitting rate limits frequently, consider:

```python
# Increase backoff for rate-limited endpoints
response = get_with_automatic_retry(
    "https://api.example.com/rate-limited",
    max_retries=5,
    backoff_factor=2.0,  # Longer waits
    status_forcelist=(429,),  # Only retry on rate limit
)
```

### 5. Use Async for I/O-Bound Operations

When making multiple HTTP requests, async can significantly improve performance:

```python
import asyncio
import httpx
from aresnet import get_with_automatic_retry_async


async def fetch_all_data(urls):
    async with httpx.AsyncClient() as client:
        tasks = [get_with_automatic_retry_async(url, client=client) for url in urls]
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
from aresnet import get_with_automatic_retry

response = get_with_automatic_retry("https://api.example.com/data")
print(response.json())
```

```python
# Async example - FastAPI application
from fastapi import FastAPI
from aresnet import get_with_automatic_retry_async

app = FastAPI()


@app.get("/fetch-data")
async def fetch_data():
    response = await get_with_automatic_retry_async("https://api.example.com/data")
    return response.json()
```

### 7. Enable Debug Logging for Troubleshooting

`aresnet` uses Python's standard `logging` module to provide detailed debug information about
retries, backoff times, and errors. This can be helpful for troubleshooting issues or understanding
retry behavior.

```python
import logging
from aresnet import get_with_automatic_retry

# Enable debug logging to see retry details
logging.basicConfig(level=logging.DEBUG)

# This will log:
# - Each retry attempt
# - Wait times between retries
# - Whether Retry-After header is being used
# - Success/failure of each attempt
response = get_with_automatic_retry("https://api.example.com/data")
```

Example debug output:
```
DEBUG:aresnet.request:GET request to https://api.example.com/data failed with status 503 (attempt 1/4)
DEBUG:aresnet.utils:Waiting 0.30s before retry
DEBUG:aresnet.request:GET request to https://api.example.com/data succeeded on attempt 2
```

For production use, keep the default log level (INFO or WARNING) to avoid excessive logging.

## Additional Resources

- [API Reference](refs/index.md) - Complete API documentation
- [Get Started](get_started.md) - Installation and setup instructions
- [httpx Documentation](https://www.python-httpx.org/) - Learn more about the underlying library
