# Sync/Async Architecture Review and Improvement Proposal

**Date:** February 2026
**Status:** 🔄 Under Review
**Authors:** Architecture Review Team

---

## Executive Summary

This document reviews the current architecture of the **aresilient** library, a Python library for resilient HTTP requests supporting both synchronous and asynchronous APIs. The library has grown to approximately 6,600 lines across 40 modules and successfully transitioned from a flat structure to a modular architecture. However, significant code duplication exists between sync and async implementations (14 paired modules, ~3,300 lines duplicated).

**Key Findings:**
- ✅ Current modular structure is well-organized and scalable
- ⚠️ Significant duplication between sync/async implementations (~50% of codebase)
- ⚠️ Maintenance burden: changes must be made twice
- ⚠️ Risk of divergence between sync and async behavior

**Recommendations:**
This document proposes three alternative architectural approaches with varying levels of change:
1. **Minimal Change:** Extract shared logic to reduce duplication while maintaining current structure
2. **Moderate Refactor:** Shared core with thin sync/async wrappers
3. **Advanced Pattern:** Template-based code generation or protocol-based abstraction

---

## Table of Contents

1. [Current Architecture Analysis](#1-current-architecture-analysis)
2. [Structural Issues and Limitations](#2-structural-issues-and-limitations)
3. [Proposed Architectural Alternatives](#3-proposed-architectural-alternatives)
4. [Detailed Comparison and Trade-offs](#4-detailed-comparison-and-trade-offs)
5. [Migration Considerations](#5-migration-considerations)
6. [Recommendations](#6-recommendations)

---

## 1. Current Architecture Analysis

### 1.1 Current Structure Overview

```
src/aresilient/
├── __init__.py                    (120 lines)  - Public API exports
├── config.py                      (32 lines)   - Configuration constants
├── exceptions.py                  (81 lines)   - Exception definitions
├── callbacks.py                   (155 lines)  - Callback dataclasses
├── circuit_breaker.py             (464 lines)  - Circuit breaker pattern
│
├── Synchronous Modules (~1,650 lines):
│   ├── client.py                  (385 lines)  - Context manager client
│   ├── request.py                 (177 lines)  - Core retry logic
│   ├── get.py                     (152 lines)  - GET wrapper
│   ├── post.py                    (155 lines)  - POST wrapper
│   ├── put.py                     (154 lines)  - PUT wrapper
│   ├── delete.py                  (156 lines)  - DELETE wrapper
│   ├── patch.py                   (155 lines)  - PATCH wrapper
│   ├── head.py                    (165 lines)  - HEAD wrapper
│   └── options.py                 (163 lines)  - OPTIONS wrapper
│
├── Asynchronous Modules (~1,707 lines):
│   ├── client_async.py            (412 lines)  - Async context manager
│   ├── request_async.py           (181 lines)  - Async core retry
│   ├── get_async.py               (158 lines)  - Async GET
│   ├── post_async.py              (160 lines)  - Async POST
│   ├── put_async.py               (160 lines)  - Async PUT
│   ├── delete_async.py            (160 lines)  - Async DELETE
│   ├── patch_async.py             (160 lines)  - Async PATCH
│   ├── head_async.py              (167 lines)  - Async HEAD
│   └── options_async.py           (167 lines)  - Async OPTIONS
│
├── backoff/                       (~470 lines)
│   ├── __init__.py                (26 lines)   - Exports
│   ├── strategy.py                (318 lines)  - Backoff strategies
│   └── sleep.py                   (126 lines)  - Sleep utilities
│
├── retry/                         (~1,108 lines)
│   ├── __init__.py                (33 lines)   - Exports
│   ├── config.py                  (61 lines)   - Retry configuration
│   ├── strategy.py                (65 lines)   - Retry strategies
│   ├── manager.py                 (150 lines)  - Retry manager
│   ├── decider.py                 (130 lines)  - Retry decision logic
│   ├── executor.py                (326 lines)  - Sync retry executor
│   └── executor_async.py          (343 lines)  - Async retry executor
│
└── utils/                         (~795 lines)
    ├── __init__.py                (43 lines)   - Exports
    ├── callbacks.py               (121 lines)  - Callback utilities
    ├── exceptions.py              (239 lines)  - Exception utilities
    ├── response.py                (65 lines)   - Response utilities
    ├── retry_after.py             (73 lines)   - Retry-After parsing
    ├── retry_if_handler.py        (177 lines)  - Custom retry predicates
    └── validation.py              (77 lines)   - Parameter validation
```

**Total:** 40 Python files, ~6,612 lines

### 1.2 Code Duplication Analysis

#### Sync/Async Paired Modules (14 pairs)

| Module Type           | Sync Lines | Async Lines | Total | Similarity |
|-----------------------|------------|-------------|-------|------------|
| **HTTP Clients**      | 385        | 412         | 797   | ~90%       |
| **Core Request**      | 177        | 181         | 358   | ~95%       |
| **GET Method**        | 152        | 158         | 310   | ~98%       |
| **POST Method**       | 155        | 160         | 315   | ~98%       |
| **PUT Method**        | 154        | 160         | 314   | ~98%       |
| **DELETE Method**     | 156        | 160         | 316   | ~98%       |
| **PATCH Method**      | 155        | 160         | 315   | ~98%       |
| **HEAD Method**       | 165        | 167         | 332   | ~98%       |
| **OPTIONS Method**    | 163        | 167         | 330   | ~98%       |
| **Retry Executors**   | 326        | 343         | 669   | ~93%       |
| **TOTAL**             | **1,988**  | **2,068**   | **4,056** | **~95%** |

**Key Observation:** Approximately **61%** of the codebase (4,056 / 6,612 lines) consists of sync/async pairs with **~95% similarity**.

#### Duplication Breakdown by Category

1. **Nearly Identical (98% similarity):**
   - HTTP method wrappers (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
   - Only differences: `async`/`await` keywords, client type hints

2. **High Similarity (90-95%):**
   - Context manager clients (client.py vs client_async.py)
   - Core request functions (request.py vs request_async.py)
   - Retry executors (executor.py vs executor_async.py)
   - Differences: async keywords + slightly different error handling patterns

3. **Fully Shared (no duplication):**
   - Configuration (config.py)
   - Exceptions (exceptions.py)
   - Callbacks (callbacks.py)
   - Circuit breaker (circuit_breaker.py)
   - Utilities (utils/*)
   - Backoff strategies (backoff/*)

### 1.3 Strengths of Current Architecture

1. ✅ **Clear Separation:** Easy to identify sync vs async code
2. ✅ **Simple Imports:** Straightforward API (`from aresilient import get_with_automatic_retry`)
3. ✅ **Independent Testing:** Each version can be tested separately
4. ✅ **Type Safety:** Full type hints for both sync and async
5. ✅ **No Runtime Overhead:** No abstraction layers affecting performance
6. ✅ **Explicit Async:** Users clearly understand async requirements
7. ✅ **Modular Organization:** Good separation via backoff/, retry/, utils/
8. ✅ **Backward Compatible:** Simple re-exports maintain API stability

### 1.4 Current Development Workflow

**When adding a new feature:**
1. Implement in sync version (e.g., `get.py`)
2. Copy to async version (e.g., `get_async.py`)
3. Add `async`/`await` keywords
4. Change `httpx.Client` → `httpx.AsyncClient`
5. Write tests for sync version
6. Copy and adapt tests for async version
7. Update documentation for both

**Example:** Adding HEAD and OPTIONS methods required:
- 4 implementation files (head.py, head_async.py, options.py, options_async.py)
- 4 test files (test_head.py, test_head_async.py, test_options.py, test_options_async.py)
- ~664 lines of mostly duplicated code

---

## 2. Structural Issues and Limitations

### 2.1 Code Duplication Issues

#### Problem 1: Maintenance Burden

**Issue:** Every feature change requires modification in two places.

**Example:**
```python
# Change in get.py
def get_with_automatic_retry(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    # ... 10 more parameters
) -> httpx.Response:
    """Docstring..."""
    validate_retry_params(timeout, max_retries, ...)
    # ... implementation

# MUST also change in get_async.py
async def get_with_automatic_retry_async(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    # ... 10 more parameters (DUPLICATED)
) -> httpx.Response:
    """Docstring... (DUPLICATED)"""
    validate_retry_params(timeout, max_retries, ...)  # (DUPLICATED)
    # ... implementation (DUPLICATED with async/await)
```

**Impact:**
- 2x development time for features
- 2x documentation maintenance
- 2x testing effort
- Risk of missing changes in one version

#### Problem 2: Risk of Divergence

**Issue:** Sync and async versions can unintentionally diverge in behavior.

**Example Scenarios:**
- Bug fix applied to sync but not async
- Parameter validation differs between versions
- Default values updated in one but not the other
- Error handling logic inconsistent

**Real Risk:**
```python
# Sync version
if response.status_code in status_forcelist:
    should_retry = True

# Async version (accidentally different)
if response.status_code in status_forcelist and attempt < max_retries:
    should_retry = True
```

**Impact:**
- Inconsistent behavior between sync and async APIs
- Users encounter different bugs depending on which API they use
- Difficult to catch in code review
- Requires careful testing of both versions

#### Problem 3: Testing Redundancy

**Issue:** Test suites are nearly identical.

**Statistics:**
- 789 total unit tests
- Approximately 50% are sync/async pairs
- Similar test patterns repeated with `async`/`await`

**Example:**
```python
# test_get.py
def test_successful_request():
    response = get_with_automatic_retry("https://api.example.com/data")
    assert response.status_code == 200

# test_get_async.py (nearly identical)
async def test_successful_request():
    response = await get_with_automatic_retry_async("https://api.example.com/data")
    assert response.status_code == 200
```

**Impact:**
- 2x test maintenance
- Slower test suite execution
- More code to review

### 2.2 Scalability Concerns

#### Concern 1: Linear Growth

**Current Pattern:**
- Adding 1 HTTP method = 2 implementation files + 2 test files
- Adding 1 feature to retry logic = changes in 2 executors
- Adding 1 client feature = changes in 2 client files

**Projection:**
- At 10 HTTP methods: 20 implementation files
- At 15 HTTP methods: 30 implementation files
- Current: 14 sync/async pairs (28 files)

#### Concern 2: Cognitive Load

**Issue:** Developers must remember to update both versions.

**Example Checklist for Adding a Feature:**
- [ ] Update sync implementation
- [ ] Update async implementation
- [ ] Update sync tests
- [ ] Update async tests
- [ ] Update sync documentation
- [ ] Update async documentation
- [ ] Verify behavior is identical
- [ ] Check type hints match
- [ ] Ensure error messages are consistent

**Impact:**
- Higher chance of errors
- Slower development velocity
- Steeper learning curve for contributors

### 2.3 Comparison with Similar Libraries

#### Example 1: httpx

**Approach:** Shared core with sync/async wrappers
```python
# httpx uses a shared Request/Response model
# Thin wrappers for sync vs async
class Client:
    def get(self, url):
        return self._send(Request("GET", url))

class AsyncClient:
    async def get(self, url):
        return await self._send_async(Request("GET", url))
```

**Benefits:**
- Single source of truth for core logic
- Reduced duplication

#### Example 2: aiohttp vs requests

**Approach:** Separate libraries
- `requests`: Pure synchronous
- `aiohttp`: Pure asynchronous

**Benefits:**
- No mixing of concerns
- Each optimized for its paradigm

**Drawbacks:**
- Different APIs
- Feature parity not guaranteed

#### Example 3: urllib3

**Approach:** Synchronous only, async support via compatibility layer
```python
# urllib3 is sync-only
# httpx provides async version with similar API
```

### 2.4 Technical Debt Assessment

| Issue                          | Severity | Impact | Urgency |
|--------------------------------|----------|--------|---------|
| Code duplication (~4,000 lines)| High     | High   | Medium  |
| Maintenance burden (2x work)   | High     | High   | Medium  |
| Risk of divergence             | Medium   | High   | Medium  |
| Testing redundancy             | Medium   | Medium | Low     |
| Scalability constraints        | Medium   | Medium | Low     |
| Documentation duplication      | Medium   | Medium | Low     |

**Overall Assessment:** 🟡 Moderate technical debt that should be addressed proactively before library grows further.

---

## 3. Proposed Architectural Alternatives

This section presents three alternative architectures, each with increasing levels of change and benefit.

### 3.1 Option A: Minimal Refactor - Extract Shared Logic

**Philosophy:** Reduce duplication while maintaining current structure and API.

#### Proposed Structure

```
src/aresilient/
├── __init__.py                    - Public API (unchanged)
├── config.py                      - Configuration (unchanged)
├── exceptions.py                  - Exceptions (unchanged)
├── callbacks.py                   - Callbacks (unchanged)
├── circuit_breaker.py             - Circuit breaker (unchanged)
│
├── core/                          - NEW: Shared core logic
│   ├── __init__.py
│   ├── http_method.py             - HTTP method definitions
│   ├── retry_logic.py             - Shared retry logic
│   └── validation.py              - Shared parameter validation
│
├── Synchronous (thin wrappers):
│   ├── client.py                  - Calls core with sync client
│   ├── request.py                 - Sync wrapper around core
│   ├── get.py                     - Sync GET (thin wrapper)
│   ├── post.py                    - Sync POST (thin wrapper)
│   └── ... (other HTTP methods)
│
├── Asynchronous (thin wrappers):
│   ├── client_async.py            - Calls core with async client
│   ├── request_async.py           - Async wrapper around core
│   ├── get_async.py               - Async GET (thin wrapper)
│   ├── post_async.py              - Async POST (thin wrapper)
│   └── ... (other HTTP methods)
│
├── backoff/                       - Unchanged
├── retry/                         - Partially refactored
│   ├── executor.py                - Thin sync wrapper
│   ├── executor_async.py          - Thin async wrapper
│   └── executor_core.py           - NEW: Shared execution logic
└── utils/                         - Unchanged
```

#### Implementation Example

**Before (Duplicated):**
```python
# get.py
def get_with_automatic_retry(url, *, timeout, max_retries, ...):
    validate_retry_params(timeout, max_retries, ...)
    # ... 100 lines of retry logic

# get_async.py
async def get_with_automatic_retry_async(url, *, timeout, max_retries, ...):
    validate_retry_params(timeout, max_retries, ...)
    # ... 100 lines of DUPLICATED retry logic
```

**After (Shared Core):**
```python
# core/http_method.py
class HttpMethodLogic:
    @staticmethod
    def prepare_request(url, timeout, max_retries, ...):
        validate_retry_params(timeout, max_retries, ...)
        # ... shared preparation logic
        return config

    @staticmethod
    def should_retry(response, exception, config):
        # ... shared retry decision logic
        return bool

# get.py (thin wrapper - ~30 lines)
def get_with_automatic_retry(url, *, timeout, max_retries, ...):
    config = HttpMethodLogic.prepare_request(url, timeout, max_retries, ...)
    return execute_with_retry(
        method="GET",
        url=url,
        config=config,
        client_func=httpx.Client,
    )

# get_async.py (thin wrapper - ~30 lines)
async def get_with_automatic_retry_async(url, *, timeout, max_retries, ...):
    config = HttpMethodLogic.prepare_request(url, timeout, max_retries, ...)
    return await execute_with_retry_async(
        method="GET",
        url=url,
        config=config,
        client_func=httpx.AsyncClient,
    )
```

#### Benefits

1. ✅ **50% Reduction in Code:** ~2,000 lines eliminated
2. ✅ **Single Source of Truth:** Core logic defined once
3. ✅ **Reduced Divergence Risk:** Shared logic can't diverge
4. ✅ **Backward Compatible:** No API changes required
5. ✅ **Minimal Migration:** Refactor internals, keep public API
6. ✅ **Easier Maintenance:** Bug fixes in one place
7. ✅ **Faster Feature Development:** Write once, use in both

#### Drawbacks

1. ❌ **Indirection:** Slightly more complex call chains
2. ❌ **Some Duplication Remains:** Wrappers still duplicated
3. ❌ **Refactoring Effort:** ~40 hours of work
4. ❌ **Risk of Breaking Changes:** Must ensure behavior unchanged
5. ❌ **Testing Updates:** Tests may need adjustments

#### Implementation Effort

| Phase                          | Effort    | Risk   |
|--------------------------------|-----------|--------|
| Create core/ module            | 8 hours   | Low    |
| Refactor HTTP method wrappers  | 16 hours  | Medium |
| Refactor retry executors       | 12 hours  | Medium |
| Update tests                   | 8 hours   | Low    |
| Documentation updates          | 4 hours   | Low    |
| **TOTAL**                      | **48 hours** | **Medium** |

### 3.2 Option B: Moderate Refactor - Shared Core with Protocol Abstraction

**Philosophy:** Use Python protocols and generics to unify sync/async under a common interface.

#### Proposed Structure

```
src/aresilient/
├── __init__.py                    - Public API (re-exports)
├── config.py                      - Configuration
├── exceptions.py                  - Exceptions
├── callbacks.py                   - Callbacks
├── circuit_breaker.py             - Circuit breaker
│
├── core/                          - NEW: Core abstractions
│   ├── __init__.py
│   ├── protocol.py                - HttpClientProtocol, RequestProtocol
│   ├── engine.py                  - Generic request engine
│   ├── retry_engine.py            - Generic retry engine
│   └── method_factory.py          - HTTP method factory
│
├── adapters/                      - NEW: Sync/async adapters
│   ├── __init__.py
│   ├── sync_adapter.py            - httpx.Client adapter
│   └── async_adapter.py           - httpx.AsyncClient adapter
│
├── Synchronous (simple facades):
│   ├── client.py                  - Facade over core engine (sync)
│   ├── methods.py                 - All sync methods in one file
│   └── request.py                 - Sync request wrapper
│
├── Asynchronous (simple facades):
│   ├── client_async.py            - Facade over core engine (async)
│   ├── methods_async.py           - All async methods in one file
│   └── request_async.py           - Async request wrapper
│
├── backoff/                       - Unchanged
├── retry/                         - Simplified
│   ├── config.py
│   ├── strategy.py
│   └── engine.py                  - Unified retry engine
└── utils/                         - Unchanged
```

#### Implementation Example

**Core Protocol:**
```python
# core/protocol.py
from typing import Protocol, runtime_checkable, TypeVar

ResponseT = TypeVar('ResponseT')

@runtime_checkable
class HttpClientProtocol(Protocol[ResponseT]):
    """Protocol for HTTP clients (sync or async)."""

    def request(self, method: str, url: str, **kwargs) -> ResponseT:
        """Send HTTP request. May be sync or async."""
        ...

# Adapter implementations
# adapters/sync_adapter.py
class SyncHttpClient:
    def __init__(self, client: httpx.Client):
        self._client = client

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        return self._client.request(method, url, **kwargs)

# adapters/async_adapter.py
class AsyncHttpClient:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        return await self._client.request(method, url, **kwargs)
```

**Unified Engine:**
```python
# core/engine.py
from typing import Generic, TypeVar, Callable, Union
import inspect

ClientT = TypeVar('ClientT')
ResponseT = TypeVar('ResponseT')

class RequestEngine(Generic[ClientT, ResponseT]):
    """Generic request engine supporting both sync and async."""

    def __init__(self, client: ClientT, config: RequestConfig):
        self._client = client
        self._config = config

    def execute(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Union[ResponseT, Awaitable[ResponseT]]:
        """Execute request, returning Response or Awaitable[Response]."""
        request_func = getattr(self._client, method.lower())

        # Detect if async
        if inspect.iscoroutinefunction(request_func):
            return self._execute_async(request_func, url, **kwargs)
        else:
            return self._execute_sync(request_func, url, **kwargs)

    def _execute_sync(self, func, url, **kwargs) -> ResponseT:
        # Shared retry logic
        for attempt in range(self._config.max_retries + 1):
            try:
                response = func(url, **kwargs)
                if not self._should_retry(response):
                    return response
            except Exception as e:
                if not self._should_retry_exception(e):
                    raise
            self._sleep(attempt)
        raise MaxRetriesExceeded()

    async def _execute_async(self, func, url, **kwargs) -> ResponseT:
        # Same logic as _execute_sync but with await
        for attempt in range(self._config.max_retries + 1):
            try:
                response = await func(url, **kwargs)
                if not self._should_retry(response):
                    return response
            except Exception as e:
                if not self._should_retry_exception(e):
                    raise
            await self._sleep_async(attempt)
        raise MaxRetriesExceeded()
```

**Simple Facades:**
```python
# Sync methods.py (all methods in one file)
from core.engine import RequestEngine
from adapters.sync_adapter import SyncHttpClient

def get_with_automatic_retry(url, **kwargs):
    """GET request with retry."""
    config = _prepare_config(**kwargs)
    client = SyncHttpClient(httpx.Client())
    engine = RequestEngine(client, config)
    return engine.execute("GET", url, **kwargs)

def post_with_automatic_retry(url, **kwargs):
    """POST request with retry."""
    config = _prepare_config(**kwargs)
    client = SyncHttpClient(httpx.Client())
    engine = RequestEngine(client, config)
    return engine.execute("POST", url, **kwargs)

# ... all other methods

# Async methods_async.py (all methods in one file)
async def get_with_automatic_retry_async(url, **kwargs):
    """Async GET request with retry."""
    config = _prepare_config(**kwargs)
    client = AsyncHttpClient(httpx.AsyncClient())
    engine = RequestEngine(client, config)
    return await engine.execute("GET", url, **kwargs)

# ... all other methods
```

#### Benefits

1. ✅ **70% Reduction in Code:** ~2,800 lines eliminated
2. ✅ **Single Implementation:** Core logic written once
3. ✅ **Type Safe:** Protocols provide static type checking
4. ✅ **Extensible:** Easy to add new HTTP methods
5. ✅ **DRY:** Maximum code reuse
6. ✅ **Modern Python:** Leverages Python 3.8+ features
7. ✅ **Testable:** Test core engine once, facades are trivial

#### Drawbacks

1. ❌ **Higher Complexity:** Protocols and generics add cognitive load
2. ❌ **Larger Refactor:** ~80 hours of work
3. ❌ **Breaking Risk:** More complex refactor, higher risk
4. ❌ **Learning Curve:** Contributors need to understand protocols
5. ❌ **Debugging:** Stack traces may be deeper
6. ❌ **Python 3.8+ Required:** May limit compatibility

#### Implementation Effort

| Phase                          | Effort    | Risk   |
|--------------------------------|-----------|--------|
| Design protocols               | 8 hours   | Low    |
| Implement core engine          | 24 hours  | High   |
| Create adapters                | 8 hours   | Medium |
| Refactor to facades            | 24 hours  | High   |
| Update tests                   | 16 hours  | Medium |
| Documentation updates          | 8 hours   | Low    |
| **TOTAL**                      | **88 hours** | **High** |

### 3.3 Option C: Advanced Pattern - Code Generation

**Philosophy:** Generate sync/async code from a single source of truth using templates or decorators.

#### Approach 1: Template-Based Generation

**Structure:**
```
src/aresilient/
├── templates/                     - NEW: Code templates
│   ├── http_method.py.jinja2      - Template for HTTP methods
│   └── client.py.jinja2           - Template for clients
│
├── generators/                    - NEW: Code generators
│   ├── __init__.py
│   └── generate.py                - Generation script
│
├── Generated (at build time):
│   ├── get.py                     - Generated sync GET
│   ├── get_async.py               - Generated async GET
│   └── ... (all other methods)
```

**Template Example:**
```jinja2
{# http_method.py.jinja2 #}
{% if is_async %}async {% endif %}def {{ method }}_with_automatic_retry{% if is_async %}_async{% endif %}(
    url: str,
    *,
    client: httpx.{% if is_async %}Async{% endif %}Client | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    # ... other parameters
) -> httpx.Response:
    """{{ method.upper() }} request with automatic retry."""
    validate_retry_params(timeout, max_retries, ...)

    {% if is_async %}
    async with httpx.AsyncClient() as client:
        response = await client.{{ method }}(url, **kwargs)
    {% else %}
    with httpx.Client() as client:
        response = client.{{ method }}(url, **kwargs)
    {% endif %}

    return response
```

**Build Process:**
```bash
# Generate code during build
python -m aresilient.generators.generate
# Creates get.py, get_async.py, post.py, post_async.py, etc.
```

#### Approach 2: Decorator-Based Generation

**Structure:**
```python
# core/decorators.py
def http_method(method: str):
    """Decorator to generate sync and async versions."""
    def decorator(func):
        # Generate sync version
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Generate async version
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return sync_wrapper, async_wrapper
    return decorator

# Usage
@http_method("GET")
def get_base(url, client, **kwargs):
    """Base GET implementation."""
    return client.request("GET", url, **kwargs)

# Automatically creates:
# - get_with_automatic_retry (sync)
# - get_with_automatic_retry_async (async)
```

#### Benefits

1. ✅ **DRY to the Extreme:** Write once, generate both versions
2. ✅ **Guaranteed Consistency:** Impossible for sync/async to diverge
3. ✅ **Minimal Source Code:** Only templates or decorated functions
4. ✅ **Easy Updates:** Change template, regenerate all
5. ✅ **Scalable:** Adding methods is trivial

#### Drawbacks

1. ❌ **Build Complexity:** Requires generation step
2. ❌ **IDE Support:** Generated code may confuse IDEs
3. ❌ **Debugging:** Generated code harder to debug
4. ❌ **Over-Engineering:** May be overkill for this library size
5. ❌ **Learning Curve:** Contributors must understand generation
6. ❌ **Tooling:** Requires Jinja2 or similar dependencies
7. ❌ **Source of Truth:** Template syntax less readable than Python

#### Implementation Effort

| Phase                          | Effort    | Risk   |
|--------------------------------|-----------|--------|
| Design template system         | 16 hours  | Medium |
| Create templates               | 24 hours  | High   |
| Build generation pipeline      | 16 hours  | High   |
| Update build system            | 8 hours   | Medium |
| Migrate existing code          | 32 hours  | High   |
| Update tests                   | 16 hours  | Medium |
| Documentation                  | 8 hours   | Low    |
| **TOTAL**                      | **120 hours** | **Very High** |

**Recommendation:** ❌ **Not recommended** for this library. Over-engineered for current needs.

---

## 4. Detailed Comparison and Trade-offs

### 4.1 Comparison Matrix

| Aspect                  | Current | Option A (Extract) | Option B (Protocol) | Option C (Generate) |
|-------------------------|---------|--------------------|---------------------|---------------------|
| **Code Duplication**    | ~4,000  | ~2,000             | ~1,200              | ~0                  |
| **Maintenance Burden**  | High    | Medium             | Low                 | Very Low            |
| **Implementation Effort** | 0     | 48 hours           | 88 hours            | 120 hours           |
| **Complexity**          | Low     | Medium             | High                | Very High           |
| **Risk**                | N/A     | Medium             | High                | Very High           |
| **Backward Compat.**    | ✅      | ✅                 | ✅                  | ✅                  |
| **Type Safety**         | ✅      | ✅                 | ✅                  | ⚠️                  |
| **IDE Support**         | ✅      | ✅                 | ✅                  | ⚠️                  |
| **Debuggability**       | ✅      | ✅                 | ⚠️                  | ❌                  |
| **Learning Curve**      | Low     | Low                | Medium              | High                |
| **Future Flexibility**  | Medium  | High               | High                | Medium              |
| **Performance**         | ✅      | ✅                 | ✅                  | ✅                  |

### 4.2 Trade-off Analysis

#### Simplicity vs. Maintainability

**Current Architecture:**
- ✅ Simple: Flat, explicit sync/async separation
- ❌ Maintainability: High duplication, 2x effort

**Option A (Extract Shared Logic):**
- ✅ Balanced: Some abstraction, still straightforward
- ✅ Better maintainability: 50% less duplication
- Slight complexity increase acceptable for large benefit

**Option B (Protocol Abstraction):**
- ❌ More complex: Protocols, generics, type variables
- ✅ Excellent maintainability: Minimal duplication
- Higher complexity may not justify benefit at current size

**Option C (Code Generation):**
- ❌ Very complex: Build system, templates, generation
- ✅ Perfect maintainability: Zero duplication
- Complexity far exceeds benefit for this library

#### Developer Experience vs. User Experience

**Current:**
- Developer: Easy to understand, hard to maintain
- User: Simple, clear API

**Option A:**
- Developer: Still easy, easier to maintain
- User: Unchanged (backward compatible)
- **Winner:** Best balance

**Option B:**
- Developer: Steeper learning curve, but easier maintenance
- User: Unchanged (backward compatible)
- **Risk:** New contributors may struggle with abstractions

**Option C:**
- Developer: Difficult to understand, difficult to contribute
- User: Unchanged (backward compatible)
- **Risk:** High barrier to contribution

#### Short-term vs. Long-term

**Current:**
- Short-term: No effort required
- Long-term: Technical debt accumulates

**Option A:**
- Short-term: Moderate effort (48 hours)
- Long-term: Significant improvement, reduced debt

**Option B:**
- Short-term: High effort (88 hours)
- Long-term: Excellent architecture, but may be over-engineered

**Option C:**
- Short-term: Very high effort (120 hours)
- Long-term: Perfect DRY, but maintenance of generation system

### 4.3 Decision Criteria

#### When to Choose Current (No Change)

Choose if:
- Library is stable with few changes
- Team is small (1-2 developers)
- No plans for major growth
- Duplication acceptable trade-off

#### When to Choose Option A (Extract Shared Logic)

Choose if:
- Library is actively developed ✅
- Adding features frequently ✅
- Team has 2+ contributors ✅
- Want to reduce technical debt ✅
- Need backward compatibility ✅
- Want moderate improvement without high risk ✅

**Verdict:** ✅ **Best fit for aresilient's current state**

#### When to Choose Option B (Protocol Abstraction)

Choose if:
- Library is large (10,000+ lines)
- Heavy refactor acceptable
- Team comfortable with advanced Python
- Want maximum DRY
- Can accept learning curve

**Verdict:** 🟡 **Premature for current size, consider later**

#### When to Choose Option C (Code Generation)

Choose if:
- Library has 50+ sync/async pairs
- Extreme DRY required
- Build system already complex
- Team experienced with code generation

**Verdict:** ❌ **Over-engineered for this use case**

---

## 5. Migration Considerations

### 5.1 Migration Strategy for Option A (Recommended)

#### Phase 1: Foundation (Week 1)

1. **Create core/ module:**
   ```
   src/aresilient/core/
   ├── __init__.py
   ├── http_logic.py       - Shared HTTP method logic
   ├── retry_logic.py      - Shared retry logic
   └── validation.py       - Shared validation
   ```

2. **Extract shared validation:**
   - Move parameter validation to core/validation.py
   - Both sync and async import from core

3. **Extract retry decision logic:**
   - Move should_retry logic to core/retry_logic.py
   - Share between sync and async executors

#### Phase 2: HTTP Methods (Week 2-3)

4. **Refactor one HTTP method as proof of concept:**
   - Choose GET (most commonly used)
   - Extract shared logic to core/http_logic.py
   - Update get.py to use core
   - Update get_async.py to use core
   - Verify tests pass

5. **Apply pattern to remaining methods:**
   - POST, PUT, DELETE, PATCH, HEAD, OPTIONS
   - Use GET as template
   - Automated where possible

#### Phase 3: Executors (Week 3-4)

6. **Refactor retry executors:**
   - Extract shared logic to retry/executor_core.py
   - Update executor.py and executor_async.py
   - Verify all retry tests pass

#### Phase 4: Clients (Week 4)

7. **Refactor context manager clients:**
   - Extract shared client logic
   - Update client.py and client_async.py
   - Verify context manager tests pass

#### Phase 5: Testing and Documentation (Week 5)

8. **Comprehensive testing:**
   - Run full test suite
   - Add integration tests
   - Verify backward compatibility
   - Performance benchmarks

9. **Update documentation:**
   - Update architecture docs
   - Update contributor guide
   - Add migration notes

### 5.2 Backward Compatibility Strategy

#### Guarantee: No Breaking Changes

**Public API remains identical:**
```python
# Before refactor
from aresilient import get_with_automatic_retry
response = get_with_automatic_retry("https://api.example.com")

# After refactor (SAME)
from aresilient import get_with_automatic_retry
response = get_with_automatic_retry("https://api.example.com")
```

**Internal imports may change:**
```python
# Before (direct import)
from aresilient.request import request_with_automatic_retry

# After (may still work via re-exports)
from aresilient.request import request_with_automatic_retry  # Still works
from aresilient.core.retry_logic import RetryLogic  # New internal API
```

#### Deprecation Strategy

**If any internal APIs must change:**
1. Keep old API with deprecation warning
2. Document migration path
3. Provide 2-3 releases before removal
4. Update all examples to new API

**Example:**
```python
# Old internal API (deprecated)
def _should_retry(response, status_codes):
    warnings.warn(
        "_should_retry is deprecated. Use core.retry_logic.should_retry",
        DeprecationWarning,
        stacklevel=2
    )
    return should_retry(response, status_codes)
```

### 5.3 Testing Strategy

#### Test Coverage Requirements

1. **Maintain 100% backward compatibility:**
   - All existing tests must pass unchanged
   - No test modifications except for internal testing

2. **Add integration tests:**
   - Test sync and async produce identical results
   - Test core logic directly
   - Test edge cases in shared code

3. **Performance benchmarks:**
   - Ensure no performance regression
   - Benchmark before and after refactor

#### Test Organization

```
tests/
├── unit/
│   ├── test_get.py              - Unchanged
│   ├── test_get_async.py        - Unchanged
│   ├── core/                    - NEW
│   │   ├── test_http_logic.py   - Test shared HTTP logic
│   │   └── test_retry_logic.py  - Test shared retry logic
│   └── ...
├── integration/
│   ├── test_sync_async_parity.py - NEW: Verify identical behavior
│   └── ...
└── performance/
    └── benchmark_refactor.py     - NEW: Performance comparison
```

### 5.4 Risk Mitigation

#### High Risk: Behavioral Changes

**Mitigation:**
- Extract logic incrementally
- Test after each extraction
- Use property-based testing to verify equivalence
- Manual review of all changes

#### Medium Risk: Performance Regression

**Mitigation:**
- Benchmark before refactor
- Benchmark after each phase
- Monitor function call depth
- Profile critical paths

#### Low Risk: Documentation Drift

**Mitigation:**
- Update docs simultaneously with code
- Review docs in code review
- Automated doc tests

---

## 6. Recommendations

### 6.1 Recommended Approach: Option A (Extract Shared Logic)

**Why Option A:**

1. ✅ **Best ROI:** 50% code reduction for moderate effort (48 hours)
2. ✅ **Right Size:** Appropriate for library at ~6,600 lines
3. ✅ **Low Risk:** Incremental refactor with testing at each step
4. ✅ **Backward Compatible:** No API changes
5. ✅ **Maintainable:** Reduces duplication without excessive complexity
6. ✅ **Future-Proof:** Can evolve to Option B later if needed

**Not Option B because:**
- Premature for current library size
- Higher risk with limited additional benefit
- Can migrate to B later if library grows significantly

**Not Option C because:**
- Over-engineered for this use case
- High complexity, limited benefit
- Maintenance burden of generation system

### 6.2 Implementation Roadmap

#### Immediate (Q1 2026)

1. ✅ **Accept this design document**
2. 📝 **Create detailed implementation plan for Option A**
3. 🔨 **Begin Phase 1: Foundation (core/ module)**

#### Short-term (Q2 2026)

4. 🔨 **Complete Option A implementation**
   - Phases 2-5 as outlined in section 5.1
   - Target: 50% code reduction
   - Target: All tests passing

5. 📊 **Measure Impact**
   - Lines of code reduction
   - Maintenance effort improvement
   - Developer satisfaction

#### Medium-term (Q3-Q4 2026)

6. 🔍 **Monitor library growth**
   - Track total lines of code
   - Track number of sync/async pairs
   - Evaluate if further refactoring needed

7. 📚 **Documentation improvements**
   - Update architecture documentation
   - Create contributor guide
   - Add examples using shared core

#### Long-term (2027+)

8. 🔄 **Re-evaluate architecture**
   - If library exceeds 10,000 lines, consider Option B
   - If 20+ sync/async pairs, consider more aggressive refactor
   - Continue to balance simplicity and maintainability

### 6.3 Success Metrics

#### Code Metrics

| Metric                    | Current | Target | Status |
|---------------------------|---------|--------|--------|
| Total lines of code       | 6,612   | 5,000  | 📊     |
| Sync/async paired lines   | 4,056   | 2,000  | 📊     |
| Duplication percentage    | 61%     | 30%    | 📊     |
| Modules with duplication  | 14      | 7      | 📊     |

#### Development Metrics

| Metric                         | Current | Target | Status |
|--------------------------------|---------|--------|--------|
| Time to add HTTP method        | 4 hours | 2 hours | 📊    |
| Time to add retry feature      | 8 hours | 4 hours | 📊    |
| Test coverage                  | High    | High    | ✅    |
| Contributor onboarding time    | 2 days  | 1 day   | 📊    |

#### Quality Metrics

| Metric                    | Current | Target | Status |
|---------------------------|---------|--------|--------|
| Bugs due to sync/async divergence | Low | Zero | 📊 |
| Code review time          | Medium  | Low    | 📊     |
| Backward compatibility    | 100%    | 100%   | ✅     |

### 6.4 Decision

**Final Recommendation:** ✅ **Implement Option A (Extract Shared Logic)**

**Rationale:**
- Optimal balance of effort vs. benefit
- Reduces technical debt significantly
- Low risk, high value
- Keeps architecture simple and maintainable
- Positions library well for future growth

**Next Steps:**
1. Approve this design document
2. Create implementation ticket/issue
3. Assign to development team
4. Begin Phase 1 in Q1 2026

---

## Appendix

### A. Code Examples

#### A.1 Current Duplication Example

**get.py (Sync):**
```python
def get_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    jitter_factor: float = 0.0,
    **kwargs: Any,
) -> httpx.Response:
    """GET request with automatic retry."""
    validate_retry_params(timeout, max_retries, backoff_factor, jitter_factor)
    return request_with_automatic_retry(
        url,
        method="GET",
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        jitter_factor=jitter_factor,
        **kwargs,
    )
```

**get_async.py (Async - 98% identical):**
```python
async def get_with_automatic_retry_async(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,  # Only difference: AsyncClient
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
    jitter_factor: float = 0.0,
    **kwargs: Any,
) -> httpx.Response:
    """GET request with automatic retry."""  # Identical docstring
    validate_retry_params(timeout, max_retries, backoff_factor, jitter_factor)  # Identical
    return await request_with_automatic_retry_async(  # Only difference: async/await
        url,
        method="GET",
        client=client,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        jitter_factor=jitter_factor,
        **kwargs,
    )
```

#### A.2 Option A Refactored Example

**core/http_method.py (Shared):**
```python
from typing import Any
from aresilient.config import (
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BACKOFF_FACTOR,
    RETRY_STATUS_CODES,
)
from aresilient.utils import validate_retry_params

class HttpMethodConfig:
    """Shared configuration for HTTP methods."""

    @staticmethod
    def prepare(
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        status_forcelist: tuple[int, ...] = RETRY_STATUS_CODES,
        jitter_factor: float = 0.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Prepare and validate configuration."""
        validate_retry_params(timeout, max_retries, backoff_factor, jitter_factor)
        return {
            "timeout": timeout,
            "max_retries": max_retries,
            "backoff_factor": backoff_factor,
            "status_forcelist": status_forcelist,
            "jitter_factor": jitter_factor,
            **kwargs,
        }
```

**get.py (Sync - Thin wrapper):**
```python
import httpx
from aresilient.core.http_method import HttpMethodConfig
from aresilient.request import request_with_automatic_retry

def get_with_automatic_retry(
    url: str,
    *,
    client: httpx.Client | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """GET request with automatic retry."""
    config = HttpMethodConfig.prepare(**kwargs)
    return request_with_automatic_retry(
        url,
        method="GET",
        client=client,
        **config,
    )
```

**get_async.py (Async - Thin wrapper):**
```python
import httpx
from aresilient.core.http_method import HttpMethodConfig
from aresilient.request_async import request_with_automatic_retry_async

async def get_with_automatic_retry_async(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """GET request with automatic retry."""
    config = HttpMethodConfig.prepare(**kwargs)  # Same as sync
    return await request_with_automatic_retry_async(
        url,
        method="GET",
        client=client,
        **config,
    )
```

**Result:**
- Shared logic: 20 lines (in core/)
- Sync wrapper: 15 lines (down from 20)
- Async wrapper: 16 lines (down from 21)
- **Total: 51 lines** (down from 41 duplicated lines = **24% reduction per method**)
- **For 7 HTTP methods: ~280 lines saved**

### B. References

1. **Python Documentation:**
   - [PEP 544 - Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
   - [PEP 585 - Type Hinting Generics](https://peps.python.org/pep-0585/)

2. **Similar Libraries:**
   - [httpx: Sync/async HTTP client](https://www.python-httpx.org/)
   - [urllib3: HTTP client with retry logic](https://urllib3.readthedocs.io/)
   - [tenacity: Retry library](https://tenacity.readthedocs.io/)

3. **Design Patterns:**
   - Martin Fowler: "Refactoring: Improving the Design of Existing Code"
   - "Clean Architecture" by Robert C. Martin
   - "Design Patterns: Elements of Reusable Object-Oriented Software"

### C. Glossary

- **DRY (Don't Repeat Yourself):** Principle of reducing code duplication
- **Sync/Async:** Synchronous and asynchronous programming paradigms
- **Protocol:** Structural typing mechanism in Python (PEP 544)
- **Generic:** Type that can be parameterized with other types
- **Facade:** Simplified interface to a complex subsystem
- **Adapter:** Pattern to make incompatible interfaces compatible
- **Technical Debt:** Cost of future refactoring due to suboptimal design

---

**Document Version:** 1.0
**Last Updated:** February 8, 2026
**Next Review:** Q2 2026 or after Option A implementation
**Status:** 🔄 Awaiting Approval
