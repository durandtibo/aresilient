# httpx-Compatible Client API Design for aresilient

**Date:** February 2026  
**Status:** 📋 Proposal  
**Authors:** Design Team

---

## Executive Summary

This document proposes a design for extending the `aresilient` library to provide a fully `httpx`-compatible client API. The goal is to enable users to easily replace `httpx.Client` and `httpx.AsyncClient` with resilient versions that maintain the same API surface while adding automatic retry, backoff, circuit breaker, and other resilience features.

**Current State:**
- ✅ `ResilientClient` and `AsyncResilientClient` context managers exist
- ✅ Full HTTP method support (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- ✅ Comprehensive retry and resilience features
- ⚠️ API differs from `httpx` - requires different parameter names and usage patterns

**Proposed State:**
- ✅ Maintain existing `ResilientClient` and `AsyncResilientClient` (backward compatible)
- ✅ Add new `httpx`-compatible client classes for drop-in replacement
- ✅ Same API signature as `httpx.Client` and `httpx.AsyncClient`
- ✅ Enable plug-and-play migration from `httpx` to `aresilient`

**Key Design Decisions:**
1. **Recommended naming:** `Client` and `AsyncClient` (matches httpx exactly)
2. **Alternative naming options:** Ranked list provided for consideration
3. **API compatibility:** Full compatibility with `httpx` client API
4. **Backward compatibility:** Existing clients remain unchanged
5. **Implementation strategy:** Wrap `httpx` clients with resilience features

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Current Implementation Analysis](#2-current-implementation-analysis)
3. [Design Goals](#3-design-goals)
4. [Proposed Solution](#4-proposed-solution)
5. [Client Naming Options](#5-client-naming-options)
6. [API Design](#6-api-design)
7. [Implementation Strategy](#7-implementation-strategy)
8. [Migration Path](#8-migration-path)
9. [Examples](#9-examples)
10. [Backward Compatibility](#10-backward-compatibility)
11. [Trade-offs and Alternatives](#11-trade-offs-and-alternatives)
12. [Success Metrics](#12-success-metrics)
13. [Timeline and Phases](#13-timeline-and-phases)

---

## 1. Problem Statement

### 1.1 Current Situation

The `aresilient` library provides resilient HTTP request functionality with:
- Context manager clients: `ResilientClient` and `AsyncResilientClient`
- Standalone functions: `get_with_automatic_retry`, `post_with_automatic_retry`, etc.
- Comprehensive retry logic, backoff strategies, circuit breakers, and callbacks

However, the API differs from `httpx` in several ways:
- Different class names (`ResilientClient` vs `httpx.Client`)
- Different parameter names and patterns for resilience configuration
- Cannot be used as a drop-in replacement for `httpx.Client`

### 1.2 User Pain Points

**Migration Friction:**
```python
# Current httpx usage
import httpx

with httpx.Client() as client:
    response = client.get('https://api.example.com/data')
    
# To use aresilient, user must change both import and class name
from aresilient import ResilientClient

with ResilientClient() as client:
    response = client.get('https://api.example.com/data')
```

**Issues:**
1. Users must change import statements and class names throughout their codebase
2. Cannot easily A/B test resilient vs non-resilient clients
3. Migration requires code review and testing of all changed locations
4. Harder to adopt incrementally

### 1.3 Desired State

Enable seamless migration:
```python
# Before (httpx)
import httpx

with httpx.Client() as client:
    r = client.get('https://example.com')

# After (aresilient) - minimal change
import aresilient

with aresilient.Client() as client:
    r = client.get('https://example.com')
```

Or even better with aliasing:
```python
# Can switch between implementations with one line
# import httpx as http_client
import aresilient as http_client

with http_client.Client() as client:
    r = client.get('https://example.com')
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

**Limitations for httpx Compatibility:**
- ❌ Different class name (`ResilientClient` vs `Client`)
- ❌ Resilience parameters in `__init__` (not in httpx)
- ❌ Cannot accept all `httpx.Client` constructor parameters
- ❌ Missing some `httpx.Client` methods (build_request, send, stream, etc.)

### 2.2 httpx Client API Surface

**Key `httpx.Client` features:**
```python
class httpx.Client:
    def __init__(
        self,
        *,
        auth: Auth | None = None,
        params: QueryParams | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        verify: VerifyTypes = True,
        cert: CertTypes | None = None,
        http1: bool = True,
        http2: bool = False,
        proxy: ProxyTypes | None = None,
        proxies: ProxiesTypes | None = None,
        mounts: Mapping[str, BaseTransport] | None = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        follow_redirects: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: EventHooks | None = None,
        base_url: str = "",
        transport: BaseTransport | None = None,
        app: Callable | None = None,
        trust_env: bool = True,
        default_encoding: str | Callable = "utf-8",
    ) -> None:
        ...
    
    # Request methods
    def request(self, method: str, url: str, **kwargs) -> Response
    def get(self, url: str, **kwargs) -> Response
    def post(self, url: str, **kwargs) -> Response
    def put(self, url: str, **kwargs) -> Response
    def delete(self, url: str, **kwargs) -> Response
    def patch(self, url: str, **kwargs) -> Response
    def head(self, url: str, **kwargs) -> Response
    def options(self, url: str, **kwargs) -> Response
    
    # Advanced methods
    def build_request(self, method: str, url: str, **kwargs) -> Request
    def send(self, request: Request, **kwargs) -> Response
    def stream(self, method: str, url: str, **kwargs) -> ContextManager[Response]
    
    # Context manager
    def __enter__(self) -> Self
    def __exit__(self, ...) -> None
    
    # Properties
    @property
    def cookies(self) -> Cookies
    @property
    def headers(self) -> Headers
    @property
    def is_closed(self) -> bool
    
    # Lifecycle
    def close(self) -> None
```

**Same for `httpx.AsyncClient` with async methods.**

---

## 3. Design Goals

### 3.1 Primary Goals

1. **Drop-in Replacement:** Users should be able to replace `httpx.Client` with `aresilient.Client` with minimal code changes
2. **API Compatibility:** Match `httpx.Client` API signature and behavior exactly
3. **Resilience by Default:** Automatically add retry, backoff, and circuit breaker capabilities
4. **Backward Compatibility:** Existing `ResilientClient` users are not affected
5. **Configurability:** Allow users to configure resilience features while maintaining httpx compatibility

### 3.2 Secondary Goals

1. **Gradual Migration:** Support incremental adoption in existing codebases
2. **Clear Documentation:** Provide migration guides and examples
3. **Type Safety:** Maintain full type hints throughout
4. **Performance:** Minimal overhead compared to direct httpx usage
5. **Testing:** Comprehensive test coverage for compatibility

### 3.3 Non-Goals

1. **Perfect httpx Clone:** We don't need to replicate internal httpx implementation details
2. **All httpx Features Day 1:** Can implement advanced features (streaming, etc.) incrementally
3. **Deprecate Existing API:** Keep `ResilientClient` and existing functions for backward compatibility

---

## 4. Proposed Solution

### 4.1 Overview

Add new client classes that wrap `httpx.Client` and `httpx.AsyncClient` while maintaining full API compatibility:

```
aresilient/
├── client.py              # Existing ResilientClient (unchanged)
├── client_async.py        # Existing AsyncResilientClient (unchanged)
├── httpx_client.py        # New: httpx-compatible Client
└── httpx_client_async.py  # New: httpx-compatible AsyncClient
```

### 4.2 Architecture

**Layered Approach:**

```
┌─────────────────────────────────────────┐
│   aresilient.Client (new)               │
│   - httpx-compatible API                │
│   - Resilience configuration            │
└─────────────────────────────────────────┘
                 │
                 │ wraps
                 ▼
┌─────────────────────────────────────────┐
│   httpx.Client                          │
│   - HTTP transport layer                │
│   - Connection pooling                  │
└─────────────────────────────────────────┘
```

**Key Design Patterns:**

1. **Composition over Inheritance:** Wrap httpx.Client rather than inherit
2. **Configuration Extension:** Add resilience parameters to constructor
3. **Method Delegation:** Delegate to wrapped client after applying retry logic
4. **Transparent Pass-through:** Support all httpx parameters unchanged

### 4.3 Configuration Strategy

**Two configuration levels:**

1. **httpx Configuration:** Pass through to underlying `httpx.Client`
   - `auth`, `headers`, `cookies`, `timeout`, `proxy`, etc.
   - All standard httpx parameters supported

2. **Resilience Configuration:** New parameters for retry/backoff/circuit breaker
   - `max_retries`, `backoff_factor`, `jitter_factor`
   - `status_forcelist`, `retry_if`
   - `backoff_strategy`, `circuit_breaker`
   - `on_request`, `on_retry`, `on_success`, `on_failure`

**Parameter Separation:**
```python
aresilient.Client(
    # httpx parameters (passed through)
    timeout=30.0,
    headers={'User-Agent': 'MyApp/1.0'},
    follow_redirects=True,
    
    # Resilience parameters (new)
    max_retries=5,
    backoff_factor=0.5,
    circuit_breaker=my_breaker,
)
```

---

## 5. Client Naming Options

### 5.1 Recommended Option (Highest Priority)

**Option 1: `Client` and `AsyncClient`**

```python
from aresilient import Client, AsyncClient

# Sync
with Client() as client:
    response = client.get('https://example.com')

# Async
async with AsyncClient() as client:
    response = await client.get('https://example.com')
```

**Pros:**
- ✅ Exact match with httpx naming
- ✅ Minimal migration effort (change import only)
- ✅ Clear and simple
- ✅ Industry standard naming pattern
- ✅ Enables alias-based switching: `import aresilient as httpx`

**Cons:**
- ⚠️ Less descriptive - doesn't indicate resilience features
- ⚠️ May confuse users about which client they're using
- ⚠️ Namespace collision if importing both httpx and aresilient

**Mitigation:**
- Use clear documentation and examples
- Provide type hints: `aresilient.Client` vs `httpx.Client`
- Most users won't import both simultaneously

**Verdict:** ⭐⭐⭐⭐⭐ **RECOMMENDED** - Best for drop-in replacement

---

### 5.2 Alternative Options (Ranked)

**Option 2: `ResilientClient` and `AsyncResilientClient` (Current)**

*Status:* Already implemented, keep for backward compatibility

```python
from aresilient import ResilientClient, AsyncResilientClient
```

**Pros:**
- ✅ Already exists
- ✅ Descriptive name
- ✅ No confusion with httpx

**Cons:**
- ❌ Not drop-in compatible with httpx
- ❌ Requires code changes throughout codebase

**Verdict:** ⭐⭐⭐⭐ - Keep as alias to `Client` for backward compatibility

---

**Option 3: `HttpxClient` and `AsyncHttpxClient`**

```python
from aresilient import HttpxClient, AsyncHttpxClient
```

**Pros:**
- ✅ Indicates httpx compatibility
- ✅ Clear and descriptive
- ✅ No namespace collision

**Cons:**
- ❌ Redundant "Httpx" prefix
- ❌ Still requires code changes
- ❌ Longer than necessary

**Verdict:** ⭐⭐⭐ - Acceptable but not ideal

---

**Option 4: `RetryClient` and `AsyncRetryClient`**

```python
from aresilient import RetryClient, AsyncRetryClient
```

**Pros:**
- ✅ Describes primary feature (retry)
- ✅ Clear purpose
- ✅ No namespace collision

**Cons:**
- ❌ Only mentions retry, not other features (circuit breaker, backoff)
- ❌ Still requires code changes
- ❌ Less aligned with httpx naming

**Verdict:** ⭐⭐⭐ - Acceptable but incomplete

---

**Option 5: `SafeClient` and `AsyncSafeClient`**

```python
from aresilient import SafeClient, AsyncSafeClient
```

**Pros:**
- ✅ Short and memorable
- ✅ Indicates safety/resilience

**Cons:**
- ❌ "Safe" is vague - safe from what?
- ❌ Doesn't clearly indicate retry/resilience
- ❌ May be confused with security features

**Verdict:** ⭐⭐ - Too vague

---

### 5.3 Naming Recommendation Summary

**Ordered list of recommended names (from best to acceptable):**

1. ⭐⭐⭐⭐⭐ **`Client` and `AsyncClient`** - Exact httpx compatibility (RECOMMENDED)
2. ⭐⭐⭐⭐ **`ResilientClient` and `AsyncResilientClient`** - Current names (keep for backward compatibility)
3. ⭐⭐⭐ **`HttpxClient` and `AsyncHttpxClient`** - Explicit httpx compatibility
4. ⭐⭐⭐ **`RetryClient` and `AsyncRetryClient`** - Describes primary feature
5. ⭐⭐ **`SafeClient` and `AsyncSafeClient`** - Too vague

**Implementation Strategy:**
- Add `Client` and `AsyncClient` as new primary classes
- Keep `ResilientClient` and `AsyncResilientClient` as aliases for backward compatibility
- Update documentation to recommend `Client` for new code

---

## 6. API Design

### 6.1 Client Class Interface

```python
class Client:
    """httpx-compatible synchronous client with automatic retry and resilience.
    
    This class provides a drop-in replacement for httpx.Client with added
    resilience features including automatic retry, exponential backoff,
    circuit breaker, and custom retry predicates.
    
    All httpx.Client parameters are supported and passed through to the
    underlying client. Additional resilience parameters control retry behavior.
    
    Args:
        # Standard httpx.Client parameters (passed through)
        auth: Authentication instance.
        params: Query parameters to include in all requests.
        headers: Headers to include in all requests.
        cookies: Cookies to include in all requests.
        verify: SSL certificate verification.
        cert: SSL client certificate.
        http1: Enable HTTP/1.1.
        http2: Enable HTTP/2.
        proxy: Proxy URL for all requests.
        timeout: Request timeout configuration.
        follow_redirects: Whether to follow redirects.
        limits: Connection pool limits.
        base_url: Base URL for all requests.
        transport: Custom transport instance.
        trust_env: Whether to trust environment variables.
        
        # Resilience parameters (aresilient-specific)
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
    
    Example:
        ```python
        import aresilient
        
        # Drop-in replacement for httpx.Client
        with aresilient.Client(timeout=30.0, max_retries=5) as client:
            response = client.get('https://api.example.com/data')
            print(response.json())
        ```
    
    Note:
        This class wraps httpx.Client and maintains full API compatibility.
        All httpx features are supported including streaming, cookies, headers, etc.
    """
    
    def __init__(
        self,
        *,
        # httpx.Client parameters
        auth: httpx.Auth | None = None,
        params: httpx.QueryParams | None = None,
        headers: httpx.HeaderTypes | None = None,
        cookies: httpx.CookieTypes | None = None,
        verify: httpx.VerifyTypes = True,
        cert: httpx.CertTypes | None = None,
        http1: bool = True,
        http2: bool = False,
        proxy: httpx.ProxyTypes | None = None,
        timeout: httpx.TimeoutTypes = DEFAULT_TIMEOUT,
        follow_redirects: bool = False,
        limits: httpx.Limits | None = None,
        base_url: str = "",
        transport: httpx.BaseTransport | None = None,
        trust_env: bool = True,
        
        # aresilient resilience parameters
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
        """Initialize the resilient httpx-compatible client."""
        ...
    
    # Context manager protocol
    def __enter__(self) -> Self:
        """Enter the context manager."""
        ...
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager and close the client."""
        ...
    
    # HTTP methods (httpx-compatible signatures)
    def request(
        self,
        method: str,
        url: httpx.URL | str,
        *,
        content: httpx.RequestContent | None = None,
        data: httpx.RequestData | None = None,
        files: httpx.RequestFiles | None = None,
        json: Any | None = None,
        params: httpx.QueryParamTypes | None = None,
        headers: httpx.HeaderTypes | None = None,
        cookies: httpx.CookieTypes | None = None,
        auth: httpx.AuthTypes | None = None,
        follow_redirects: bool | None = None,
        timeout: httpx.TimeoutTypes | None = None,
        extensions: dict[str, Any] | None = None,
        
        # Optional resilience overrides
        max_retries: int | None = None,
        backoff_factor: float | None = None,
        status_forcelist: tuple[int, ...] | None = None,
        jitter_factor: float | None = None,
        retry_if: Callable | None = None,
        backoff_strategy: BackoffStrategy | None = None,
        max_total_time: float | None = None,
        max_wait_time: float | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        on_request: Callable | None = None,
        on_retry: Callable | None = None,
        on_success: Callable | None = None,
        on_failure: Callable | None = None,
    ) -> httpx.Response:
        """Send an HTTP request with automatic retry.
        
        This method matches httpx.Client.request() signature exactly,
        with optional resilience parameter overrides.
        """
        ...
    
    def get(self, url: httpx.URL | str, **kwargs: Any) -> httpx.Response:
        """Send a GET request."""
        return self.request("GET", url, **kwargs)
    
    def post(self, url: httpx.URL | str, **kwargs: Any) -> httpx.Response:
        """Send a POST request."""
        return self.request("POST", url, **kwargs)
    
    def put(self, url: httpx.URL | str, **kwargs: Any) -> httpx.Response:
        """Send a PUT request."""
        return self.request("PUT", url, **kwargs)
    
    def delete(self, url: httpx.URL | str, **kwargs: Any) -> httpx.Response:
        """Send a DELETE request."""
        return self.request("DELETE", url, **kwargs)
    
    def patch(self, url: httpx.URL | str, **kwargs: Any) -> httpx.Response:
        """Send a PATCH request."""
        return self.request("PATCH", url, **kwargs)
    
    def head(self, url: httpx.URL | str, **kwargs: Any) -> httpx.Response:
        """Send a HEAD request."""
        return self.request("HEAD", url, **kwargs)
    
    def options(self, url: httpx.URL | str, **kwargs: Any) -> httpx.Response:
        """Send an OPTIONS request."""
        return self.request("OPTIONS", url, **kwargs)
    
    # Advanced httpx methods (Phase 2 implementation)
    def build_request(
        self,
        method: str,
        url: httpx.URL | str,
        **kwargs: Any,
    ) -> httpx.Request:
        """Build an HTTP request without sending it.
        
        Delegates to underlying httpx.Client.
        """
        ...
    
    def send(
        self,
        request: httpx.Request,
        *,
        stream: bool = False,
        auth: httpx.AuthTypes | None = None,
        follow_redirects: bool | None = None,
        
        # Resilience overrides
        max_retries: int | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send a pre-built request with retry logic."""
        ...
    
    def stream(
        self,
        method: str,
        url: httpx.URL | str,
        **kwargs: Any,
    ) -> ContextManager[httpx.Response]:
        """Send a streaming request.
        
        Note: Streaming responses disable automatic retry by default
        (can't replay streamed content).
        """
        ...
    
    # Properties (delegate to underlying client)
    @property
    def cookies(self) -> httpx.Cookies:
        """Get the cookie jar."""
        return self._client.cookies
    
    @property
    def headers(self) -> httpx.Headers:
        """Get the default headers."""
        return self._client.headers
    
    @property
    def is_closed(self) -> bool:
        """Check if the client is closed."""
        return self._client.is_closed if self._client else True
    
    # Lifecycle
    def close(self) -> None:
        """Close the client and release resources."""
        if self._client is not None:
            self._client.close()
```

### 6.2 AsyncClient Class Interface

```python
class AsyncClient:
    """httpx-compatible asynchronous client with automatic retry and resilience.
    
    Async version of Client with identical API but async methods.
    All parameters and features match the synchronous Client.
    
    Example:
        ```python
        import asyncio
        import aresilient
        
        async def main():
            async with aresilient.AsyncClient(max_retries=5) as client:
                response = await client.get('https://api.example.com/data')
                print(response.json())
        
        asyncio.run(main())
        ```
    """
    
    def __init__(self, **kwargs) -> None:
        """Initialize async client (same parameters as Client)."""
        ...
    
    # Async context manager
    async def __aenter__(self) -> Self:
        """Enter the async context manager."""
        ...
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        ...
    
    # Async HTTP methods
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Send an async HTTP request with retry."""
        ...
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Send an async GET request."""
        return await self.request("GET", url, **kwargs)
    
    # ... similar async methods for post, put, delete, patch, head, options
    
    # Async lifecycle
    async def aclose(self) -> None:
        """Close the async client."""
        if self._client is not None:
            await self._client.aclose()
```

---

## 7. Implementation Strategy

### 7.1 Phase 1: Core Implementation (Week 1-2)

**Deliverables:**
1. New `httpx_client.py` with `Client` class
2. New `httpx_client_async.py` with `AsyncClient` class
3. Basic HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
4. Full httpx parameter pass-through
5. Resilience parameter support
6. Unit tests for core functionality

**Implementation Steps:**

```python
# src/aresilient/httpx_client.py

class Client:
    def __init__(self, *, 
                 # httpx params
                 auth=None, params=None, headers=None, cookies=None,
                 verify=True, cert=None, http1=True, http2=False,
                 proxy=None, timeout=DEFAULT_TIMEOUT, follow_redirects=False,
                 limits=None, base_url="", transport=None, trust_env=True,
                 # resilience params
                 max_retries=DEFAULT_MAX_RETRIES,
                 backoff_factor=DEFAULT_BACKOFF_FACTOR,
                 status_forcelist=RETRY_STATUS_CODES,
                 jitter_factor=0.0,
                 retry_if=None,
                 backoff_strategy=None,
                 max_total_time=None,
                 max_wait_time=None,
                 circuit_breaker=None,
                 on_request=None,
                 on_retry=None,
                 on_success=None,
                 on_failure=None):
        
        # Validate resilience parameters
        validate_retry_params(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            jitter_factor=jitter_factor,
            timeout=timeout,
            max_total_time=max_total_time,
            max_wait_time=max_wait_time,
        )
        
        # Store resilience config
        self._resilience_config = {
            'max_retries': max_retries,
            'backoff_factor': backoff_factor,
            'status_forcelist': status_forcelist,
            'jitter_factor': jitter_factor,
            'retry_if': retry_if,
            'backoff_strategy': backoff_strategy,
            'max_total_time': max_total_time,
            'max_wait_time': max_wait_time,
            'circuit_breaker': circuit_breaker,
            'on_request': on_request,
            'on_retry': on_retry,
            'on_success': on_success,
            'on_failure': on_failure,
        }
        
        # Create underlying httpx.Client with httpx params only
        self._client = httpx.Client(
            auth=auth,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=verify,
            cert=cert,
            http1=http1,
            http2=http2,
            proxy=proxy,
            timeout=timeout,
            follow_redirects=follow_redirects,
            limits=limits,
            base_url=base_url,
            transport=transport,
            trust_env=trust_env,
        )
        
        self._closed = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def request(self, method, url, **kwargs):
        """Execute request with retry logic."""
        # Separate httpx params from resilience params
        httpx_params = {}
        resilience_overrides = {}
        
        for key, value in kwargs.items():
            if key in RESILIENCE_PARAM_NAMES:
                resilience_overrides[key] = value
            else:
                httpx_params[key] = value
        
        # Merge client config with per-request overrides
        retry_config = {**self._resilience_config, **resilience_overrides}
        
        # Use existing request_with_automatic_retry logic
        return request_with_automatic_retry(
            url=url,
            method=method,
            request_func=self._client.request,
            **retry_config,
            **httpx_params,
        )
    
    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)
    
    # ... similar for other methods
    
    @property
    def cookies(self):
        return self._client.cookies
    
    @property
    def headers(self):
        return self._client.headers
    
    @property
    def is_closed(self):
        return self._closed
    
    def close(self):
        if not self._closed:
            self._client.close()
            self._closed = True
```

### 7.2 Phase 2: Advanced Features (Week 3-4)

**Deliverables:**
1. `build_request()` method support
2. `send()` method with retry logic
3. `stream()` method (with streaming considerations)
4. Complete property delegation
5. Integration tests with real httpx usage patterns

**Streaming Considerations:**

Streaming responses present a challenge for retry:
- Can't replay streamed content that's already consumed
- Need to disable automatic retry by default for streaming
- Or buffer content (memory intensive)
- Or allow retry only before stream consumption begins

**Proposed Solution:**
```python
def stream(self, method, url, **kwargs):
    """Stream response (retry disabled by default).
    
    Streaming responses cannot be automatically retried after
    the stream has been consumed. Set max_retries=0 by default
    unless user explicitly overrides.
    """
    if 'max_retries' not in kwargs:
        kwargs['max_retries'] = 0
    
    # Delegate to underlying client's stream method
    return self._client.stream(method, url, **kwargs)
```

### 7.3 Phase 3: Documentation & Migration Guides (Week 5)

**Deliverables:**
1. API documentation for Client and AsyncClient
2. Migration guide from httpx to aresilient
3. Migration guide from ResilientClient to Client
4. Example code snippets
5. Comparison table: httpx vs aresilient
6. Blog post or tutorial

**Documentation Structure:**
```markdown
# Migration Guide: httpx to aresilient

## Why Migrate?

Add automatic retry, exponential backoff, circuit breaker, and other
resilience features to your httpx code with minimal changes.

## Quick Start

### Before (httpx)
```python
import httpx

with httpx.Client() as client:
    response = client.get('https://api.example.com/data')
```

### After (aresilient)
```python
import aresilient

with aresilient.Client() as client:
    response = client.get('https://api.example.com/data')
```

That's it! You now have automatic retry on failures.

## Configuration

Configure resilience features through constructor:
```python
import aresilient

with aresilient.Client(
    # httpx parameters (unchanged)
    timeout=30.0,
    headers={'User-Agent': 'MyApp/1.0'},
    
    # Resilience features (new)
    max_retries=5,
    backoff_factor=0.5,
    circuit_breaker=my_breaker,
) as client:
    response = client.get('https://api.example.com/data')
```

## Compatibility

✅ All httpx.Client parameters supported
✅ All HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
✅ Context manager protocol
✅ Cookies, headers, authentication
✅ Timeouts and redirects
✅ HTTP/2 support
⚠️ Streaming (limited retry support - see Streaming Guide)

## Advanced Usage

...
```

### 7.4 Phase 4: Testing & Validation (Week 6)

**Testing Strategy:**

1. **Unit Tests:**
   - All constructor parameters work correctly
   - HTTP methods delegate properly
   - Resilience features activate correctly
   - Context manager lifecycle

2. **Integration Tests:**
   - Real httpx compatibility
   - Retry logic with mock server
   - Circuit breaker integration
   - Callback execution

3. **Compatibility Tests:**
   - Test against httpx test suite (if possible)
   - Verify parameter pass-through
   - Edge cases and error handling

4. **Performance Tests:**
   - Overhead comparison: aresilient.Client vs httpx.Client
   - Memory usage
   - Connection pool behavior

---

## 8. Migration Path

### 8.1 For httpx Users

**Minimal Migration (Just add retry):**

```python
# Before
import httpx
with httpx.Client() as client:
    response = client.get('https://api.example.com/data')

# After - change import only
import aresilient
with aresilient.Client() as client:
    response = client.get('https://api.example.com/data')
```

**With Configuration:**

```python
import aresilient

with aresilient.Client(
    timeout=30.0,              # httpx parameter
    follow_redirects=True,     # httpx parameter
    max_retries=5,             # resilience parameter
    backoff_factor=0.5,        # resilience parameter
) as client:
    response = client.get('https://api.example.com/data')
```

**Gradual Rollout:**

```python
import os
import httpx
import aresilient

# Use environment variable to switch clients
USE_RESILIENT = os.getenv('USE_RESILIENT_CLIENT', 'false').lower() == 'true'
ClientClass = aresilient.Client if USE_RESILIENT else httpx.Client

with ClientClass(timeout=30.0) as client:
    response = client.get('https://api.example.com/data')
```

### 8.2 For Existing aresilient Users

**Current Code (ResilientClient):**

```python
from aresilient import ResilientClient

with ResilientClient(max_retries=5, timeout=30) as client:
    response = client.get('https://api.example.com/data')
```

**Option 1: Keep Using ResilientClient (no change needed)**

```python
from aresilient import ResilientClient

with ResilientClient(max_retries=5, timeout=30) as client:
    response = client.get('https://api.example.com/data')
```

**Option 2: Migrate to Client (recommended for new code)**

```python
from aresilient import Client

with Client(max_retries=5, timeout=30) as client:
    response = client.get('https://api.example.com/data')
```

**Backward Compatibility:**
- `ResilientClient` and `AsyncResilientClient` remain fully supported
- Can alias `Client = ResilientClient` internally for compatibility
- No breaking changes

---

## 9. Examples

### 9.1 Drop-in Replacement

```python
# Replace httpx with aresilient in existing code
import aresilient

# Works exactly like httpx.Client
with aresilient.Client() as client:
    response = client.get('https://api.example.com/users')
    users = response.json()
    
    for user in users:
        detail = client.get(f'https://api.example.com/users/{user["id"]}')
        print(detail.json())
```

### 9.2 With Resilience Configuration

```python
import aresilient
from aresilient import LinearBackoff

with aresilient.Client(
    # httpx parameters
    timeout=30.0,
    headers={'User-Agent': 'MyApp/1.0'},
    follow_redirects=True,
    
    # Resilience parameters
    max_retries=5,
    backoff_strategy=LinearBackoff(base_delay=1.0),
    jitter_factor=0.1,
    status_forcelist=(429, 500, 502, 503, 504),
) as client:
    response = client.post(
        'https://api.example.com/data',
        json={'key': 'value'},
    )
    print(response.status_code)
```

### 9.3 With Circuit Breaker

```python
import aresilient
from aresilient import CircuitBreaker

# Create circuit breaker
breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
    expected_exception=aresilient.HttpRequestError,
)

with aresilient.Client(
    max_retries=3,
    circuit_breaker=breaker,
) as client:
    try:
        response = client.get('https://api.example.com/data')
    except aresilient.HttpRequestError as e:
        print(f"Request failed: {e}")
```

### 9.4 With Custom Retry Logic

```python
import aresilient

def should_retry(response, exception):
    """Custom retry logic based on response content."""
    if response and response.status_code == 200:
        data = response.json()
        # Retry if API indicates rate limiting in response body
        if data.get('status') == 'rate_limited':
            return True
    return False

with aresilient.Client(
    max_retries=5,
    retry_if=should_retry,
) as client:
    response = client.get('https://api.example.com/data')
```

### 9.5 With Callbacks for Monitoring

```python
import aresilient
import logging

logger = logging.getLogger(__name__)

def on_request(info):
    logger.info(f"Request: {info.method} {info.url}")

def on_retry(info):
    logger.warning(f"Retry {info.attempt}/{info.max_retries}: {info.url}")

def on_failure(info):
    logger.error(f"Failed after {info.attempts} attempts: {info.url}")

with aresilient.Client(
    max_retries=3,
    on_request=on_request,
    on_retry=on_retry,
    on_failure=on_failure,
) as client:
    response = client.get('https://api.example.com/data')
```

### 9.6 Async Usage

```python
import asyncio
import aresilient

async def fetch_data():
    async with aresilient.AsyncClient(max_retries=5) as client:
        response = await client.get('https://api.example.com/data')
        return response.json()

# Run async function
data = asyncio.run(fetch_data())
print(data)
```

### 9.7 Mixed httpx Parameters

```python
import aresilient
import httpx

# All httpx features work: auth, cookies, custom transport, etc.
auth = httpx.BasicAuth('username', 'password')

with aresilient.Client(
    auth=auth,
    cookies={'session': 'abc123'},
    verify=True,
    http2=True,
    max_retries=5,
) as client:
    response = client.get('https://api.example.com/protected')
```

---

## 10. Backward Compatibility

### 10.1 Existing API Preservation

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
- All parameter names and signatures unchanged
- All behaviors preserved
- Comprehensive re-exports maintained

### 10.2 Aliasing Strategy

**Option A: Keep ResilientClient as separate class**
```python
# Both exist independently
Client              # New httpx-compatible client
ResilientClient     # Existing client (unchanged)
```

**Option B: Alias ResilientClient to Client**
```python
# Single implementation, multiple names
Client = _HttpxCompatibleClient
ResilientClient = Client  # Alias for backward compatibility
```

**Recommendation:** Option A initially, then potentially merge in future version once Client is proven stable.

### 10.3 Deprecation Strategy (Future)

**No immediate deprecation**, but potential future path:

1. **v0.x (Current):** Add `Client` and `AsyncClient` as new recommended API
2. **v1.0:** Mark `ResilientClient` as "legacy but supported"
3. **v2.0 (far future):** Potentially deprecate `ResilientClient` if `Client` is universally adopted
4. **v3.0 (far future):** Potentially remove `ResilientClient` after long deprecation period

**Note:** Deprecation timeline is tentative and would require community feedback.

---

## 11. Trade-offs and Alternatives

### 11.1 Design Trade-offs

**Chosen Approach: Composition (Wrap httpx.Client)**

**Pros:**
- ✅ Full control over retry logic injection
- ✅ Can support all httpx parameters
- ✅ Easy to maintain and test
- ✅ Clear separation of concerns
- ✅ No need to inherit httpx internals

**Cons:**
- ⚠️ Need to manually delegate all httpx methods
- ⚠️ May lag behind httpx API changes
- ⚠️ Additional layer of abstraction (minimal overhead)

**Alternative: Inheritance (Inherit from httpx.Client)**

**Pros:**
- ✅ Automatic method inheritance
- ✅ Fewer lines of code
- ✅ Automatic API compatibility

**Cons:**
- ❌ httpx.Client may not be designed for inheritance
- ❌ Harder to inject retry logic cleanly
- ❌ Risk of breaking with httpx updates
- ❌ Tight coupling to httpx internals

**Verdict:** Composition is safer and more maintainable.

### 11.2 Parameter Design Trade-offs

**Chosen Approach: Mixed Parameters**

Constructor accepts both httpx and resilience parameters:
```python
Client(
    timeout=30,         # httpx
    max_retries=5,      # resilience
    headers={...},      # httpx
    backoff_factor=0.5  # resilience
)
```

**Alternative 1: Separate Config Objects**
```python
Client(
    httpx_config=HttpxConfig(timeout=30, headers={...}),
    resilience_config=ResilienceConfig(max_retries=5, backoff_factor=0.5)
)
```

**Alternative 2: Subclass httpx.Client**
```python
class Client(httpx.Client):
    def __init__(self, *, max_retries=3, **httpx_kwargs):
        super().__init__(**httpx_kwargs)
        self.max_retries = max_retries
```

**Verdict:** Mixed parameters provide best user experience with minimal migration effort.

### 11.3 Naming Trade-offs

See [Section 5: Client Naming Options](#5-client-naming-options) for detailed analysis.

**Chosen:** `Client` and `AsyncClient` (exact httpx match)

---

## 12. Success Metrics

### 12.1 Adoption Metrics

**Target Metrics (6 months post-release):**
- 📊 30%+ of new aresilient code uses `Client` instead of `ResilientClient`
- 📊 50%+ of documentation examples showcase `Client`
- 📊 10+ migration case studies or blog posts from users
- 📊 Zero reported incompatibility issues with httpx API

### 12.2 Code Quality Metrics

**Target:**
- ✅ 95%+ test coverage for Client and AsyncClient
- ✅ 100% of httpx.Client constructor parameters supported
- ✅ <5% performance overhead compared to direct httpx usage
- ✅ Zero breaking changes to existing APIs

### 12.3 User Satisfaction Metrics

**Target:**
- ⭐ Positive community feedback on API design
- ⭐ Low support burden (few questions about usage)
- ⭐ GitHub stars increase by 20%+
- ⭐ PyPI downloads increase by 50%+

---

## 13. Timeline and Phases

### 13.1 Development Timeline

**Total Duration:** 6 weeks (with buffer for testing and docs)

| Phase | Duration | Deliverables | Status |
|-------|----------|--------------|--------|
| Phase 1: Core Implementation | 2 weeks | Client, AsyncClient classes, basic methods | 📋 Planned |
| Phase 2: Advanced Features | 2 weeks | build_request, send, stream methods | 📋 Planned |
| Phase 3: Documentation | 1 week | Docs, migration guides, examples | 📋 Planned |
| Phase 4: Testing & Validation | 1 week | Comprehensive tests, compatibility checks | 📋 Planned |

### 13.2 Phase Details

**Phase 1: Core Implementation (Week 1-2)**
- [ ] Create `httpx_client.py` with `Client` class
- [ ] Create `httpx_client_async.py` with `AsyncClient` class
- [ ] Implement constructor with all httpx + resilience parameters
- [ ] Implement context manager protocol (`__enter__`, `__exit__`, etc.)
- [ ] Implement `request()` method with retry logic
- [ ] Implement HTTP method shortcuts (get, post, put, delete, patch, head, options)
- [ ] Add parameter validation
- [ ] Add basic unit tests (50%+ coverage)

**Phase 2: Advanced Features (Week 3-4)**
- [ ] Implement `build_request()` method
- [ ] Implement `send()` method with retry
- [ ] Implement `stream()` method (with streaming considerations)
- [ ] Implement property delegation (cookies, headers, is_closed)
- [ ] Implement `close()` and lifecycle methods
- [ ] Add integration tests with real httpx usage patterns
- [ ] Increase test coverage to 90%+

**Phase 3: Documentation (Week 5)**
- [ ] Write API documentation for Client and AsyncClient
- [ ] Create migration guide: httpx → aresilient.Client
- [ ] Create migration guide: ResilientClient → Client
- [ ] Write example code snippets (10+ examples)
- [ ] Create comparison table: httpx vs aresilient
- [ ] Update main README with Client examples
- [ ] Write blog post or tutorial

**Phase 4: Testing & Validation (Week 6)**
- [ ] Comprehensive unit tests (95%+ coverage)
- [ ] Integration tests with mock servers
- [ ] Compatibility tests against httpx patterns
- [ ] Performance benchmarks
- [ ] Code review and refinement
- [ ] Beta release for community feedback
- [ ] Address feedback and finalize

### 13.3 Release Strategy

**Beta Release (v0.x-beta):**
- Release Client and AsyncClient as beta feature
- Gather community feedback
- Fix bugs and refine API
- Update based on real-world usage

**Stable Release (v0.x):**
- Mark Client and AsyncClient as stable
- Full documentation and examples
- Promote as recommended API for new code
- Maintain ResilientClient for backward compatibility

**Future (v1.0+):**
- Consider marking ResilientClient as "legacy but supported"
- Potentially add Client as primary API in main exports

---

## 14. Open Questions

### 14.1 For Discussion

1. **Naming:** Should we use `Client`/`AsyncClient` or a more descriptive name?
   - **Recommendation:** Use `Client`/`AsyncClient` for httpx compatibility
   - **Alternative:** Keep as `ResilientClient` and add import aliases

2. **Streaming Support:** How should we handle streaming with retry?
   - **Recommendation:** Disable retry by default for streaming, document clearly
   - **Alternative:** Buffer content for retry (memory intensive)

3. **Deprecation Timeline:** When (if ever) should we deprecate `ResilientClient`?
   - **Recommendation:** Never deprecate, just recommend `Client` for new code
   - **Alternative:** Deprecate in v2.0 after multiple years

4. **Parameter Conflicts:** What if httpx adds parameters that conflict with resilience params?
   - **Recommendation:** Prefix resilience params (e.g., `resilient_max_retries`)
   - **Current:** Use current unprefixed names, monitor httpx changes

### 14.2 Future Enhancements

- **Connection Pooling:** Custom connection pool with per-endpoint retry config
- **Request Middleware:** Hook system for request/response transformation
- **Metrics Integration:** Built-in Prometheus/StatsD metrics
- **Distributed Tracing:** OpenTelemetry integration
- **Load Balancing:** Client-side load balancing across multiple endpoints
- **Caching:** Response caching with configurable strategies

---

## 15. Conclusion

### 15.1 Summary

This design proposes adding httpx-compatible client classes (`Client` and `AsyncClient`) to aresilient, enabling users to:

1. **Drop-in Replace** httpx.Client with aresilient.Client
2. **Maintain Full Compatibility** with httpx API
3. **Gain Resilience Features** automatically (retry, backoff, circuit breaker)
4. **Migrate Incrementally** from httpx or existing aresilient code
5. **Preserve Backward Compatibility** with existing ResilientClient

### 15.2 Key Benefits

**For httpx Users:**
- ✅ Minimal migration effort (change import only)
- ✅ Automatic retry and resilience
- ✅ No API learning curve
- ✅ Can switch back easily if needed

**For Existing aresilient Users:**
- ✅ No breaking changes
- ✅ Cleaner API for new code
- ✅ Better httpx ecosystem compatibility
- ✅ Optional migration path

**For aresilient Library:**
- ✅ Broader appeal and adoption
- ✅ Standards-compliant API
- ✅ Better positioning in ecosystem
- ✅ Reduced migration friction

### 15.3 Recommendations

1. ⭐ **Implement `Client` and `AsyncClient`** as primary new API
2. ⭐ **Keep `ResilientClient`** for backward compatibility (no deprecation)
3. ⭐ **Use composition** (wrap httpx.Client) for implementation
4. ⭐ **Follow phased rollout** (core → advanced → docs → testing)
5. ⭐ **Document migration paths** clearly
6. ⭐ **Gather community feedback** through beta release

### 15.4 Next Steps

1. **Get Stakeholder Approval** on design and naming
2. **Begin Phase 1 Implementation** (core Client/AsyncClient)
3. **Create Tracking Issues** for each phase
4. **Set Up Project Board** for task management
5. **Recruit Beta Testers** from community
6. **Plan Release Timeline** and communication

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
- **Retry Libraries Comparison:** See MISSING_FUNCTIONALITIES.md
- **aresilient Documentation:** https://durandtibo.github.io/aresilient/

---

## Appendix C: Comparison Table

| Feature | httpx.Client | aresilient.ResilientClient | aresilient.Client (Proposed) |
|---------|--------------|---------------------------|------------------------------|
| **Basic HTTP Methods** | ✅ | ✅ | ✅ |
| **Async Support** | ✅ (AsyncClient) | ✅ (AsyncResilientClient) | ✅ (AsyncClient) |
| **Context Manager** | ✅ | ✅ | ✅ |
| **Automatic Retry** | ❌ | ✅ | ✅ |
| **Exponential Backoff** | ❌ | ✅ | ✅ |
| **Circuit Breaker** | ❌ | ✅ | ✅ |
| **Custom Retry Logic** | ❌ | ✅ | ✅ |
| **Callbacks** | Partial | ✅ | ✅ |
| **httpx API Compatible** | ✅ | ❌ | ✅ |
| **Drop-in Replacement** | N/A | ❌ | ✅ |
| **All httpx Parameters** | ✅ | ⚠️ (limited) | ✅ |
| **Streaming Support** | ✅ | ⚠️ (limited) | ✅ (limited retry) |
| **HTTP/2 Support** | ✅ | ✅ (via httpx) | ✅ (via httpx) |
| **Connection Pooling** | ✅ | ✅ (via httpx) | ✅ (via httpx) |

---

**Last Updated:** February 2026  
**Next Review:** After Phase 1 implementation completion  
**Document Status:** 📋 Proposal - Awaiting approval and implementation
