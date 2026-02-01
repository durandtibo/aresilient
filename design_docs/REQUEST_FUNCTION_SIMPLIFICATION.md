# Request Function Simplification Design Document

## Problem Statement

The `request_with_automatic_retry` and `request_with_automatic_retry_async` functions are too complex and raise the following linting errors:

- **PLR0912**: Too many branches (19 > 12)
- **PLR0915**: Too many statements (58 > 50)

These functions need to be simplified to improve maintainability while preserving all existing functionality and maintaining backward compatibility.

## Current Implementation Analysis

### Function Complexity

Both functions currently have:
- **58 statements** (exceeding the limit of 50)
- **19 branches** (exceeding the limit of 12)
- Approximately 190 lines of code each (excluding docstrings)

### Current Structure

The functions follow this general flow:
1. Initialize variables (response, start_time, last_error, last_status_code)
2. Enter retry loop (attempt 0 to max_retries)
3. Within each attempt:
   - Invoke on_request callback
   - Make HTTP request
   - Handle successful response (status < 400)
     - Check retry_if predicate for success case
     - Invoke on_success callback if truly successful
     - Return response
   - Handle retryable error responses (status >= 400)
     - Check retry_if predicate vs status_forcelist
     - Raise HttpRequestError if not retryable
   - Handle TimeoutException
     - Check retry_if predicate
     - Call handle_exception_with_callback or raise with on_failure
   - Handle RequestError
     - Check retry_if predicate
     - Call handle_exception_with_callback or raise with on_failure
4. Calculate sleep time and invoke on_retry callback
5. Sleep/await sleep
6. Raise final error if all retries exhausted

### Complexity Drivers

The main sources of complexity are:

1. **Dual handling paths for retry_if predicate**: When `retry_if` is provided, the code duplicates error handling logic that would otherwise be delegated to utility functions
2. **Inline exception handling with callbacks**: Lines 215-243 and 256-283 duplicate similar logic for TimeoutException and RequestError when retry_if is present
3. **Multiple conditional branches**: Success path, retryable response path, two exception types, each with retry_if branches
4. **Callback invocation scattered throughout**: on_request, on_retry, on_success, on_failure are invoked at different points

## Proposed Simplification Approaches

### Approach 1: Extract retry_if Handling to Helper Function (Recommended)

**Complexity Reduction**: Reduces branches by ~6-8, statements by ~10-15

**Changes**:
1. Create new helper function `should_retry_with_predicate()` in `utils/` module
2. Move retry_if evaluation logic into this function
3. Create helper function `handle_retry_if_exception()` to consolidate exception handling when retry_if is used
4. Replace duplicated code blocks with function calls

**Example pseudocode**:
```python
def should_retry_with_predicate(
    retry_if: Callable | None,
    response: httpx.Response | None,
    exception: Exception | None,
    attempt: int,
    max_retries: int,
    url: str,
    method: str,
    on_failure: Callable | None,
    start_time: float,
) -> bool:
    """Evaluate retry_if predicate and handle early termination."""
    if retry_if is None:
        return True  # Delegate to other logic
    
    should_retry = retry_if(response, exception)
    
    if not should_retry or attempt == max_retries:
        # Create error and invoke callback
        # Raise appropriate exception
        ...
    
    return should_retry
```

**Pros**:
- Minimal changes to overall function structure
- Consolidates duplicated retry_if handling
- Easy to test and maintain
- Clear separation of concerns

**Cons**:
- Adds one more utility function to the codebase
- Still maintains the overall flow complexity

### Approach 2: State Machine Pattern

**Complexity Reduction**: Reduces branches by ~10-12, statements by ~20-25

**Changes**:
1. Extract request attempt logic into separate function `execute_request_attempt()`
2. Create result classes: `SuccessResult`, `RetryableResult`, `FinalErrorResult`
3. Use pattern matching or type checking to handle results
4. Separate callback handling into dedicated function

**Example pseudocode**:
```python
@dataclass
class RequestResult:
    """Base class for request results."""
    pass

@dataclass
class SuccessResult(RequestResult):
    response: httpx.Response
    attempt: int

@dataclass
class RetryableResult(RequestResult):
    status_code: int | None = None
    error: Exception | None = None
    attempt: int = 0

@dataclass
class FinalErrorResult(RequestResult):
    error: Exception
    response: httpx.Response | None = None

def execute_request_attempt(
    url: str,
    method: str,
    request_func: Callable,
    retry_if: Callable | None,
    status_forcelist: tuple,
    attempt: int,
    max_retries: int,
    **kwargs
) -> RequestResult:
    """Execute a single request attempt and return result."""
    # Implementation
    ...
```

**Pros**:
- Very clean separation of concerns
- Each function has a single responsibility
- Easier to test individual components
- Clearer control flow

**Cons**:
- Significant refactoring required
- More complex type system
- Potential performance overhead from object creation
- May be harder for contributors to understand initially

### Approach 3: Exception Handler Registry

**Complexity Reduction**: Reduces branches by ~5-7, statements by ~8-12

**Changes**:
1. Create exception handler registry mapping exception types to handler functions
2. Consolidate retry_if checking into a single function
3. Use registry lookup instead of multiple try-except blocks

**Example pseudocode**:
```python
EXCEPTION_HANDLERS = {
    httpx.TimeoutException: handle_timeout_exception,
    httpx.RequestError: handle_request_error,
}

def handle_exception_with_retry_if(
    exc: Exception,
    retry_if: Callable | None,
    attempt: int,
    max_retries: int,
    # ... other params
) -> bool:
    """Handle exception considering retry_if predicate."""
    if retry_if is not None:
        should_retry = retry_if(None, exc)
        if not should_retry or attempt == max_retries:
            raise_with_callback(...)
    
    # Delegate to appropriate handler
    handler = EXCEPTION_HANDLERS.get(type(exc))
    if handler:
        handler(exc, ...)
    
    return True  # Should retry
```

**Pros**:
- Reduces exception handling duplication
- Easier to extend with new exception types
- Maintains backward compatibility

**Cons**:
- Registry pattern may be overkill for just 2 exception types
- Still doesn't address response handling complexity

### Approach 4: Hybrid - Extract Methods + Consolidate Conditionals

**Complexity Reduction**: Reduces branches by ~8-10, statements by ~15-20

**Changes**:
1. Extract response handling: `handle_response_with_retry_if()`
2. Extract exception handling: `handle_exception_with_retry_if()`
3. Consolidate retry_if checking into shared functions
4. Simplify conditional logic by combining related checks

**Key Functions**:
- `handle_response_with_retry_if()`: Handles all response scenarios (success, retryable, non-retryable)
- `handle_exception_with_retry_if()`: Unified exception handler for both TimeoutException and RequestError
- `should_continue_retry()`: Determines if retry loop should continue

**Pros**:
- Balanced approach - significant simplification without radical restructuring
- Maintains overall function flow
- Easy to review and test incrementally
- Clear naming makes code self-documenting

**Cons**:
- Still creates additional utility functions
- May need careful parameter passing

## Recommended Approach

**Approach 1: Extract retry_if Handling to Helper Function**

This approach provides the best balance of:
- **Simplicity**: Minimal structural changes
- **Effectiveness**: Directly addresses the duplicated retry_if handling
- **Maintainability**: Creates focused, testable utility functions
- **Risk**: Low risk of introducing bugs
- **Compatibility**: 100% backward compatible

## Implementation Plan

### Phase 1: Create Helper Functions (Week 1)

1. **Create `utils/retry_if.py` module** with:
   - `should_retry_with_predicate()`: Evaluates retry_if and handles early termination
   - `handle_exception_with_retry_if()`: Consolidated exception handling with retry_if

2. **Add comprehensive tests** for new functions in `tests/unit/utils/test_retry_if.py`

### Phase 2: Refactor Synchronous Function (Week 1)

1. Update `request_with_automatic_retry()` to use new helper functions
2. Remove duplicated retry_if handling code
3. Run full test suite to ensure no regression
4. Verify linting passes (should fix PLR0912 and PLR0915)

### Phase 3: Refactor Async Function (Week 1)

1. Update `request_with_automatic_retry_async()` to use new helper functions
2. Remove duplicated retry_if handling code
3. Run full test suite to ensure no regression
4. Verify linting passes

### Phase 4: Documentation and Review (Week 2)

1. Update inline comments if needed
2. Update IMPLEMENTATION_SUMMARY.md if it exists
3. Code review
4. Merge

## Expected Outcomes

After implementing Approach 1:

### Metrics
- **Branches**: Reduced from 19 to ~11-12 (within limit of 12)
- **Statements**: Reduced from 58 to ~43-48 (within limit of 50)
- **Lines of code**: Reduced by ~15-20 per function
- **Test coverage**: Maintained at 100%

### Benefits
- ✅ Passes linting checks (no PLR0912, PLR0915 errors)
- ✅ Easier to understand and maintain
- ✅ Better separation of concerns
- ✅ More testable components
- ✅ Zero breaking changes
- ✅ Reduced code duplication

## Alternative Considerations

If Approach 1 doesn't reduce complexity enough to pass linting:

1. **Combine with Approach 4**: Extract additional methods for response handling
2. **Request per-file ignore**: Add PLR0912/PLR0915 to per-file-ignores in pyproject.toml (least preferred)
3. **Increase limits**: Adjust Ruff configuration to allow higher complexity (not recommended as it defeats the purpose)

## Security Considerations

- No security implications from this refactoring
- All exception handling and error reporting remains intact
- No changes to authentication, authorization, or data handling

## Testing Strategy

1. **Existing tests**: All existing tests must pass without modification
2. **New tests**: Add tests for new helper functions
3. **Edge cases**: Verify retry_if edge cases are handled correctly
4. **Integration tests**: Run integration tests to ensure end-to-end behavior unchanged
5. **Performance**: Verify no performance regression (should be negligible)

## Backward Compatibility

✅ **100% Backward Compatible**

- No changes to function signatures
- No changes to public API
- No changes to behavior or semantics
- All existing code using these functions will work unchanged

## Conclusion

The recommended approach (Approach 1) provides a pragmatic solution that:
- Directly addresses the linting violations
- Improves code maintainability
- Maintains backward compatibility
- Can be implemented incrementally with low risk
- Sets foundation for future improvements if needed

The implementation can be completed within 1-2 weeks with proper testing and review.
