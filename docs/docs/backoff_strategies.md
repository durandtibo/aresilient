# Backoff Strategies

This guide explains the different backoff strategies available in `aresilient` and how to use them
to fine-tune retry behavior for your specific use case.

## Overview

Backoff strategies determine how long to wait between retry attempts when a request fails. Choosing
the right strategy can significantly improve the resilience and efficiency of your application when
dealing with transient failures or rate-limited APIs.

## Available Strategies

### Exponential Backoff (Default)

Exponential backoff doubles the delay with each retry attempt. This is the default strategy and
works well for most scenarios where you want progressively longer delays between retries.

**Formula:** `base_delay * (2 ** attempt)`

**When to use:**
- Most general-purpose retry scenarios
- Services that need time to recover from failures
- Preventing overwhelming a struggling service

**Example:**

```python
from aresilient import get_with_automatic_retry, ExponentialBackoff

# Explicit exponential backoff with max delay cap
response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=ExponentialBackoff(base_delay=0.5, max_delay=10.0),
)
# Delays: 0.5s, 1s, 2s, 4s, 8s, 10s (capped), 10s (capped)...
```

**Default behavior** (when no `backoff_strategy` is specified):

```python
from aresilient import get_with_automatic_retry

# Uses exponential backoff with backoff_factor
response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_factor=0.3,  # Equivalent to ExponentialBackoff(base_delay=0.3)
)
# Delays: 0.3s, 0.6s, 1.2s, 2.4s...
```

### Linear Backoff

Linear backoff provides evenly spaced retry delays, increasing linearly with each attempt. This is
useful for services with predictable recovery times.

**Formula:** `base_delay * (attempt + 1)`

**When to use:**
- Services that recover quickly and predictably
- Testing scenarios where you want consistent delays
- APIs with linear rate limit recovery

**Example:**

```python
from aresilient import get_with_automatic_retry, LinearBackoff

response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=LinearBackoff(base_delay=1.0),
)
# Delays: 1s, 2s, 3s, 4s, 5s...

# With max_delay cap
response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=LinearBackoff(base_delay=2.0, max_delay=8.0),
)
# Delays: 2s, 4s, 6s, 8s (capped), 8s (capped)...
```

### Fibonacci Backoff

Fibonacci backoff provides a middle ground between linear and exponential backoff, with delays
following the Fibonacci sequence. This provides a more gradual increase than exponential backoff.

**Formula:** `base_delay * fibonacci(attempt + 1)`

**When to use:**
- When exponential backoff is too aggressive
- Services that need gradual recovery time
- Balancing between quick retries and giving services time to recover

**Example:**

```python
from aresilient import get_with_automatic_retry, FibonacciBackoff

response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=FibonacciBackoff(base_delay=1.0),
)
# Delays: 1s, 1s, 2s, 3s, 5s, 8s, 13s...

# With max_delay cap
response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=FibonacciBackoff(base_delay=1.0, max_delay=10.0),
)
# Delays: 1s, 1s, 2s, 3s, 5s, 8s, 10s (capped)...
```

### Constant Backoff

Constant backoff uses a fixed delay for all retry attempts, regardless of the attempt number. This
is useful for testing or when you know the exact delay that works best.

**Formula:** `delay` (constant)

**When to use:**
- Testing and debugging scenarios
- APIs with specific retry delay requirements
- Situations where you know the optimal wait time

**Example:**

```python
from aresilient import get_with_automatic_retry, ConstantBackoff

response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=ConstantBackoff(delay=2.5),
)
# Delays: 2.5s, 2.5s, 2.5s, 2.5s...
```

## Custom Backoff Strategy

You can implement your own backoff strategy by subclassing `BackoffStrategy` and implementing the
`calculate()` method:

```python
from aresilient import get_with_automatic_retry, BackoffStrategy


class SquareBackoff(BackoffStrategy):
    """Custom backoff using square of attempt number."""

    def __init__(self, base_delay: float = 1.0):
        self.base_delay = base_delay

    def calculate(self, attempt: int) -> float:
        """Calculate delay as square of (attempt + 1)."""
        return self.base_delay * ((attempt + 1) ** 2)


response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=SquareBackoff(base_delay=0.5),
)
# Delays: 0.5s, 2s, 4.5s, 8s, 12.5s...
```

## Using Backoff Strategies with Jitter

Jitter adds randomization to backoff delays to prevent the "thundering herd" problem where multiple
clients retry simultaneously. Jitter works with all backoff strategies:

```python
from aresilient import get_with_automatic_retry, LinearBackoff

response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=LinearBackoff(base_delay=1.0),
    jitter_factor=0.1,  # Add up to 10% random jitter
)
# Delays: 1.0-1.1s, 2.0-2.2s, 3.0-3.3s...
```

## Retry-After Header Support

When a server returns a `Retry-After` header (commonly with 429 or 503 status codes), the library
automatically uses the server's suggested wait time instead of the configured backoff strategy.
This ensures compliance with server requirements:

```python
from aresilient import get_with_automatic_retry, ExponentialBackoff

response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=ExponentialBackoff(base_delay=1.0),
)
# If server returns "Retry-After: 60", waits 60 seconds
# Otherwise uses the configured strategy
```

## Max Delay Cap

Most strategies support an optional `max_delay` parameter to prevent extremely long waits:

```python
from aresilient import get_with_automatic_retry, ExponentialBackoff

response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=ExponentialBackoff(base_delay=1.0, max_delay=30.0),
    max_retries=10,
)
# Delays won't exceed 30 seconds, even with many retries
```

## Comparison of Strategies

Here's how different strategies compare for the first 6 retry attempts (with `base_delay=1.0`):

| Attempt | Exponential | Linear | Fibonacci | Constant |
|---------|-------------|--------|-----------|----------|
| 1       | 1s          | 1s     | 1s        | 1s       |
| 2       | 2s          | 2s     | 1s        | 1s       |
| 3       | 4s          | 3s     | 2s        | 1s       |
| 4       | 8s          | 4s     | 3s        | 1s       |
| 5       | 16s         | 5s     | 5s        | 1s       |
| 6       | 32s         | 6s     | 8s        | 1s       |

## Best Practices

1. **Use exponential backoff by default** - It works well for most scenarios and prevents
   overwhelming failing services.

2. **Add jitter in production** - Set `jitter_factor=0.1` to prevent thundering herd issues when
   multiple clients retry simultaneously.

3. **Set max_delay caps** - Prevent extremely long waits by setting a reasonable `max_delay`,
   especially with exponential or Fibonacci backoff.

4. **Respect Retry-After headers** - The library automatically honors these, but be aware that they
   take precedence over your configured strategy.

5. **Choose strategy based on service behavior**:
   - **Exponential**: Services that need increasing recovery time
   - **Linear**: Services with predictable recovery patterns
   - **Fibonacci**: When you want gradual increase without exponential growth
   - **Constant**: Testing or APIs with specific requirements

6. **Test your strategy** - Use different strategies in staging to find what works best for your
   specific API.

## Async Support

All backoff strategies work identically with async functions:

```python
from aresilient import get_with_automatic_retry_async, FibonacciBackoff


async def fetch_data():
    response = await get_with_automatic_retry_async(
        "https://api.example.com/data",
        backoff_strategy=FibonacciBackoff(base_delay=1.0, max_delay=10.0),
    )
    return response.json()
```

## Using with Context Managers

Backoff strategies work seamlessly with `ResilientClient` and `AsyncResilientClient`:

```python
from aresilient import ResilientClient, LinearBackoff, ConstantBackoff

# All requests in the context use the same backoff strategy
with ResilientClient(
    backoff_strategy=LinearBackoff(base_delay=1.0, max_delay=8.0),
    max_retries=5,
) as client:
    response1 = client.get("https://api.example.com/data1")
    response2 = client.post("https://api.example.com/data2", json={"key": "value"})

    # Override strategy for a specific request
    response3 = client.get(
        "https://api.example.com/data3",
        backoff_strategy=ConstantBackoff(delay=2.0),
    )
```

Async context manager example:

```python
import asyncio
from aresilient import AsyncResilientClient, ExponentialBackoff


async def fetch_all():
    async with AsyncResilientClient(
        backoff_strategy=ExponentialBackoff(base_delay=0.5, max_delay=15.0),
        max_retries=3,
    ) as client:
        results = await asyncio.gather(
            client.get("https://api.example.com/data1"),
            client.get("https://api.example.com/data2"),
            client.get("https://api.example.com/data3"),
        )
        return [r.json() for r in results]
```
