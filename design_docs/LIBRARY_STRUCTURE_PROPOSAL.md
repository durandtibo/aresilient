# Library Structure Proposal for aresnet

## Executive Summary

After analyzing the current codebase (~1,350 lines, 16 modules), **I recommend continuing with the flat structure**. The library has grown with comprehensive async support but remains appropriately sized for a flat architecture. The `*_async.py` naming convention provides clear sync/async separation while maintaining excellent discoverability and simplicity.

## Current Structure Analysis

### Current Layout

```
src/aresnet/
├── __init__.py          (52 lines)   - Main public API (18 exports)
├── config.py            (27 lines)   - Configuration constants
├── exceptions.py        (81 lines)   - Custom exception classes
├── utils.py             (33 lines)   - Utility/validation functions
├── request.py          (169 lines)   - Core retry logic (sync)
├── request_async.py    (173 lines)   - Core retry logic (async)
├── get.py               (85 lines)   - GET request wrapper (sync)
├── get_async.py         (90 lines)   - GET request wrapper (async)
├── post.py              (87 lines)   - POST request wrapper (sync)
├── post_async.py        (93 lines)   - POST request wrapper (async)
├── put.py               (90 lines)   - PUT request wrapper (sync)
├── put_async.py         (92 lines)   - PUT request wrapper (async)
├── delete.py            (89 lines)   - DELETE request wrapper (sync)
├── delete_async.py      (93 lines)   - DELETE request wrapper (async)
├── patch.py             (88 lines)   - PATCH request wrapper (sync)
└── patch_async.py       (93 lines)   - PATCH request wrapper (async)

Total: 16 Python files, ~1,350 lines
```

### Strengths of Current Structure

1. ✅ **Excellent discoverability**: All modules visible at `aresnet.*` level
2. ✅ **Clear sync/async separation**: `*_async.py` naming convention is intuitive
3. ✅ **Consistent patterns**: All HTTP method modules follow identical structure
4. ✅ **Simple imports**: `from aresnet import get_with_automatic_retry`
5. ✅ **Manageable size**: ~1,350 lines is still small for a library
6. ✅ **Clean responsibilities**: Each file has a single, focused purpose
7. ✅ **Parallel structure**: Easy to find async equivalents of sync functions
8. ✅ **No file exceeds 175 lines**: All modules remain readable and maintainable

### Current Weaknesses

1. ⚠️ **16 files in one directory**: Getting close to cognitive overload threshold (~20 files)
2. ⚠️ **Duplication**: Sync and async files are nearly identical (could be more DRY)
3. ⚠️ **Namespace growth**: Will become cluttered if more features are added
4. ⚠️ **No visual grouping**: Related files (sync/async pairs) are alphabetically separated in some editors
5. ⚠️ **Limited headroom**: Only ~4-5 more file pairs before restructuring becomes necessary

## Public API Overview

### Exported Functions (18 total)

**HTTP Method Functions:**
- Sync: `get_with_automatic_retry`, `post_with_automatic_retry`, `put_with_automatic_retry`, `delete_with_automatic_retry`, `patch_with_automatic_retry`
- Async: `get_with_automatic_retry_async`, `post_with_automatic_retry_async`, `put_with_automatic_retry_async`, `delete_with_automatic_retry_async`, `patch_with_automatic_retry_async`

**Core Request Functions:**
- `request_with_automatic_retry` (sync)
- `request_with_automatic_retry_async` (async)

**Configuration Constants:**
- `DEFAULT_TIMEOUT`
- `DEFAULT_MAX_RETRIES`
- `DEFAULT_BACKOFF_FACTOR`
- `RETRY_STATUS_CODES`

**Exceptions:**
- `HttpRequestError`

### Import Patterns

```python
# Method-specific (most common)
from aresnet import get_with_automatic_retry
from aresnet import get_with_automatic_retry_async

# Core request function (advanced)
from aresnet import request_with_automatic_retry

# Configuration
from aresnet import DEFAULT_TIMEOUT, RETRY_STATUS_CODES

# Exceptions
from aresnet import HttpRequestError
```

## Structure Options

### Option A: Keep Flat Structure (RECOMMENDED)

**Structure:**
```
src/aresnet/
├── __init__.py
├── config.py
├── exceptions.py
├── utils.py
├── request.py
├── request_async.py
├── get.py
├── get_async.py
├── post.py
├── post_async.py
├── put.py
├── put_async.py
├── delete.py
├── delete_async.py
├── patch.py
└── patch_async.py
```

**Pros:**
- ✅ Zero changes required - already optimal
- ✅ Maintains all current benefits
- ✅ Simple imports for users
- ✅ Easy to navigate with alphabetical sorting (pairs are grouped: delete/delete_async)
- ✅ Follows Python's "flat is better than nested" principle
- ✅ No breaking changes for existing users

**Cons:**
- ⚠️ Will need restructuring if library grows significantly
- ⚠️ Approaching the ~20 file threshold for flat structures

**Recommendation:** Stay with this structure until the library reaches **2,500+ lines** or **20+ files**, or when adding major new feature categories (auth, middleware, caching, webhooks, etc.).

---

### Option B: Minimal Sub-package Structure (Future consideration)

**Structure:**
```
src/aresnet/
├── __init__.py          # Re-exports all public APIs
├── config.py            # Keep at root (frequently accessed)
├── exceptions.py        # Keep at root (frequently accessed)
├── utils.py             # Keep at root (small utility)
└── methods/
    ├── __init__.py      # Re-exports for convenience
    ├── sync/
    │   ├── __init__.py
    │   ├── core.py      # request_with_automatic_retry
    │   ├── get.py
    │   ├── post.py
    │   ├── put.py
    │   ├── delete.py
    │   └── patch.py
    └── async_/          # Note: async_ to avoid reserved keyword
        ├── __init__.py
        ├── core.py      # request_with_automatic_retry_async
        ├── get.py
        ├── post.py
        ├── put.py
        ├── delete.py
        └── patch.py
```

**Pros:**
- ✅ Clear sync/async separation
- ✅ Better scalability for future features
- ✅ Logical grouping reduces root-level clutter
- ✅ Easy to add middleware, auth, etc., as sibling packages

**Cons:**
- ❌ More complex file structure
- ❌ Requires careful re-exports in `__init__.py` to maintain simple API
- ❌ Overkill for current size (~1,350 lines)
- ❌ May confuse users if they import from sub-modules directly

**Changes Required:**
1. Create directory structure
2. Move files to appropriate locations
3. Update all internal imports
4. Update tests
5. Maintain backward compatibility via comprehensive re-exports

---

### Option C: Hybrid Flat Structure (Alternative)

**Structure:**
```
src/aresnet/
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
src/aresnet/
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

## Recommendation: Option A (Continue with Flat Structure)

### Rationale

1. **Library Size**: At ~1,350 lines across 16 files, the library is still well below the threshold where nested structures provide clear benefits. Most successful Python libraries maintain flat structures until **2,500-5,000+ lines** or **20-30+ files**.

2. **Current Structure Works Well**: The `*_async.py` naming convention provides clear visual separation between sync and async variants while maintaining discoverability.

3. **User Experience**: Simple imports are critical for developer happiness:
   ```python
   # Current (Excellent)
   from aresnet import get_with_automatic_retry, get_with_automatic_retry_async

   # With sub-packages (More verbose, no clear benefit at this size)
   from aresnet.methods.sync import get_with_automatic_retry
   from aresnet.methods.async_ import get_with_automatic_retry_async
   ```

4. **Python Philosophy**: "Flat is better than nested" (Zen of Python). The current structure embodies this principle.

5. **Real-World Examples**: Comparable libraries maintain flat structures:
   - `httpx` core: Flat structure with 40+ modules
   - `requests`: Flat structure for core functionality
   - `aiohttp`: Minimal nesting despite large size

6. **Stability**: No breaking changes for users who may import from specific modules.

### When to Reconsider

Trigger a restructuring (move to Option B) when **any** of these conditions are met:

1. **Size threshold**: Library exceeds **2,500 lines** or **20 files**
2. **New feature categories**: Adding major new capabilities like:
   - Authentication/authorization modules
   - Middleware/interceptors
   - Response caching
   - WebSocket support
   - Connection pooling abstractions
   - Rate limiting decorators
   - Circuit breakers
3. **User feedback**: Community reports confusion with current structure
4. **Maintenance burden**: Team finds navigation difficult

### Immediate Action Items

**No structural changes recommended.** Instead, focus on:

1. ✅ **Documentation**:
   - Ensure all module docstrings are comprehensive
   - Verify `__all__` exports are correct in all modules

2. ✅ **Code quality**:
   - Audit for DRY violations between sync/async pairs
   - Consider helper functions for common patterns
   - Ensure consistent docstring style across all modules

3. ✅ **Testing**:
   - Verify test coverage for all 18 exported functions
   - Add integration tests for common usage patterns

4. ✅ **Future-proofing**:
   - Document the restructuring threshold in CONTRIBUTING.md
   - Create a migration guide template for when restructuring becomes necessary

## Comparison Table

| Aspect               | Flat (A)    | Minimal Sub (B) | Hybrid (C)  | Combined (D) |
|----------------------|-------------|-----------------|-------------|--------------|
| Import simplicity    | ⭐⭐⭐⭐⭐ | ⭐⭐⭐          | ⭐⭐⭐⭐    | ⭐⭐⭐⭐⭐    |
| Discoverability      | ⭐⭐⭐⭐⭐ | ⭐⭐⭐          | ⭐⭐⭐⭐    | ⭐⭐⭐⭐     |
| Scalability          | ⭐⭐⭐     | ⭐⭐⭐⭐⭐       | ⭐⭐⭐⭐    | ⭐⭐         |
| Simplicity           | ⭐⭐⭐⭐⭐ | ⭐⭐⭐          | ⭐⭐⭐⭐    | ⭐⭐⭐⭐     |
| Maintenance          | ⭐⭐⭐⭐⭐ | ⭐⭐⭐          | ⭐⭐⭐⭐    | ⭐⭐⭐       |
| Navigation           | ⭐⭐⭐⭐   | ⭐⭐⭐⭐        | ⭐⭐⭐⭐    | ⭐⭐⭐⭐⭐    |
| Current size fit     | ⭐⭐⭐⭐⭐ | ⭐⭐            | ⭐⭐⭐      | ⭐⭐⭐⭐     |
| Sync/async clarity   | ⭐⭐⭐⭐   | ⭐⭐⭐⭐⭐       | ⭐⭐⭐⭐⭐  | ⭐⭐⭐       |
| **Total**            | **36/40**   | **28/40**       | **32/40**   | **30/40**    |

## Evolution Timeline

### Phase 1: Current
- **Status**: ~1,350 lines, 16 files
- **Structure**: Flat with `*_async.py` pattern
- **Action**: Continue with current structure ✅

### Phase 2: Growth (~2,500-3,000 lines or 20+ files)
- **Trigger**: Adding 1-2 major feature categories
- **Action**: Evaluate Option B (minimal sub-packages)
- **Example additions**: Authentication, middleware, or caching

### Phase 3: Mature (~5,000+ lines or 30+ files)
- **Trigger**: Multiple feature categories, complex interdependencies
- **Action**: Full modular architecture with clear sub-packages
- **Structure**: Similar to `httpx`, `aiohttp` organization

## Conclusion

**Continue with the current flat structure (Option A).** The library is well-organized, appropriately sized, and provides excellent user experience. The `*_async.py` naming convention elegantly handles the dual sync/async architecture without introducing unnecessary complexity.

### Summary of Recommendations

1. ✅ **Keep current structure** - No changes needed
2. ✅ **Monitor growth** - Set clear thresholds for future restructuring
3. ✅ **Focus on quality** - Improve docs, tests, and consistency
4. ⏳ **Plan for future** - Be ready to restructure at 2,500+ lines

This minimal-change approach maintains stability for users while preserving all the benefits of the current structure. Save the reorganization effort for when the library genuinely needs it.

---

**Last Updated**: January 2026
**Next Review**: When library reaches 2,000 lines or 18 files (before restructuring threshold)
