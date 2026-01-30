# Library Structure Proposal for aresnet (2025)

> **⚠️ SUPERSEDED**: This document has been superseded by [LIBRARY_STRUCTURE_PROPOSAL_2026.md](LIBRARY_STRUCTURE_PROPOSAL_2026.md) which reflects the current state of the library including async support. This document is kept for historical reference.

## Executive Summary

After analyzing the current codebase (~900 lines, 12 modules), **I recommend keeping the current flat structure** with minor improvements. The library is still small and focused enough that a flat structure provides better discoverability and simplicity.

## Current Structure Analysis

### Current Layout
```
src/aresnet/
├── __init__.py          (42 lines)  - Main public API
├── config.py            (27 lines)  - Configuration constants
├── exception.py         (97 lines)  - Custom exceptions
├── utils.py             (25 lines)  - Utility functions
├── request.py          (142 lines)  - Core retry logic (sync)
├── request_async.py    (142 lines)  - Core retry logic (async)
├── get.py               (87 lines)  - GET request wrapper
├── post.py              (87 lines)  - POST request wrapper
├── put.py               (87 lines)  - PUT request wrapper
├── delete.py            (89 lines)  - DELETE request wrapper
└── patch.py             (88 lines)  - PATCH request wrapper
```

### Strengths of Current Structure
1. **Excellent discoverability**: All modules visible at `aresnet.*` level
2. **Clean separation**: Each HTTP method in its own file
3. **Simple imports**: `from aresnet import get_with_automatic_retry`
4. **Small codebase**: ~900 lines total - well below complexity threshold
5. **Clear responsibilities**: No module exceeds 150 lines
6. **Consistent patterns**: All HTTP method modules follow same structure

### Weaknesses
1. **Slightly cluttered namespace**: 12 files in one directory
2. **HTTP methods could be grouped**: GET/POST/PUT/DELETE/PATCH are similar
3. **Naming inconsistency**: `exception.py` vs. `exceptions` (plural)

## Alternative Structure Proposals

### Option A: Keep Flat Structure (RECOMMENDED)

**Structure:**
```
src/aresnet/
├── __init__.py
├── config.py
├── exceptions.py     # Renamed from exception.py (plural)
├── utils.py
├── request.py        # Core sync retry logic
├── request_async.py  # Core async retry logic
├── get.py
├── post.py
├── put.py
├── delete.py
└── patch.py
```

**Pros:**
- ✅ Minimal changes required
- ✅ Maximum discoverability
- ✅ Simple imports: `from aresnet import get_with_automatic_retry`
- ✅ Follows Python's "flat is better than nested" principle
- ✅ Easy navigation for newcomers
- ✅ No import complexity

**Cons:**
- ⚠️ Moderate number of files in root (acceptable for library this size)

**Changes Required:**
1. Rename `exception.py` → `exceptions.py` (standard Python convention)
2. Update imports in `__init__.py` and other modules

---

### Option B: Modular Sub-packages

**Structure:**
```
src/aresnet/
├── __init__.py          # Re-exports all public APIs
├── core/
│   ├── __init__.py
│   ├── config.py        # Configuration constants
│   ├── exceptions.py    # Custom exceptions
│   └── utils.py         # Utility functions
├── requests/
│   ├── __init__.py
│   ├── base.py          # Core retry logic (request.py + request_async.py)
│   ├── get.py
│   ├── post.py
│   ├── put.py
│   ├── delete.py
│   └── patch.py
```

**Pros:**
- ✅ Logical grouping of related functionality
- ✅ Clearer separation between core utilities and HTTP methods
- ✅ Scalable if library grows significantly
- ✅ Easier to add new categories (e.g., `middleware/`, `auth/`)

**Cons:**
- ❌ More complex imports: `from aresnet.requests import get_with_automatic_retry`
- ❌ Requires careful re-export in `__init__.py` to maintain simple API
- ❌ More files and directories to navigate
- ❌ Overkill for current codebase size
- ❌ Breaking change for users if they import from sub-modules

**Changes Required:**
1. Create new directory structure
2. Move and update all files
3. Update all imports throughout codebase
4. Update tests to match new structure
5. Maintain backward compatibility via re-exports

---

### Option C: Simplified Sub-packages

**Structure:**
```
src/aresnet/
├── __init__.py          # Re-exports all public APIs
├── config.py            # Keep at root (frequently accessed)
├── exceptions.py        # Keep at root (frequently accessed)
├── utils.py             # Keep at root (small utility module)
└── requests/
    ├── __init__.py
    ├── base.py          # Core retry logic
    ├── get.py
    ├── post.py
    ├── put.py
    ├── delete.py
    └── patch.py
```

**Pros:**
- ✅ Groups HTTP method implementations together
- ✅ Keeps commonly accessed modules at root
- ✅ Moderate complexity increase
- ✅ Good balance between organization and simplicity

**Cons:**
- ⚠️ Hybrid approach may feel inconsistent
- ⚠️ Still requires import updates
- ⚠️ Minimal benefit over flat structure for this size

**Changes Required:**
1. Create `requests/` directory
2. Move HTTP method files
3. Update imports
4. Update tests

---

### Option D: Functional Grouping

**Structure:**
```
src/aresnet/
├── __init__.py
├── config.py
├── exceptions.py
├── utils.py
└── methods/            # or http/ or api/
    ├── __init__.py
    ├── sync.py        # All sync methods (GET, POST, etc.)
    ├── async_.py      # All async methods
    └── core.py        # Shared retry logic
```

**Pros:**
- ✅ Further reduces number of files
- ✅ Groups related functionality
- ✅ Clear sync vs. async separation

**Cons:**
- ❌ Larger files (~400-500 lines each for sync.py)
- ❌ Harder to navigate to specific methods
- ❌ Less modular
- ❌ Worse for git blame/history

---

## Recommendation: Option A (Keep Flat with Minor Improvements)

### Rationale

1. **Library Size**: At ~900 lines, this library is well below the threshold where nested structure provides benefits. Most successful Python libraries keep flat structures until 2000-5000+ lines.

2. **Python Philosophy**: "Flat is better than nested" (Zen of Python). The current structure is already well-organized.

3. **User Experience**: Simpler imports mean better developer experience:
   ```python
   # Current (Good)
   from aresnet import get_with_automatic_retry

   # With sub-packages (More complex, no clear benefit)
   from aresnet.requests import get_with_automatic_retry
   ```

4. **Real-World Examples**: Similar-sized libraries maintain flat structures:
   - `httpx` core: Flat structure with ~30+ modules in root
   - `requests`: Flat structure for core functionality
   - `urllib3`: Flat-ish structure despite being larger

5. **Discoverability**: Developers can see all available modules at a glance without navigating subdirectories.

6. **Maintenance**: Fewer directories = less cognitive overhead for maintainers.

### When to Reconsider

Consider moving to Option B or C if:
- Library grows beyond 3000-5000 lines
- Adding major new feature categories (auth, middleware, caching, etc.)
- Number of modules exceeds 20-25
- Community feedback indicates confusion with flat structure

## Implementation Plan for Option A

### Phase 1: Naming Consistency
1. Rename `exception.py` → `exceptions.py` (follows Python convention)
2. Update import in `__init__.py`:
   ```python
   from aresnet.exceptions import HttpRequestError  # was: from aresnet.exception
   ```
3. Update imports in other modules (`request.py`, `request_async.py`, etc.)
4. Update all tests

### Phase 2: Documentation
1. Add module docstrings if missing
2. Ensure `__all__` is defined in each module
3. Update README if needed

### Phase 3: Optional Enhancements
1. Consider combining `request.py` and `request_async.py` if the duplication is significant
2. Add a simple module dependency diagram to docs

## Comparison Table

| Aspect | Flat (A) | Modular (B) | Simplified (C) | Functional (D) |
|--------|----------|-------------|----------------|----------------|
| Import simplicity | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Discoverability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Scalability | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Simplicity | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Maintenance effort | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Navigation | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Current size fit | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Total** | **33/35** | **24/35** | **28/35** | **28/35** |

## Conclusion

**Keep the flat structure (Option A) with just one improvement: rename `exception.py` to `exceptions.py` for consistency with Python conventions.**

The current structure is already well-designed for a library of this size. The proposed sub-package structures would add complexity without providing meaningful benefits at the current scale. Save the reorganization effort for when the library genuinely needs it (3000+ lines or major new feature categories).

### Immediate Action Items
1. ✅ Rename `exception.py` → `exceptions.py`
2. ✅ Update all imports
3. ✅ Run tests to verify
4. ✅ Update any documentation references

This minimal change improves consistency while maintaining all the benefits of the current structure.
