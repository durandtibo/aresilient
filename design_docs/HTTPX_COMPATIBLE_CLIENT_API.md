# httpx Client Wrapper Design for aresilient

**Date:** February 2026  
**Status:** 📋 Proposal (Updated)  
**Authors:** Design Team

---

## Executive Summary

This document proposes a design for extending the `aresilient` library to wrap existing `httpx.Client` and `httpx.AsyncClient` instances, making them resilient with automatic retry, backoff, circuit breaker, and other resilience features.

**Current State:**
- ✅ `ResilientClient` and `AsyncResilientClient` context managers exist
- ✅ Full HTTP method support (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- ✅ Comprehensive retry and resilience features
- ⚠️ `ResilientClient` creates its own internal httpx.Client
- ⚠️ Cannot wrap existing httpx.Client instances configured by users

**Proposed State:**
- ✅ Modify `ResilientClient` and `AsyncResilientClient` to accept existing httpx clients
- ✅ Enable wrapping of user-configured httpx.Client instances
- ✅ Maintain backward compatibility with existing API (auto-create if no client provided)
- ✅ Preserve all httpx.Client configuration (auth, headers, proxies, etc.)
- ✅ Add resilience features to any httpx client

**Key Design Decisions:**
1. **Client wrapping approach:** Accept httpx.Client as optional constructor parameter
2. **Backward compatibility:** Auto-create httpx.Client if not provided (current behavior)
3. **Lifecycle management:** User controls wrapped client lifecycle
4. **API simplicity:** Minimal changes to existing ResilientClient API

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Current Implementation Analysis](#2-current-implementation-analysis)
3. [Design Goals](#3-design-goals)
4. [Proposed Solution](#4-proposed-solution)
5. [API Design](#5-api-design)
6. [Implementation Strategy](#6-implementation-strategy)
7. [Migration Path](#7-migration-path)
8. [Examples](#8-examples)
9. [Backward Compatibility](#9-backward-compatibility)
10. [Trade-offs and Alternatives](#10-trade-offs-and-alternatives)
11. [Success Metrics](#11-success-metrics)
12. [Timeline and Phases](#12-timeline-and-phases)

---

## 1. Problem Statement

### 1.1 Current Situation

The `aresilient` library provides resilient HTTP request functionality with:
- Context manager clients: `ResilientClient` and `AsyncResilientClient`
- Standalone functions: `get_with_automatic_retry`, `post_with_automatic_retry`, etc.
- Comprehensive retry logic, backoff strategies, circuit breakers, and callbacks

However, the current implementation has limitations:
- `ResilientClient` creates its own internal `httpx.Client` with limited configuration
- Users cannot wrap their existing, pre-configured `httpx.Client` instances
- Users lose custom httpx configuration (auth, headers, cookies, proxies, etc.) when using ResilientClient
- Cannot add resilience to existing httpx clients without recreating them

### 1.2 User Pain Points

**Limited Configuration:**
```python
# User has a carefully configured httpx client
import httpx

client = httpx.Client(
    auth=httpx.BasicAuth('user', 'pass'),
    headers={'User-Agent': 'MyApp/1.0'},
    cookies={'session': 'abc123'},
    proxy='http://proxy.example.com:8080',
    http2=True,
    verify='/path/to/cert.pem',
)

# Cannot add resilience to this client - must recreate with ResilientClient
# This loses all the configuration above!
from aresilient import ResilientClient

with ResilientClient(max_retries=5) as resilient_client:
    # This uses a different client without the configuration above
    response = resilient_client.get('https://api.example.com/data')
```

**Issues:**
1. Users cannot preserve their httpx.Client configuration when adding resilience
2. Must choose between custom httpx configuration OR resilience features (can't have both)
3. Code duplication - must specify configuration in multiple places
4. Harder to incrementally add resilience to existing code

### 1.3 Desired State

Enable wrapping of existing httpx clients:
```python
# User has a carefully configured httpx client
import httpx

client = httpx.Client(
    auth=httpx.BasicAuth('user', 'pass'),
    headers={'User-Agent': 'MyApp/1.0'},
    cookies={'session': 'abc123'},
    proxy='http://proxy.example.com:8080',
    http2=True,
    verify='/path/to/cert.pem',
)

# Wrap it with ResilientClient to add resilience
from aresilient import ResilientClient

with ResilientClient(client=client, max_retries=5) as resilient_client:
    # Now uses the configured client WITH resilience features
    response = resilient_client.get('https://api.example.com/data')
```

---

## 2. Current Implementation Analysis

### 2.1 Existing Client Classes

**Current `ResilientClient` (385 lines):**
```python
class ResilientClient:
    def __init__(
        self,
        *,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
        jitter_factor: float = 0.0,
        retry_if: Callable | None = None,
        backoff_strategy: BackoffStrategy | None = None,
        max_total_time: float | None = None,
        max_wait_time: float | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        on_request: Callable | None = None,
        on_retry: Callable | None = None,
        on_success: Callable | None = None,
        on_failure: Callable | None = None,
    ) -> None:
        ...
    
    def __enter__(self) -> Self:
        """Create underlying httpx.Client"""
        self._client = httpx.Client(timeout=self._timeout)
        return self
    
    def __exit__(self, ...) -> None:
        """Close underlying httpx.Client"""
        self._client.close()
    
    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make request with retry logic"""
        ...
    
    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)
    
    # Similar for post, put, delete, patch, head, options
```

**Strengths:**
- ✅ Comprehensive resilience configuration
- ✅ Clean API for retry/backoff/circuit breaker features
- ✅ Context manager lifecycle management
- ✅ All HTTP methods supported
- ✅ Per-request configuration overrides

**Limitations:**
- ❌ Creates its own internal `httpx.Client` (line 135)
- ❌ Only accepts `timeout` parameter from httpx (loses auth, headers, cookies, proxy, etc.)
- ❌ Cannot wrap existing user-configured `httpx.Client` instances
- ❌ Users must choose between custom httpx configuration OR resilience (can't have both)

---

## 3. Design Goals

### 3.1 Primary Goals

1. **Client Wrapping:** Enable wrapping of existing httpx.Client instances with resilience features
2. **Configuration Preservation:** Preserve all httpx.Client configuration (auth, headers, cookies, proxy, etc.)
3. **Backward Compatibility:** Existing `ResilientClient` usage continues to work (auto-create if no client provided)
4. **Lifecycle Control:** User controls the lifecycle of the wrapped client
5. **Minimal API Changes:** Add single optional `client` parameter to existing API

### 3.2 Secondary Goals

1. **Gradual Migration:** Support incremental adoption - wrap existing clients without recreating them
2. **Clear Documentation:** Provide migration guides and examples
3. **Type Safety:** Maintain full type hints throughout
4. **Performance:** Minimal overhead from wrapping layer
5. **Testing:** Comprehensive test coverage for wrapped clients

### 3.3 Non-Goals

1. **Create New Client Classes:** Use existing `ResilientClient` and `AsyncResilientClient`
2. **Replace httpx.Client:** Not trying to be a drop-in replacement, just a wrapper
3. **Manage httpx Configuration:** Wrapped client retains its own configuration

---

## 4. Proposed Solution

### 4.1 Overview

Modify existing `ResilientClient` and `AsyncResilientClient` to accept optional `httpx.Client`/`httpx.AsyncClient` instances:

```python
# Current behavior (still supported)
with ResilientClient(max_retries=5, timeout=30) as client:
    response = client.get('https://api.example.com/data')

# New behavior (wrapping existing client)
import httpx
http_client = httpx.Client(auth=..., headers=..., proxy=...)
with ResilientClient(client=http_client, max_retries=5) as resilient:
    response = resilient.get('https://api.example.com/data')
```

### 4.2 Architecture

**Wrapper Pattern:**

```
┌─────────────────────────────────────────┐
│   ResilientClient (modified)            │
│   - Accepts optional httpx.Client       │
│   - Adds resilience features            │
│   - Delegates to wrapped client         │
└─────────────────────────────────────────┘
                 │
                 │ wraps (if provided)
                 ▼
┌─────────────────────────────────────────┐
│   httpx.Client (user-configured)        │
│   - Auth, headers, cookies, proxy       │
│   - HTTP/2, SSL verification            │
│   - Connection pooling                  │
└─────────────────────────────────────────┘
```

**Key Design Patterns:**

1. **Composition:** Wrap provided client or create new one if not provided
2. **Lifecycle Separation:** User manages wrapped client's lifecycle
3. **Method Delegation:** Delegate to wrapped client after applying retry logic
4. **Configuration Preservation:** Wrapped client retains all its configuration

### 4.3 Configuration Strategy

**Two modes of operation:**

**Mode 1: Auto-create client (current behavior - backward compatible)**
```python
ResilientClient(
    timeout=30.0,           # Used to create internal httpx.Client
    max_retries=5,          # Resilience parameter
    backoff_factor=0.5,     # Resilience parameter
)
```

**Mode 2: Wrap existing client (new behavior)**
```python
# User creates and configures httpx.Client
client = httpx.Client(
    auth=httpx.BasicAuth('user', 'pass'),
    headers={'User-Agent': 'MyApp/1.0'},
    timeout=30.0,
    proxy='http://proxy.example.com',
)

# Wrap it with resilience
ResilientClient(
    client=client,          # Wrap this client
    max_retries=5,          # Resilience parameter  
    backoff_factor=0.5,     # Resilience parameter
)
```

### 4.4 Lifecycle Management

**Key Principle:** ResilientClient delegates to the wrapped httpx.Client's context manager protocol by calling `__enter__` and `__exit__`, but only closes the client if it created it.

**Implementation Strategy:**

1. **Client Creation:** Happens in `__init__` (not `__enter__`)
   - If `client=None`: Create httpx.Client and set `_owns_client=True`
   - If `client` provided: Store it and set `_owns_client=False`

2. **Context Manager Entry:** Call wrapped client's `__enter__`
   - `ResilientClient.__enter__` calls `self._client.__enter__()`
   - This allows proper nesting and connection pool initialization

3. **Context Manager Exit:** Call wrapped client's `__exit__`, close only if owned
   - `ResilientClient.__exit__` calls `self._client.__exit__()`
   - Then closes client only if `_owns_client=True`

**Supported Usage Patterns:**

**Pattern 1: User manages httpx.Client lifecycle**
```python
import httpx
from aresilient import ResilientClient

# User creates and manages httpx.Client
http_client = httpx.Client(auth=..., headers=...)

# Wrap with ResilientClient (doesn't close http_client on exit)
with ResilientClient(client=http_client, max_retries=5) as resilient:
    response = resilient.post('https://api.example.com/data', json={'key': 'value'})

# User responsible for closing
http_client.close()
```

**Pattern 2: Nested context managers (RECOMMENDED)**
```python
import httpx
from aresilient import ResilientClient

# httpx.Client managed by its own context manager
with httpx.Client(auth=..., headers=...) as http_client:
    # ResilientClient calls http_client.__enter__ and __exit__
    with ResilientClient(client=http_client, max_retries=5) as resilient:
        response = resilient.post('https://api.example.com/data', json={'key': 'value'})
# httpx.Client automatically closed by its context manager
```

**Pattern 3: Auto-create (backward compatible)**
```python
from aresilient import ResilientClient

# ResilientClient creates and manages httpx.Client
with ResilientClient(timeout=30, max_retries=5) as client:
    response = client.get('https://api.example.com/data')
# httpx.Client automatically created and closed by ResilientClient
```

**Why `__enter__` and `__exit__` can be called multiple times:**

httpx.Client's `__enter__` and `__exit__` are designed to be idempotent and can be called multiple times:
- `__enter__` returns `self` and doesn't perform exclusive initialization
- `__exit__` handles cleanup but doesn't prevent re-entry
- Connection pools handle multiple enter/exit cycles gracefully

This design allows Pattern 2 to work correctly where both the httpx.Client context manager and ResilientClient context manager call `__enter__` and `__exit__` on the same httpx.Client instance.

**Recommendation:** Use Pattern 2 (nested context managers) for cleanest lifecycle management when wrapping existing clients. Pattern 1 is supported but requires manual cleanup.

---

## 5. API Design

### 5.1 Modified ResilientClient Interface

```python
class ResilientClient:
    """Synchronous context manager for resilient HTTP requests.
    
    This class wraps an httpx.Client instance (or creates one) and adds
    resilience features including automatic retry, exponential backoff,
    circuit breaker, and custom retry predicates.
    
    Args:
        client: Optional httpx.Client instance to wrap. If not provided,
            a new client will be created using the timeout parameter.
        timeout: Timeout for requests. Only used if client is not provided.
        max_retries: Maximum number of retry attempts. Default: 3.
        backoff_factor: Exponential backoff factor. Default: 0.3.
        status_forcelist: HTTP status codes to retry. Default: (429, 500, 502, 503, 504).
        jitter_factor: Random jitter factor for backoff. Default: 0.0.
        retry_if: Custom retry predicate function.
        backoff_strategy: Custom backoff strategy instance.
        max_total_time: Maximum total time for all retries.
        max_wait_time: Maximum backoff delay cap.
        circuit_breaker: Circuit breaker instance.
        on_request: Callback before each request.
        on_retry: Callback before each retry.
        on_success: Callback on successful request.
        on_failure: Callback on final failure.
    
    Example (Mode 1 - Auto-create client):
        ```python
        from aresilient import ResilientClient
        
        # ResilientClient creates its own httpx.Client
        with ResilientClient(timeout=30.0, max_retries=5) as client:
            response = client.get('https://api.example.com/data')
        ```
    
    Example (Mode 2 - Wrap existing client):
        ```python
        import httpx
        from aresilient import ResilientClient
        
        # Create configured httpx client
        http_client = httpx.Client(
            auth=httpx.BasicAuth('user', 'pass'),
            headers={'User-Agent': 'MyApp/1.0'},
            proxy='http://proxy.example.com',
        )
        
        # Wrap it with resilience
        with ResilientClient(client=http_client, max_retries=5) as resilient:
            response = resilient.get('https://api.example.com/data')
        ```
    
    Note:
        When wrapping an existing client, the user is responsible for closing
        the wrapped client. The ResilientClient will not close it on exit.
    """
    
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,  # NEW: Optional client to wrap
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
        jitter_factor: float = 0.0,
        retry_if: Callable[[httpx.Response | None, Exception | None], bool] | None = None,
        backoff_strategy: BackoffStrategy | None = None,
        max_total_time: float | None = None,
        max_wait_time: float | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        on_request: Callable[[RequestInfo], None] | None = None,
        on_retry: Callable[[RetryInfo], None] | None = None,
        on_success: Callable[[ResponseInfo], None] | None = None,
        on_failure: Callable[[FailureInfo], None] | None = None,
    ) -> None:
        """Initialize the resilient client."""
        ...
    
    def __enter__(self) -> Self:
        """Enter the context manager.
        
        If a client was provided, uses it directly.
        Otherwise, creates a new httpx.Client.
        """
        ...
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager.
        
        Only closes the client if it was auto-created.
        Wrapped clients are not closed (user manages lifecycle).
        """
        ...
    
    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Send an HTTP request with automatic retry logic."""
        ...
    
    def get(self, url: str, **kwargs) -> httpx.Response:
        """Send a GET request."""
        return self.request("GET", url, **kwargs)
    
    # Similar for post, put, delete, patch, head, options
    
    @property
    def cookies(self) -> httpx.Cookies:
        """Get the cookie jar from wrapped client."""
        return self._client.cookies
    
    @property
    def headers(self) -> httpx.Headers:
        """Get the default headers from wrapped client."""
        return self._client.headers
```

### 5.2 Modified AsyncResilientClient Interface

```python
class AsyncResilientClient:
    """Asynchronous context manager for resilient HTTP requests.
    
    Async version of ResilientClient with identical API but async methods.
    All parameters and features match the synchronous ResilientClient.
    
    Example (wrap existing async client):
        ```python
        import httpx
        from aresilient import AsyncResilientClient
        
        async with httpx.AsyncClient(auth=...) as http_client:
            async with AsyncResilientClient(client=http_client, max_retries=5) as resilient:
                response = await resilient.get('https://api.example.com/data')
        ```
    """
    
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,  # NEW: Optional async client to wrap
        # ... same parameters as ResilientClient
    ) -> None:
        """Initialize the async resilient client."""
        ...
    
    async def __aenter__(self) -> Self:
        """Enter the async context manager."""
        ...
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        ...
    
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Send an async HTTP request with retry."""
        ...
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Send an async GET request."""
        return await self.request("GET", url, **kwargs)
    
    # ... similar async methods for post, put, delete, patch, head, options
```

---

## 6. Implementation Strategy

### 6.1 Phase 1: Modify Existing Classes (Week 1-2)

**Deliverables:**
1. Update `src/aresilient/client.py` to accept optional `client` parameter
2. Update `src/aresilient/client_async.py` to accept optional `client` parameter
3. Handle lifecycle correctly (don't close wrapped clients)
4. Update unit tests for both modes (auto-create and wrap)
5. Documentation updates

**Implementation Steps:**

**Step 1: Modify `ResilientClient.__init__`**

```python
# src/aresilient/client.py

class ResilientClient:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,  # NEW: Optional client to wrap
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        # ... other resilience parameters
    ) -> None:
        # Validate resilience parameters
        validate_retry_params(...)
        
        # Store configuration
        self._max_retries = max_retries
        # ... store other resilience config
        
        # Create or store the client in constructor
        if client is None:
            # Auto-create client if not provided
            self._client = httpx.Client(timeout=self._timeout)
            self._owns_client = True
        else:
            # Use provided client
            self._client = client
            self._owns_client = False
        
        self._entered = False
```

**Step 2: Modify `__enter__` and `__exit__`**

```python
def __enter__(self) -> Self:
    """Enter context manager."""
    # Call __enter__ on the wrapped httpx.Client
    # This allows proper nesting of context managers
    self._client.__enter__()
    self._entered = True
    return self

def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    """Exit context manager."""
    if self._entered:
        # Call __exit__ on wrapped client (handles cleanup like connection pooling)
        self._client.__exit__(exc_type, exc_val, exc_tb)
        
        # Only close if we created the client
        if self._owns_client:
            self._client.close()
            self._client = None
        
        self._entered = False
```

**Step 3: Request method stays the same**

The `request()` method doesn't need changes - it already delegates to `self._client`.

**Step 4: Repeat for `AsyncResilientClient`**

Apply the same changes to `client_async.py` with async methods.

### 6.2 Phase 2: Testing (Week 3)

**Test Coverage:**

1. **Backward compatibility tests:**
   - Existing usage (auto-create) still works
   - All existing tests pass

2. **New wrapper tests:**
   - Wrap pre-configured httpx.Client
   - Verify auth, headers, cookies preserved
   - Verify resilience features work
   - Verify lifecycle (wrapped client not closed)

3. **Edge cases:**
   - Wrap client with context manager
   - Wrap client without context manager
   - Error handling

**Example Test:**

```python
def test_wrap_configured_client():
    """Test wrapping a pre-configured httpx client."""
    # Create configured httpx client
    http_client = httpx.Client(
        auth=httpx.BasicAuth('user', 'pass'),
        headers={'User-Agent': 'Test/1.0'},
    )
    
    # Wrap it
    with ResilientClient(client=http_client, max_retries=3) as resilient:
        # Make request
        response = resilient.get('https://httpbin.org/get')
        
        # Verify auth and headers were used
        assert response.request.headers['Authorization']
        assert response.request.headers['User-Agent'] == 'Test/1.0'
    
    # Verify wrapped client is NOT closed
    assert not http_client.is_closed
    
    # User closes it
    http_client.close()
```

### 6.3 Phase 3: Documentation (Week 4)

**Documentation Updates:**

1. Update `ResilientClient` docstring with both modes
2. Add examples in user guide
3. Add migration guide for wrapping existing clients
4. Update API reference

**Example Documentation:**

```markdown
## Using ResilientClient

### Mode 1: Auto-create Client (Current Behavior)

ResilientClient creates and manages its own httpx.Client:

```python
from aresilient import ResilientClient

with ResilientClient(timeout=30.0, max_retries=5) as client:
    response = client.get('https://api.example.com/data')
```

### Mode 2: Wrap Existing Client (New)

Wrap a pre-configured httpx.Client to add resilience:

```python
import httpx
from aresilient import ResilientClient

# Configure httpx client with auth, headers, etc.
http_client = httpx.Client(
    auth=httpx.BasicAuth('user', 'password'),
    headers={'User-Agent': 'MyApp/1.0'},
    proxy='http://proxy.example.com:8080',
)

# Wrap it to add resilience
with ResilientClient(client=http_client, max_retries=5) as resilient:
    response = resilient.get('https://api.example.com/data')

# Close the wrapped client when done
http_client.close()
```

### Benefits of Wrapping

- Preserve all httpx.Client configuration (auth, headers, cookies, proxy, etc.)
- Add resilience to existing clients without recreating them
- Use advanced httpx features (HTTP/2, custom transports, etc.) with resilience
```

---

## 7. Migration Path

### 7.1 For Users with Existing httpx Clients

**Minimal Migration (Wrap existing clients):**

```python
# Before: Using httpx.Client directly
import httpx

client = httpx.Client(
    auth=httpx.BasicAuth('user', 'pass'),
    headers={'User-Agent': 'MyApp/1.0'},
    proxy='http://proxy.example.com',
)

response = client.get('https://api.example.com/data')
client.close()

# After: Wrap with ResilientClient to add resilience
import httpx
from aresilient import ResilientClient

client = httpx.Client(
    auth=httpx.BasicAuth('user', 'pass'),
    headers={'User-Agent': 'MyApp/1.0'},
    proxy='http://proxy.example.com',
)

with ResilientClient(client=client, max_retries=5) as resilient:
    response = resilient.get('https://api.example.com/data')

client.close()
```

**With Context Manager:**

```python
# Before
import httpx

with httpx.Client(auth=..., headers=...) as client:
    response = client.get('https://api.example.com/data')

# After - wrap the configured client
import httpx
from aresilient import ResilientClient

http_client = httpx.Client(auth=..., headers=...)
with ResilientClient(client=http_client, max_retries=5) as resilient:
    response = resilient.get('https://api.example.com/data')
http_client.close()
```

### 7.2 For Current aresilient Users

**Current usage remains unchanged (backward compatible):**

```python
# This continues to work exactly as before
from aresilient import ResilientClient

with ResilientClient(max_retries=5, timeout=30) as client:
    response = client.get('https://api.example.com/data')
```

**New usage with wrapping:**

```python
# Now you can also wrap existing httpx clients
import httpx
from aresilient import ResilientClient

http_client = httpx.Client(auth=..., headers=..., proxy=...)
with ResilientClient(client=http_client, max_retries=5) as resilient:
    response = resilient.get('https://api.example.com/data')
http_client.close()
```

---

## 8. Examples

### 8.1 Basic Usage (Auto-create Client)

```python
# ResilientClient creates its own httpx.Client
from aresilient import ResilientClient

with ResilientClient(timeout=30.0, max_retries=5) as client:
    response = client.get('https://api.example.com/data')
    print(response.json())
```

### 8.2 Wrapping with Nested Context Managers (RECOMMENDED)

```python
# Nested context managers for cleanest lifecycle management
import httpx
from aresilient import ResilientClient

# httpx.Client managed by its own context manager
with httpx.Client(
    auth=httpx.BasicAuth('user', 'password'),
    headers={'User-Agent': 'MyApp/1.0'},
    cookies={'session': 'abc123'},
    proxy='http://proxy.example.com:8080',
    http2=True,
    verify='/path/to/cert.pem',
) as http_client:
    # Wrap with resilience - httpx.Client automatically closed on exit
    with ResilientClient(client=http_client, max_retries=5, backoff_factor=0.5) as resilient:
        response = resilient.get('https://api.example.com/data')
        print(response.status_code)
# http_client automatically closed here
```

### 8.3 Wrapping with Manual Lifecycle Management

```python
# User manages httpx.Client lifecycle manually
import httpx
from aresilient import ResilientClient

# Configure httpx client with all your settings
http_client = httpx.Client(
    auth=httpx.BasicAuth('user', 'password'),
    headers={'User-Agent': 'MyApp/1.0'},
    proxy='http://proxy.example.com:8080',
)

# Wrap it to add resilience
with ResilientClient(client=http_client, max_retries=5) as resilient:
    response = resilient.get('https://api.example.com/data')
    print(response.status_code)

# User responsible for closing
http_client.close()
```

### 8.4 With Custom Backoff Strategy

```python
import httpx
from aresilient import ResilientClient, LinearBackoff

# Nested context managers (recommended)
with httpx.Client(auth=..., headers=...) as http_client:
    with ResilientClient(
        client=http_client,
        max_retries=5,
        backoff_strategy=LinearBackoff(base_delay=1.0),
        jitter_factor=0.1,
    ) as resilient:
        response = resilient.post(
            'https://api.example.com/data',
            json={'key': 'value'},
        )
```

### 8.5 With Circuit Breaker

```python
import httpx
from aresilient import ResilientClient, CircuitBreaker

# Create circuit breaker
breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
)

# Nested context managers
with httpx.Client(headers={'API-Key': 'secret'}) as http_client:
    with ResilientClient(
        client=http_client,
        max_retries=3,
        circuit_breaker=breaker,
    ) as resilient:
        try:
            response = resilient.get('https://api.example.com/data')
        except Exception as e:
            print(f"Request failed: {e}")
```

### 8.6 With Custom Retry Logic

```python
import httpx
from aresilient import ResilientClient

def should_retry(response, exception):
    """Custom retry logic based on response content."""
    if response and response.status_code == 200:
        data = response.json()
        # Retry if API indicates rate limiting in response body
        if data.get('status') == 'rate_limited':
            return True
    return False

# Nested context managers
with httpx.Client() as http_client:
    with ResilientClient(
        client=http_client,
        max_retries=5,
        retry_if=should_retry,
    ) as resilient:
        response = resilient.get('https://api.example.com/data')
```

### 8.7 With Callbacks for Monitoring

```python
import httpx
import logging
from aresilient import ResilientClient

logger = logging.getLogger(__name__)

def on_request(info):
    logger.info(f"Request: {info.method} {info.url}")

def on_retry(info):
    logger.warning(f"Retry {info.attempt}/{info.max_retries}: {info.url}")

def on_failure(info):
    logger.error(f"Failed after {info.attempts} attempts: {info.url}")

# Nested context managers
with httpx.Client() as http_client:
    with ResilientClient(
        client=http_client,
        max_retries=3,
        on_request=on_request,
        on_retry=on_retry,
        on_failure=on_failure,
    ) as resilient:
        response = resilient.get('https://api.example.com/data')
```

### 8.8 Async Usage

```python
import asyncio
import httpx
from aresilient import AsyncResilientClient

async def fetch_data():
    # Nested async context managers
    async with httpx.AsyncClient(
        auth=httpx.BasicAuth('user', 'pass'),
        headers={'User-Agent': 'MyApp/1.0'},
    ) as http_client:
        async with AsyncResilientClient(client=http_client, max_retries=5) as resilient:
            response = await resilient.get('https://api.example.com/data')
            return response.json()

# Run async function
data = asyncio.run(fetch_data())
print(data)
```

### 8.9 Reusing Client Across Multiple Resilient Contexts

```python
import httpx
from aresilient import ResilientClient

# Create one httpx client with your configuration
http_client = httpx.Client(
    auth=httpx.BasicAuth('user', 'pass'),
    headers={'User-Agent': 'MyApp/1.0'},
)

# Use it with different resilience settings for different operations
# Critical API - more retries
with ResilientClient(client=http_client, max_retries=10) as resilient:
    critical_data = resilient.get('https://api.example.com/critical')

# Non-critical API - fewer retries
with ResilientClient(client=http_client, max_retries=2) as resilient:
    optional_data = resilient.get('https://api.example.com/optional')

# Close when completely done
http_client.close()
```

---

## 9. Backward Compatibility

### 9.1 Existing API Preservation

**All existing APIs remain unchanged:**

```python
# These continue to work exactly as before
from aresilient import (
    ResilientClient,                    # ✅ No change
    AsyncResilientClient,               # ✅ No change
    get_with_automatic_retry,           # ✅ No change
    post_with_automatic_retry,          # ✅ No change
    get_with_automatic_retry_async,     # ✅ No change
    request_with_automatic_retry,       # ✅ No change
    # ... all other existing exports
)
```

**No breaking changes:**
- All existing functions and classes remain
- All parameter names and signatures unchanged (except adding optional `client` parameter)
- All behaviors preserved
- Current usage (auto-create client) continues to work

### 9.2 New Optional Parameter

**The change is additive only:**

```python
# Old usage still works (backward compatible)
ResilientClient(max_retries=5, timeout=30)

# New usage available (wrap existing client)
ResilientClient(client=http_client, max_retries=5)
```

**Implementation ensures compatibility:**
- `client` parameter defaults to `None`
- When `None`, auto-creates httpx.Client (current behavior)
- When provided, wraps the given client (new behavior)

### 9.3 No Deprecation

**No deprecation of any existing features:**
- `ResilientClient` remains the primary class name
- No new classes introduced
- No APIs marked as deprecated
- Clean, minimal change

---

## 10. Trade-offs and Alternatives

### 10.1 Chosen Approach: Optional Client Wrapping

**Pros:**
- ✅ Minimal API change (single optional parameter)
- ✅ Full backward compatibility
- ✅ Preserves all httpx.Client configuration
- ✅ User controls client lifecycle
- ✅ Flexible - supports both auto-create and wrap modes
- ✅ No new classes to maintain

**Cons:**
- ⚠️ Slightly more complex lifecycle management (track if we own the client)
- ⚠️ User must remember to close wrapped clients themselves
- ⚠️ Documentation needed to explain both modes

**Verdict:** Best balance of flexibility and backward compatibility.

### 10.2 Alternative 1: Create New Client Classes

**Approach:**
Create new `Client` and `AsyncClient` classes that accept all httpx parameters.

**Pros:**
- ✅ Could match httpx API exactly
- ✅ Clear separation from existing ResilientClient

**Cons:**
- ❌ More code to maintain (duplicate functionality)
- ❌ Confusing to have multiple client classes
- ❌ Doesn't solve the core problem (still can't wrap existing clients)

**Verdict:** Rejected - doesn't solve the user's need to wrap existing httpx clients.

### 10.3 Alternative 2: Inherit from httpx.Client

**Approach:**
Make ResilientClient inherit from httpx.Client.

**Pros:**
- ✅ Automatic method inheritance
- ✅ Fewer lines of code

**Cons:**
- ❌ httpx.Client may not be designed for inheritance
- ❌ Harder to inject retry logic cleanly
- ❌ Risk of breaking with httpx updates
- ❌ Tight coupling to httpx internals

**Verdict:** Rejected - composition is safer and more maintainable.

### 10.4 Alternative 3: Decorator Pattern

**Approach:**
Provide a decorator to wrap httpx.Client instances.

```python
@add_resilience(max_retries=5)
class MyClient(httpx.Client):
    pass
```

**Pros:**
- ✅ Pythonic decorator pattern
- ✅ Clear separation

**Cons:**
- ❌ Less intuitive for users
- ❌ Harder to configure per-request
- ❌ Doesn't work well with existing client instances

**Verdict:** Rejected - less user-friendly than wrapper approach.

---

## 11. Success Metrics

### 11.1 Adoption Metrics

**Target Metrics (3 months post-release):**
- 📊 20%+ of users with existing httpx clients adopt wrapper pattern
- 📊 Positive feedback on ability to preserve httpx configuration
- 📊 Examples in documentation showing both modes
- 📊 Zero reported issues with wrapped client behavior

### 11.2 Code Quality Metrics

**Target:**
- ✅ 95%+ test coverage for both modes (auto-create and wrap)
- ✅ <1% performance overhead from wrapping layer
- ✅ Zero breaking changes to existing APIs
- ✅ All existing tests continue to pass

### 11.3 User Satisfaction Metrics

**Target:**
- ⭐ Positive community feedback on wrapper pattern
- ⭐ Low support burden (clear documentation for both modes)
- ⭐ Adoption by users with complex httpx configurations

---

## 12. Timeline and Phases

### 12.1 Development Timeline

**Total Duration:** 4 weeks

| Phase | Duration | Deliverables | Status |
|-------|----------|--------------|--------|
| Phase 1: Modify Classes | 1-2 weeks | Add `client` parameter, handle lifecycle | 📋 Planned |
| Phase 2: Testing | 1 week | Test both modes, edge cases | 📋 Planned |
| Phase 3: Documentation | 1 week | Update docs, add examples | 📋 Planned |

### 12.2 Phase Details

**Phase 1: Modify Existing Classes (Week 1-2)**
- [ ] Add optional `client` parameter to `ResilientClient.__init__`
- [ ] Add optional `client` parameter to `AsyncResilientClient.__init__`
- [ ] Update `__enter__` to handle both modes (auto-create vs wrap)
- [ ] Update `__exit__` to only close if we own the client
- [ ] Add `_owns_client` tracking
- [ ] Update docstrings
- [ ] Basic unit tests for both modes

**Phase 2: Testing (Week 3)**
- [ ] Comprehensive tests for auto-create mode (ensure backward compat)
- [ ] Comprehensive tests for wrap mode
- [ ] Test with various httpx configurations (auth, headers, proxy, etc.)
- [ ] Test lifecycle management (wrapped client not closed)
- [ ] Test async version
- [ ] Edge case testing
- [ ] Achieve 95%+ test coverage

**Phase 3: Documentation (Week 4)**
- [ ] Update `ResilientClient` docstring with both modes
- [ ] Add examples to user guide
- [ ] Create migration guide for wrapping existing clients
- [ ] Update API reference
- [ ] Add FAQ section for lifecycle management

### 12.3 Release Strategy

**Release (v0.x):**
- Add as new feature in next version
- Highlight in release notes
- Provide examples and documentation
- Gather feedback from early adopters

---

## 13. Conclusion

### 13.1 Summary

This design proposes modifying `ResilientClient` and `AsyncResilientClient` to accept optional `httpx.Client` and `httpx.AsyncClient` instances, enabling users to:

1. **Wrap Existing Clients** - Add resilience to pre-configured httpx clients
2. **Preserve Configuration** - Keep all httpx settings (auth, headers, cookies, proxy, etc.)
3. **Maintain Backward Compatibility** - Existing usage continues to work
4. **Control Lifecycle** - User manages wrapped client lifecycle
5. **Minimal API Change** - Single optional parameter addition

### 13.2 Key Benefits

**For Users with Existing httpx Clients:**
- ✅ Can now add resilience without losing httpx configuration
- ✅ No need to recreate clients or duplicate configuration
- ✅ Works with advanced httpx features (HTTP/2, custom transports, etc.)

**For Current aresilient Users:**
- ✅ No breaking changes
- ✅ Existing code continues to work
- ✅ New flexibility to wrap pre-configured clients

**For aresilient Library:**
- ✅ Addresses user pain point
- ✅ Minimal code changes required
- ✅ Clean, Pythonic API
- ✅ Easy to test and maintain

### 13.3 Recommendations

1. ⭐ **Implement wrapper pattern** - Add optional `client` parameter
2. ⭐ **Maintain backward compatibility** - Auto-create if not provided
3. ⭐ **Clear documentation** - Explain both modes with examples
4. ⭐ **Comprehensive testing** - Test both auto-create and wrap modes
5. ⭐ **User-friendly lifecycle** - User controls wrapped client closure

### 13.4 Next Steps

1. **Get Approval** on design approach
2. **Begin Implementation** - Modify ResilientClient and AsyncResilientClient
3. **Add Tests** - Comprehensive coverage for both modes
4. **Update Documentation** - Examples and guides
5. **Release** - Add as new feature in next version

---

## Appendix A: Related Design Documents

- [LIBRARY_STRUCTURE_PROPOSAL.md](LIBRARY_STRUCTURE_PROPOSAL.md) - Current structure and organization
- [SYNC_ASYNC_ARCHITECTURE_REVIEW.md](SYNC_ASYNC_ARCHITECTURE_REVIEW.md) - Sync/async code patterns
- [MISSING_FUNCTIONALITIES.md](MISSING_FUNCTIONALITIES.md) - Feature roadmap
- [README.md](README.md) - Design document index

---

## Appendix B: References

- **httpx Documentation:** https://www.python-httpx.org/
- **httpx API Reference:** https://www.python-httpx.org/api/
- **httpx Client:** https://www.python-httpx.org/advanced/#client-instances
- **aresilient Documentation:** https://durandtibo.github.io/aresilient/

---

## Appendix C: Comparison Table

| Feature | httpx.Client | aresilient.ResilientClient (Current) | aresilient.ResilientClient (Proposed) |
|---------|--------------|--------------------------------------|---------------------------------------|
| **Basic HTTP Methods** | ✅ | ✅ | ✅ |
| **Async Support** | ✅ (AsyncClient) | ✅ (AsyncResilientClient) | ✅ (AsyncResilientClient) |
| **Context Manager** | ✅ | ✅ | ✅ |
| **Automatic Retry** | ❌ | ✅ | ✅ |
| **Exponential Backoff** | ❌ | ✅ | ✅ |
| **Circuit Breaker** | ❌ | ✅ | ✅ |
| **Custom Retry Logic** | ❌ | ✅ | ✅ |
| **Callbacks** | Partial | ✅ | ✅ |
| **Wrap Existing Client** | N/A | ❌ | ✅ **NEW** |
| **Preserve httpx Config** | ✅ | ⚠️ (timeout only) | ✅ **IMPROVED** |
| **User Controls Lifecycle** | ✅ | ⚠️ (auto-managed) | ✅ **FLEXIBLE** |

---

**Last Updated:** February 2026  
**Next Review:** After implementation completion  
**Document Status:** 📋 Proposal (Updated) - Awaiting approval and implementation
