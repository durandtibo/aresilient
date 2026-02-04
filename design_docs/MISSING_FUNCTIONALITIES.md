# Missing Functionalities Analysis for aresilient Library

## Executive Summary

This document provides a comprehensive analysis of missing functionalities in the aresilient library compared to similar resilient HTTP request libraries (urllib3, tenacity, requests-retry) and industry best practices. The analysis categorizes missing features by priority and provides implementation recommendations.

## Table of Contents

1. [Current Feature Set](#current-feature-set)
2. [Missing Observability Features](#missing-observability-features)
3. [Missing Resilience Patterns](#missing-resilience-patterns)
4. [Missing Configuration Options](#missing-configuration-options)
5. [Missing Developer Experience Features](#missing-developer-experience-features)
6. [Priority Recommendations](#priority-recommendations)

---

## Current Feature Set

### ✅ What aresilient Currently Provides

#### HTTP Methods
- **GET** (sync + async)
- **POST** (sync + async)
- **PUT** (sync + async)
- **DELETE** (sync + async)
- **PATCH** (sync + async)
- **HEAD** (sync + async)
- **OPTIONS** (sync + async)
- **Generic request** (sync + async) - allows custom HTTP methods

#### Retry Mechanisms
- Exponential backoff with configurable factor
- Optional jitter to prevent thundering herd
- Retry-After header support (integer seconds and HTTP-date formats)
- Configurable retryable status codes
- Timeout retry support
- Network error retry support

#### Configuration
- Default timeout (10s)
- Default max retries (3)
- Default backoff factor (0.3)
- Default retryable status codes (429, 500, 502, 503, 504)
- Per-request configuration override
- Custom httpx.Client support

#### Error Handling
- `HttpRequestError` with rich context
- Exception chaining
- Detailed error messages with method, URL, status code

#### Other Features
- Full async support with asyncio
- Type hints throughout
- Comprehensive logging (debug level)
- Parameter validation
- Callback/Event system (on_request, on_retry, on_success, on_failure)

---

## Missing Observability Features

### 🔴 HIGH PRIORITY

#### 1. Request/Response Statistics
**What it is:** Automatic collection of retry statistics

**Missing data:**
- Total number of attempts made
- Total time spent (including backoff)
- Which attempt succeeded
- Individual attempt timings
- Backoff times applied
- Whether Retry-After header was used

**Use cases:**
- Performance analysis
- Debugging slow requests
- Monitoring retry patterns
- SLA tracking

**Impact:** **MEDIUM-HIGH** - Valuable for production monitoring

**Recommendation:** ✅ **Implement** as optional feature (returned in response or callback)

**Example Usage:**
```python
from aresilient import get_with_automatic_retry

response, stats = get_with_automatic_retry(
    "https://api.example.com/data", return_stats=True
)
print(f"Succeeded on attempt {stats.attempts}/{stats.max_retries}")
print(f"Total time: {stats.total_time:.2f}s")
print(f"Retry delays: {stats.backoff_times}")
```

---

### 🟡 MEDIUM PRIORITY

#### 2. Structured Logging
**What it is:** Machine-readable log output with consistent fields

**Current state:**
- ✅ Has debug logging
- ❌ Logs are unstructured strings
- ❌ No correlation IDs
- ❌ No request context

**Missing:**
- JSON-formatted logs
- Correlation/trace IDs
- Consistent field names
- Log levels beyond DEBUG

**Use cases:**
- Log aggregation (ELK, Splunk)
- Automated log parsing
- Distributed tracing

**Impact:** **MEDIUM** - Helpful for large-scale deployments

**Recommendation:** ⚠️ **Consider** - May be better as separate logging adapter

---

## Missing Resilience Patterns

### 🔴 MEDIUM-HIGH PRIORITY

#### 1. Circuit Breaker Pattern
**What it is:** Stops making requests after consecutive failures to prevent cascading failures

**How it works:**
- **CLOSED** state: Normal operation, requests go through
- **OPEN** state: After N consecutive failures, stop making requests (fail fast)
- **HALF-OPEN** state: After timeout, try one request to check recovery

**Use cases:**
- Prevent overwhelming a failing service
- Fail fast instead of wasting time on retries
- Protect downstream services
- Graceful degradation

**Impact:** **MEDIUM-HIGH** - Critical for microservices, prevents cascading failures

**Comparison:**
- ✅ **tenacity** supports circuit breaker via `stop_after_attempt`
- ❌ **urllib3** does not have circuit breaker
- ❌ **requests-retry** does not have circuit breaker

**Recommendation:** ⚠️ **Consider for future** - Significant feature, may warrant separate package or module

**Example Usage:**
```python
from aresilient import get_with_automatic_retry, CircuitBreaker

circuit_breaker = CircuitBreaker(
    failure_threshold=5,  # Open circuit after 5 failures
    recovery_timeout=60.0,  # Try again after 60s
    expected_exception=HttpRequestError,
)

response = get_with_automatic_retry(
    "https://api.example.com/data", circuit_breaker=circuit_breaker
)
```

---

#### 2. Fallback Strategies
**What it is:** Alternative actions when request fails after all retries

**Missing capabilities:**
- Return cached response
- Return default value
- Call alternative endpoint
- Execute fallback function

**Use cases:**
- Graceful degradation
- Offline support
- Multi-region failover
- Default/stale data is better than no data

**Impact:** **MEDIUM** - Useful for high-availability systems

**Recommendation:** ⚠️ **Consider** - Could be implemented via callbacks

**Example Usage:**
```python
from aresilient import get_with_automatic_retry


def fallback_handler(error):
    # Return cached data or default
    return {"status": "degraded", "data": get_cached_data()}


response = get_with_automatic_retry(
    "https://api.example.com/data", fallback=fallback_handler
)
```

---

#### 3. Rate Limiting / Quota Management
**What it is:** Client-side rate limiting to stay within API quotas

**Missing capabilities:**
- Request throttling (max N requests per second/minute)
- Token bucket algorithm
- Leaky bucket algorithm
- Quota tracking across requests

**Use cases:**
- Prevent exceeding API rate limits
- Respect fair usage policies
- Distribute requests over time
- Avoid 429 errors proactively

**Impact:** **MEDIUM** - Prevents rate limit issues, but can be handled externally

**Recommendation:** ❌ **Do not implement** - Out of scope, can use external libraries like `ratelimit` or `pyrate-limiter`

---

## Missing Configuration Options

### 🔴 HIGH PRIORITY

#### 1. Custom Retry Predicates/Conditions
**What it is:** User-defined functions to decide whether to retry based on response

**Current limitations:**
- Can only retry on status codes
- Cannot retry based on response body
- Cannot retry based on headers
- Cannot retry based on custom business logic

**Missing:**
- `retry_if` callback function
- Retry on specific error messages
- Retry on empty response
- Retry on specific response patterns

**Use cases:**
- Retry if response contains "please retry"
- Retry if response is empty but status is 200
- Retry on partial failures
- Custom business logic (e.g., retry if balance is insufficient but will be replenished)

**Impact:** **HIGH** - Common need in real-world APIs

**Comparison:**
- ✅ **tenacity** has extensive retry condition support
- ⚠️ **urllib3** has limited custom logic support
- ❌ **requests-retry** limited to status codes

**Recommendation:** ✅ **Implement**

**Example Usage:**
```python
from aresilient import get_with_automatic_retry


def should_retry(response, exception):
    # Retry if response contains error message
    if response and "rate limit" in response.text.lower():
        return True
    # Retry on connection errors
    if isinstance(exception, ConnectionError):
        return True
    return False


response = get_with_automatic_retry(
    "https://api.example.com/data", retry_if=should_retry
)
```

---

### 🟡 MEDIUM PRIORITY

#### 2. Advanced Backoff Strategies
**What it is:** Alternative retry delay calculations beyond exponential backoff

**Current:**
- ✅ Exponential backoff
- ✅ Jitter

**Missing:**
- Linear backoff (`delay * attempt`)
- Fibonacci backoff (`fib(attempt)`)
- Constant/fixed backoff
- Custom backoff functions
- Max backoff cap

**Use cases:**
- Different services have different optimal backoff patterns
- Testing with predictable delays
- Fine-tuned performance optimization

**Impact:** **MEDIUM** - Useful but exponential backoff works for most cases

**Recommendation:** ⚠️ **Consider** - Could add `backoff_strategy` parameter

**Example Usage:**
```python
from aresilient import get_with_automatic_retry, LinearBackoff

response = get_with_automatic_retry(
    "https://api.example.com/data",
    backoff_strategy=LinearBackoff(base_delay=1.0),  # 1s, 2s, 3s, 4s...
)
```

---

#### 3. Max Wait Time / Total Timeout
**What it is:** Limit the total time spent on all retry attempts

**Current:**
- ✅ Per-request timeout
- ❌ No total/cumulative timeout across retries

**Missing:**
- `max_total_time` - Total time budget for all attempts
- `max_wait_time` - Maximum backoff delay (cap on exponential backoff)

**Use cases:**
- SLA guarantees (must return in 30s total)
- Prevent indefinite retries
- User experience (timeout after reasonable time)

**Impact:** **MEDIUM** - Useful for strict time constraints

**Recommendation:** ⚠️ **Consider**

**Example Usage:**
```python
from aresilient import get_with_automatic_retry

response = get_with_automatic_retry(
    "https://api.example.com/data",
    max_retries=10,
    max_total_time=30.0,  # Give up after 30s total, regardless of retry count
    max_wait_time=5.0,  # Cap backoff at 5s max
)
```

---

## Missing Developer Experience Features

### 🟡 MEDIUM PRIORITY

#### 1. Context Manager for Request Sessions
**What it is:** Pythonic context manager for managing request lifecycle

**Current:**
- ✅ Context manager support implemented via `ResilientClient` and `AsyncResilientClient`
- ✅ Automatic resource cleanup
- ✅ Shared configuration across requests

**Status:** ✅ **IMPLEMENTED** - Added in February 2026

**Implementation:**
- `ResilientClient` - Synchronous context manager
- `AsyncResilientClient` - Asynchronous context manager
- Both provide all HTTP methods (get, post, put, delete, patch, head, options, request)
- Per-request override of client defaults supported
- Automatic lifecycle management with `__enter__`/`__exit__` and `__aenter__`/`__aexit__`

**Impact:** **LOW-MEDIUM** - Convenience feature

**Example Usage:**
```python
from aresilient import ResilientClient

with ResilientClient(max_retries=5, timeout=30) as client:
    response1 = client.get("https://api.example.com/data1")
    response2 = client.post("https://api.example.com/data2", json={"key": "value"})
# Client automatically closed
```

**Async Example:**
```python
from aresilient import AsyncResilientClient

async with AsyncResilientClient(max_retries=5, timeout=30) as client:
    response1 = await client.get("https://api.example.com/data1")
    response2 = await client.post("https://api.example.com/data2", json={"key": "value"})
# Client automatically closed
```

---

#### 2. Retry Statistics/History
**What it is:** Detailed history of all retry attempts

**Missing:**
- Per-attempt response objects
- Per-attempt exceptions
- Timeline of events
- Decision logs (why retry/no-retry)

**Use cases:**
- Debugging failures
- Understanding retry behavior
- Performance optimization
- Audit logs

**Impact:** **LOW-MEDIUM** - Helpful for debugging

**Recommendation:** ⚠️ **Consider** - Can be expensive to track

---

#### 3. Mock/Testing Utilities
**What it is:** Helper utilities for testing code that uses aresilient

**Missing:**
- Mock retry behavior
- Simulate failures
- Test fixtures
- Retry simulators

**Current:**
- ✅ Basic test fixtures exist (`mock_sleep`, `mock_asleep`)
- ❌ No user-facing testing utilities

**Impact:** **LOW** - Users can mock httpx directly

**Recommendation:** ❌ **Low priority**

---

## Priority Recommendations

### 🔴 Implement Next (High Impact, Moderate Effort)

1. **Custom Retry Predicates** - High demand, flexible retry logic for complex scenarios
2. **Request/Response Statistics** - Valuable monitoring data

### 🟡 Consider for Next Release (Medium Impact)

3. **Max Total Time / Wait Time Caps** - Useful for strict SLAs
4. **Advanced Backoff Strategies** - More flexibility
5. **Structured Logging** - Or provide logging adapter

### 🟢 Future Considerations (Lower Priority)

6. **Circuit Breaker Pattern** - Major feature, complex implementation
7. **Fallback Strategies** - Can work via callbacks
8. ~~**Context Manager API**~~ - ✅ **IMPLEMENTED** (2026) - `ResilientClient` and `AsyncResilientClient`
9. **Retry History Tracking** - Debugging aid

### ❌ Out of Scope

- **Rate Limiting** - Better handled by external libraries
- **Connection Pooling** - Delegate to httpx
- **TRACE HTTP Method** - Rarely used, available via generic request
- **Mock/Testing Utilities** - Users can use httpx mocking

---

## Implementation Guidelines

### General Principles

1. **Maintain backward compatibility** - All new features should be opt-in
2. **Keep it simple** - Don't over-engineer, stick to core use cases
3. **Follow existing patterns** - Consistent with current API design
4. **Type safety** - Full type hints for all new features
5. **Comprehensive tests** - Unit and integration tests for everything
6. **Document thoroughly** - Clear examples in docstrings and README

### API Design Consistency

New features should follow these patterns:

```python
# Sync variant
def method_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    jitter_factor: float = 0.0,
    # New parameters here
    **kwargs: Any,
) -> httpx.Response: ...


# Async variant
async def method_with_automatic_retry_async(
    # Same signature
) -> httpx.Response: ...
```

### Testing Requirements

Each new feature needs:
- Unit tests (sync and async)
- Integration tests
- Error case tests
- Documentation tests (doctest)
- Type checking tests

### Documentation Requirements

Each new feature needs:
- Module docstring
- Function/class docstring with Google style
- Usage examples in docstring
- README examples
- API reference documentation

---

## Comparison Matrix

| Feature | aresilient | urllib3 | tenacity | requests-retry |
|---------|-----------|---------|----------|----------------|
| **HTTP Methods** |
| GET/POST/PUT/DELETE/PATCH | ✅ | ✅ | N/A | ✅ |
| HEAD | ✅ | ✅ | N/A | ✅ |
| OPTIONS | ✅ | ✅ | N/A | ✅ |
| **Retry Mechanisms** |
| Exponential Backoff | ✅ | ✅ | ✅ | ✅ |
| Jitter | ✅ | ✅ | ✅ | ✅ |
| Retry-After Header | ✅ | ✅ | ❌ | ✅ |
| Custom Retry Predicate | ❌ | ⚠️ | ✅ | ❌ |
| Max Total Time | ❌ | ❌ | ✅ | ❌ |
| **Observability** |
| Callbacks/Events | ✅ | ❌ | ✅ | ❌ |
| Statistics | ❌ | ❌ | ✅ | ❌ |
| Structured Logging | ❌ | ❌ | ❌ | ❌ |
| **Resilience Patterns** |
| Circuit Breaker | ❌ | ❌ | ✅ | ❌ |
| Fallback | ❌ | ❌ | ✅ | ❌ |
| **Other** |
| Async Support | ✅ | ❌ | ✅ | ❌ |
| Type Hints | ✅ | ⚠️ | ✅ | ⚠️ |

**Legend:**
- ✅ Implemented
- ❌ Not implemented
- ⚠️ Partial/limited

---

## Conclusion

The aresilient library has a solid foundation with comprehensive retry logic, async support, complete HTTP method coverage, and a callback system for observability.

The highest priority additions to bring it to feature parity with leading resilience libraries while maintaining its focused, lightweight design philosophy are:

1. **Custom retry predicates** - Flexible retry logic for complex scenarios
2. **Statistics collection** - Enhanced monitoring and debugging support

These additions would significantly enhance the library's production readiness and developer experience.
