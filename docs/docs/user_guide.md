# User Guide

This guide provides comprehensive instructions on how to use `aresnet` for making resilient HTTP
requests with automatic retry logic.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Configuration Options](#configuration-options)
- [Advanced Usage](#advanced-usage)
- [Error Handling](#error-handling)
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

## Additional Resources

- [API Reference](refs/index.md) - Complete API documentation
- [Get Started](get_started.md) - Installation and setup instructions
- [httpx Documentation](https://www.python-httpx.org/) - Learn more about the underlying library
