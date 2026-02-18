# Library Structure Proposal for aresilient

## Executive Summary

**STATUS UPDATE (February 2026):** The library has successfully transitioned to a **modular structure** with subdirectories for backoff, core, retry, and utils modules. With ~7,000 lines across 43 files, the library follows a modular sub-package structure while keeping the public API clean through focused exports in `__init__.py`.

## Current Structure Analysis

### Current Layout (Updated February 2026)

```
src/aresilient/
├── __init__.py          (91 lines)   - Main public API (20 exports)
├── callbacks.py         (263 lines)  - Callback dataclasses
├── circuit_breaker.py   (467 lines)  - Circuit breaker implementation
├── client.py            (398 lines)  - Context manager client (sync)
├── client_async.py      (435 lines)  - Context manager client (async)
├── exceptions.py        (81 lines)   - Custom exception classes
├── request.py           (177 lines)  - Core retry logic (sync)
├── request_async.py     (181 lines)  - Core retry logic (async)
├── get.py               (136 lines)  - GET request wrapper (sync)
├── get_async.py                      - GET request wrapper (async)
├── post.py                           - POST request wrapper (sync)
├── post_async.py                     - POST request wrapper (async)
├── put.py                            - PUT request wrapper (sync)
├── put_async.py                      - PUT request wrapper (async)
├── delete.py                         - DELETE request wrapper (sync)
├── delete_async.py                   - DELETE request wrapper (async)
├── patch.py                          - PATCH request wrapper (sync)
├── patch_async.py                    - PATCH request wrapper (async)
├── head.py              (149 lines)  - HEAD request wrapper (sync)
├── head_async.py        (151 lines)  - HEAD request wrapper (async)
├── options.py           (147 lines)  - OPTIONS request wrapper (sync)
├── options_async.py     (151 lines)  - OPTIONS request wrapper (async)
├── backoff/
│   ├── __init__.py      (26 lines)   - Backoff exports
│   ├── strategy.py      (318 lines)  - Backoff strategies (Exponential, Linear, etc.)
│   └── sleep.py         (126 lines)  - Sleep utilities
├── core/
│   ├── __init__.py      (40 lines)   - Core exports
│   ├── config.py        (194 lines)  - Client configuration and defaults
│   ├── http_logic.py    (223 lines)  - Shared HTTP method logic (sync/async)
│   ├── retry_logic.py   (126 lines)  - Retry decision logic
│   └── validation.py    (104 lines)  - Parameter validation
├── retry/
│   ├── __init__.py      (33 lines)   - Retry exports
│   ├── config.py        (62 lines)   - Retry configuration
│   ├── strategy.py      (75 lines)   - Retry strategies
│   ├── manager.py       (158 lines)  - Retry manager
│   ├── decider.py       (106 lines)  - Retry decision logic
│   ├── executor_core.py (176 lines)  - Shared executor logic
│   ├── executor.py      (282 lines)  - Sync retry executor
│   └── executor_async.py (299 lines) - Async retry executor
└── utils/
    ├── __init__.py      (33 lines)   - Utility exports
    ├── exceptions.py    (239 lines)  - Exception utilities
    ├── response.py      (65 lines)   - Response utilities
    ├── retry_after.py   (73 lines)   - Retry-After header parsing
    └── retry_if_handler.py (177 lines) - Custom retry predicate handling

Total: 43 Python files, ~7,032 lines
```

### Strengths of Current Structure (Updated February 2026)

1. ✅ **Modular organization**: Clear separation with `backoff/`, `retry/`, and `utils/` subdirectories
2. ✅ **Excellent discoverability**: All public APIs still accessible at `aresilient.*` level via re-exports
3. ✅ **Clear sync/async separation**: `*_async.py` naming convention remains intuitive
4. ✅ **Consistent patterns**: All HTTP method modules follow identical structure
5. ✅ **Simple imports**: `from aresilient import get_with_automatic_retry` still works
6. ✅ **Scalable architecture**: Sub-packages allow for future growth
7. ✅ **Clean responsibilities**: Each file and module has a single, focused purpose
8. ✅ **Backward compatibility**: Re-exports maintain existing API surface
9. ✅ **No file exceeds 465 lines**: All modules remain readable and maintainable
10. ✅ **Context manager support**: `ResilientClient` and `AsyncResilientClient` for batch requests
11. ✅ **Advanced features**: Circuit breaker, custom backoff strategies, retry predicates

### Current Strengths vs. Original Concerns

**Original concerns (at 2,145 lines) that have been addressed:**
1. ✅ **RESOLVED**: 18 files in one directory → Now organized into subdirectories
2. ✅ **RESOLVED**: Namespace growth → Modular structure prevents root-level clutter
3. ✅ **PARTIALLY ADDRESSED**: Duplication → Retry logic extracted to dedicated modules
4. ✅ **RESOLVED**: No visual grouping → Subdirectories provide logical grouping
5. ✅ **RESOLVED**: Limited headroom → Can now grow indefinitely with current structure

## Public API Overview

### Top-Level Exports (`aresilient`)

**Context Manager Clients:**
- `ResilientClient` (sync)
- `AsyncResilientClient` (async)

**HTTP Method Functions:**
- Sync: `get_with_automatic_retry`, `post_with_automatic_retry`, `put_with_automatic_retry`, `delete_with_automatic_retry`, `patch_with_automatic_retry`, `head_with_automatic_retry`, `options_with_automatic_retry`
- Async: `get_with_automatic_retry_async`, `post_with_automatic_retry_async`, `put_with_automatic_retry_async`, `delete_with_automatic_retry_async`, `patch_with_automatic_retry_async`, `head_with_automatic_retry_async`, `options_with_automatic_retry_async`

**Core Request Functions:**
- `request_with_automatic_retry` (sync)
- `request_with_automatic_retry_async` (async)

**Exceptions:**
- `HttpRequestError`

**Version:**
- `__version__`

### Submodule Exports

**Backoff Strategies (`aresilient.backoff`):**
- `BackoffStrategy` (base class)
- `ExponentialBackoff`
- `LinearBackoff`
- `FibonacciBackoff`
- `ConstantBackoff`
- `calculate_sleep_time`

**Circuit Breaker (`aresilient.circuit_breaker`):**
- `CircuitBreaker`
- `CircuitBreakerError`
- `CircuitState`

**Callbacks (`aresilient.callbacks`):**
- `RequestInfo`
- `ResponseInfo`
- `RetryInfo`
- `FailureInfo`

**Configuration (`aresilient.core.config`):**
- `DEFAULT_TIMEOUT`
- `DEFAULT_MAX_RETRIES`
- `DEFAULT_BACKOFF_FACTOR`
- `RETRY_STATUS_CODES`

### Import Patterns

```python
# Context manager clients
from aresilient import ResilientClient, AsyncResilientClient

# Method-specific (most common)
from aresilient import get_with_automatic_retry
from aresilient import get_with_automatic_retry_async

# Core request function (advanced)
from aresilient import request_with_automatic_retry

# Backoff strategies
from aresilient.backoff import LinearBackoff, ExponentialBackoff

# Circuit breaker
from aresilient.circuit_breaker import CircuitBreaker

# Callbacks
from aresilient.callbacks import RequestInfo, RetryInfo

# Exceptions
from aresilient import HttpRequestError
```

## Structure Options

### ✅ Implemented: Modular Sub-package Structure (Based on Option B)

**Current Implementation (February 2026):**
```
src/aresilient/
├── __init__.py          # Main public API (HTTP methods, clients, exceptions)
├── callbacks.py         # Callback dataclasses
├── circuit_breaker.py   # Circuit breaker implementation
├── client.py / client_async.py  # Context managers
├── exceptions.py        # Custom exceptions
├── request.py / request_async.py  # Core request functions
├── [HTTP methods].py / [HTTP methods]_async.py  # GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
├── backoff/             # Backoff strategies
│   ├── __init__.py      # Backoff exports
│   ├── strategy.py      # BackoffStrategy classes
│   └── sleep.py         # Sleep utilities
├── core/                # Shared configuration and logic
│   ├── __init__.py      # Core exports
│   ├── config.py        # Client configuration and defaults
│   ├── http_logic.py    # Shared HTTP method logic (sync/async)
│   ├── retry_logic.py   # Retry decision logic
│   └── validation.py    # Parameter validation
├── retry/               # Retry execution framework
│   ├── __init__.py      # Retry exports
│   ├── config.py        # Retry configuration
│   ├── strategy.py      # Retry strategies
│   ├── manager.py       # Retry manager
│   ├── decider.py       # Decision logic
│   ├── executor_core.py # Shared executor logic
│   ├── executor.py      # Sync executor
│   └── executor_async.py  # Async executor
└── utils/               # Utility functions
    ├── __init__.py      # Utility exports
    ├── exceptions.py    # Exception utilities
    ├── response.py      # Response utilities
    ├── retry_after.py   # Retry-After parsing
    └── retry_if_handler.py  # Custom retry predicates
```

**Benefits Realized:**
- ✅ Clear feature separation (backoff, core, retry, utils)
- ✅ Scalable for future features
- ✅ Logical grouping reduces root-level clutter
- ✅ Easy to add new features in appropriate modules
- ✅ Supports ~7,000 lines of code comfortably

**User Experience:**
```python
# Top-level exports for HTTP methods and clients
from aresilient import get_with_automatic_retry
from aresilient import get_with_automatic_retry_async
from aresilient import ResilientClient

# Submodule imports for backoff strategies
from aresilient.backoff import ExponentialBackoff, LinearBackoff

# Submodule imports for circuit breaker
from aresilient.circuit_breaker import CircuitBreaker

# Submodule imports for retry framework (advanced)
from aresilient.retry import RetryConfig
```

### Alternative Structures (Historical Context - Not Implemented)

The following options were considered but not chosen in favor of the current modular structure:

#### Option C: Hybrid Flat Structure (Not Chosen)

**Structure:**
```
src/aresilient/
├── __init__.py
├── config.py
├── exceptions.py
├── utils.py
├── sync/
│   ├── __init__.py
│   ├── request.py      # Core retry logic
│   ├── get.py
│   ├── post.py
│   ├── put.py
│   ├── delete.py
│   └── patch.py
└── async_/
    ├── __init__.py
    ├── request.py      # Core retry logic
    ├── get.py
    ├── post.py
    ├── put.py
    ├── delete.py
    └── patch.py
```

**Pros:**
- ✅ Clean sync/async separation
- ✅ Reduced root-level files
- ✅ Removes `_async` suffix from filenames

**Cons:**
- ❌ Moderate complexity increase
- ❌ Import paths become longer if not re-exported
- ❌ Not worth the effort for current size

---

### Option D: Combined Modules (Not Recommended)

**Structure:**
```
src/aresilient/
├── __init__.py
├── config.py
├── exceptions.py
├── utils.py
├── request.py          # Both sync and async
├── get.py              # Both sync and async
├── post.py             # Both sync and async
├── put.py              # Both sync and async
├── delete.py           # Both sync and async
└── patch.py            # Both sync and async
```

**Pros:**
- ✅ Fewer files (11 instead of 16)
- ✅ Related functionality co-located

**Cons:**
- ❌ Larger files (~170-180 lines each)
- ❌ Harder to navigate (scroll to find sync vs async)
- ❌ Mixing sync/async paradigms in same file is confusing
- ❌ Worse for code review and git blame
- ❌ Goes against Python's preference for focused modules

---

## Recommendation: Current Modular Structure is Optimal ✅

### Rationale

1. **Library Size**: At ~7,032 lines across 43 files, the library has exceeded the threshold (~2,500 lines, 20+ files) where modular structures provide clear benefits. The current structure is appropriate for the size.

2. **Implemented Structure Works Excellently**: The modular sub-package approach provides clear organization with a clean separation between public API and internal implementation.

3. **User Experience**: Simple imports for common use cases:
   ```python
   # Top-level exports for HTTP methods and clients
   from aresilient import get_with_automatic_retry
   from aresilient import get_with_automatic_retry_async
   from aresilient import ResilientClient

   # Submodule imports for extended functionality
   from aresilient.backoff import ExponentialBackoff
   from aresilient.circuit_breaker import CircuitBreaker
   from aresilient.retry import RetryConfig
   ```

4. **Python Philosophy**: While "Flat is better than nested", at this size, "Explicit is better than implicit" and "Namespaces are one honking great idea" take precedence. The modular structure provides necessary organization.

5. **Real-World Examples**: Similar libraries use modular structures at this size:
   - `httpx`: Modular structure with subdirectories
   - `requests`: Modular internals with flat public API
   - `aiohttp`: Significant use of submodules

6. **Stability**: Backward compatibility maintained through comprehensive re-exports.

### Current Status (February 2026)

**Structure:** ✅ **Modular with subdirectories (backoff/, core/, retry/, utils/)**
**Size:** ~7,032 lines across 43 files
**Organization:** Excellent - features logically grouped
**API:** Clean - HTTP methods and clients at top level, extended functionality in submodules
**Scalability:** ✅ High - can grow indefinitely with current structure

### Future Considerations

The current modular structure should remain stable for the foreseeable future. Consider refinements when **any** of these conditions are met:

1. **Size threshold**: Library exceeds **10,000 lines** or **50+ files**
2. **New major feature categories**: Adding capabilities that don't fit current modules:
   - Authentication/authorization as separate module
   - Middleware/interceptors as separate module
   - Response caching as separate module
   - WebSocket support
   - Rate limiting as dedicated module
3. **User feedback**: Community reports confusion with current structure
4. **Maintenance burden**: Team finds navigation difficult

### Immediate Action Items (February 2026)

**No structural changes needed.** The current structure is optimal. Focus on:

1. ✅ **Documentation**:
   - Keep all module docstrings comprehensive and up-to-date
   - Verify `__all__` exports are correct in all modules
   - Maintain design documentation

2. ✅ **Code quality**:
   - Continue to audit for DRY violations between sync/async pairs
   - Use helper functions for common patterns (already done in retry/, utils/)
   - Ensure consistent docstring style across all modules

3. ✅ **Testing**:
   - Maintain comprehensive test coverage
   - Add integration tests for new features
   - Test backward compatibility with each change

4. ✅ **Future-proofing**:
   - Monitor library growth
   - Document the evolution in design docs
   - Keep this document updated with actual state

## Comparison Table (Historical Reference)

| Aspect               | Modular (Implemented) | Flat (Old)  | Hybrid (Not Used) | Combined (Not Used) |
|----------------------|-----------------------|-------------|-------------------|---------------------|
| Import simplicity    | ⭐⭐⭐⭐⭐           | ⭐⭐⭐⭐⭐  | ⭐⭐⭐⭐          | ⭐⭐⭐⭐⭐          |
| Discoverability      | ⭐⭐⭐⭐⭐           | ⭐⭐⭐⭐⭐  | ⭐⭐⭐⭐          | ⭐⭐⭐⭐           |
| Scalability          | ⭐⭐⭐⭐⭐           | ⭐⭐⭐      | ⭐⭐⭐⭐          | ⭐⭐               |
| Simplicity           | ⭐⭐⭐⭐             | ⭐⭐⭐⭐⭐  | ⭐⭐⭐⭐          | ⭐⭐⭐⭐           |
| Maintenance          | ⭐⭐⭐⭐⭐           | ⭐⭐⭐      | ⭐⭐⭐⭐          | ⭐⭐⭐             |
| Navigation           | ⭐⭐⭐⭐⭐           | ⭐⭐⭐      | ⭐⭐⭐⭐          | ⭐⭐⭐⭐⭐          |
| Current size fit     | ⭐⭐⭐⭐⭐           | ⭐⭐        | ⭐⭐⭐            | ⭐⭐               |
| Sync/async clarity   | ⭐⭐⭐⭐             | ⭐⭐⭐⭐    | ⭐⭐⭐⭐⭐        | ⭐⭐⭐             |
| **Total**            | **38/40**             | **29/40**   | **31/40**         | **28/40**           |

**Note:** The modular structure (implemented in February 2026) scores highest, especially for scalability, maintenance, navigation, and fit for current size (~7,000 lines).

## Evolution Timeline

### Phase 1: Initial Development (Early 2025)
- **Status**: ~1,350 lines, 16-18 files
- **Structure**: Flat with `*_async.py` pattern
- **Action**: Started with flat structure ✅

### Phase 2: Growth and Modularization (Mid-2025 to Early 2026)
- **Status**: ~7,032 lines, 43 files
- **Structure**: Modular with `backoff/`, `core/`, `retry/`, `utils/` subdirectories
- **Action**: Successfully transitioned to modular structure ✅
- **Key additions**:
  - Circuit breaker implementation (`circuit_breaker.py`)
  - Context manager clients (`client.py`, `client_async.py`)
  - Core shared logic module (`core/`)
  - Comprehensive retry execution framework (`retry/`)
  - Custom backoff strategies (`backoff/`)
  - Retry predicates (`retry_if` functionality in `utils/retry_if_handler.py`)
  - Callbacks and observability (`callbacks.py`)

### Phase 3: Current State (February 2026)
- **Status**: ~7,032 lines, 43 files, modular structure
- **Structure**: Optimal modular organization
- **Action**: Maintain current structure, focus on quality and documentation ✅
- **Features**: Complete HTTP library with resilience patterns

### Phase 4: Future (When 10,000+ lines or 50+ files)
- **Trigger**: Adding multiple major feature categories
- **Action**: Evaluate if further modularization needed
- **Example additions**: Authentication, middleware, caching, WebSockets

## Conclusion

**The library has successfully evolved to a modular structure that is optimal for its current size and complexity.**

### Summary of Current State (February 2026)

1. ✅ **Modular structure implemented** - Clear organization with backoff/, core/, retry/, utils/ subdirectories
2. ✅ **Appropriate for size** - ~7,032 lines across 43 files needs modular organization
3. ✅ **Clean public API** - Top-level exports for common use, submodules for extended functionality
4. ✅ **Highly scalable** - Can grow indefinitely with current structure

### Recommendations

1. ✅ **Maintain current structure** - No changes needed, structure is optimal
2. ✅ **Monitor growth** - Track when library reaches 10,000+ lines for next review
3. ✅ **Focus on quality** - Keep improving docs, tests, and code quality
4. ✅ **Update design docs** - Keep this document current with actual state

This structure balances organization, discoverability, and scalability while maintaining the excellent user experience that made the library successful. The transition from flat to modular structure was executed at the right time and has positioned the library well for continued growth.

---

**Last Updated**: February 2026
**Next Review**: When library reaches 10,000 lines or 50 files, or when adding major new feature categories
