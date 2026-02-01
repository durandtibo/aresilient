# Test Structure Documentation

This document explains the organization and structure of tests in the `aresilient` library.

## Directory Structure

The test suite is organized into the following structure:

```
tests/
├── __init__.py                 # Package marker
├── conftest.py                 # Shared pytest fixtures
├── helpers.py                  # Test helpers and utilities
├── package_checks.py           # Package installation validation
├── unit/                       # Unit tests (mocked dependencies)
│   ├── __init__.py
│   ├── test_*.py              # Synchronous unit tests
│   └── test_*_async.py        # Asynchronous unit tests
└── integration/                # Integration tests (real HTTP calls)
    ├── __init__.py
    ├── test_*.py              # Synchronous integration tests
    └── test_*_async.py        # Asynchronous integration tests
```

## Test Types

### Unit Tests (`tests/unit/`)

Unit tests validate individual components in isolation using mocked dependencies. These tests:
- Use `unittest.mock` to mock HTTP clients and responses
- Do not make real network calls
- Run quickly (milliseconds per test)
- Test edge cases, error conditions, and business logic
- Use fixtures like `mock_sleep` and `mock_asleep` to avoid actual delays

**Examples:**
- `test_retry_if.py` - Tests for custom retry predicates (synchronous)
- `test_callbacks.py` - Tests for callback/event system
- `test_backoff.py` - Tests for exponential backoff logic
- `test_core.py` - Core functionality tests across all HTTP methods

### Integration Tests (`tests/integration/`)

Integration tests validate the library against real HTTP endpoints. These tests:
- Make actual HTTP requests to `https://httpbin.org`
- Verify end-to-end functionality
- Test real retry behavior, timeouts, and network errors
- Run slower than unit tests

**Examples:**
- `test_get.py` - Integration tests for GET requests
- `test_core.py` - Core integration tests across all HTTP methods
- `test_request.py` - Generic request function integration tests

### Package Checks (`package_checks.py`)

Standalone validation script that:
- Verifies the package is installed correctly
- Tests basic functionality with real HTTP calls
- Used for smoke testing after installation
- Can be run independently: `python tests/package_checks.py`

## Test Naming Conventions

### File Naming

1. **Synchronous Tests:** `test_<feature>.py`
   - Example: `test_retry_if.py` (sync tests for custom retry predicates)
   - Example: `test_get.py` (sync tests for GET requests)

2. **Asynchronous Tests:** `test_<feature>_async.py`
   - Example: `test_retry_if_async.py` (async tests for custom retry predicates)
   - Example: `test_get_async.py` (async tests for GET requests)
   - All async test files end with `_async.py` suffix

3. **Feature-Specific Tests:**
   - HTTP Methods: `test_get.py`, `test_post.py`, `test_put.py`, `test_delete.py`, `test_patch.py`, `test_head.py`, `test_options.py`
   - Core Features: `test_core.py`, `test_retry.py`, `test_backoff.py`, `test_callbacks.py`
   - Specific Features: `test_retry_if.py`, `test_retry_after.py`, `test_recovery.py`
   - Utilities: `test_utils.py`, `test_config.py`, `test_exceptions.py`, `test_dataclasses.py`

### Test Function Naming

Test functions follow the pattern: `test_<scenario>_<condition>`

Examples:
- `test_retry_if_returns_false_for_successful_response()`
- `test_successful_request_with_custom_client()`
- `test_max_retries_exhausted_raises_exception()`

## Test Categories

### HTTP Method Tests

Tests for each HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS):

- **Synchronous Tests:** `test_<method>.py` (unit), `test_<method>.py` (integration)
- **Asynchronous Tests:** `test_<method>_async.py` (unit), `test_<method>_async.py` (integration)

Each HTTP method has dedicated tests for method-specific behavior while common functionality is tested in `test_core.py` and `test_core_async.py` using parametrization.

### Core Functionality Tests

- `test_core.py` / `test_core_async.py` - Parametrized tests for functionality common to all HTTP methods
- Uses pytest parametrization to test all methods with the same test logic
- Reduces code duplication while ensuring consistent behavior

### Retry Logic Tests

- `test_retry.py` / `test_retry_async.py` - General retry mechanism tests
- `test_retry_if.py` / `test_retry_if_async.py` - Custom retry predicate tests
- `test_retry_after.py` / `test_retry_after_async.py` - Retry-After header support tests

### Backoff Strategy Tests

- `test_backoff.py` / `test_backoff_async.py` - Exponential backoff and jitter tests
- Validates wait time calculations and randomization

### Callback/Observability Tests

- `test_callbacks.py` / `test_callbacks_async.py` - Tests for callback system
- `test_http_callbacks.py` / `test_http_async_callbacks.py` - HTTP-specific callback tests
- Tests `on_request`, `on_retry`, `on_success`, `on_failure` callbacks

### Error Handling Tests

- `test_exceptions.py` - Exception class tests
- `test_recovery.py` / `test_recovery_async.py` - Error recovery and specific exception handling tests

### Configuration and Utilities

- `test_config.py` - Configuration validation tests
- `test_dataclasses.py` - Tests for dataclasses used in callbacks
- `test_utils.py` - Utility function tests
- `test_init.py` - Package exports validation

### Generic Request Tests

- `test_request.py` / `test_request_async.py` - Tests for low-level generic request functions
- Used for custom HTTP methods or advanced use cases

## Test Helpers and Fixtures

### Fixtures (`conftest.py`)

Shared pytest fixtures available to all tests:

1. **`mock_sleep`** - Patches `time.sleep()` to make synchronous tests run faster
   - Automatically mocks sleep calls to return immediately
   - Used in unit tests to avoid waiting for backoff delays

2. **`mock_asleep`** - Patches `asyncio.sleep()` to make async tests run faster
   - Automatically mocks async sleep calls to return immediately
   - Used in async unit tests to avoid waiting for backoff delays

### Test Helpers (`helpers.py`)

Provides reusable test utilities and parametrization data:

1. **`HTTPBIN_URL`** - URL for integration tests: `"https://httpbin.org"`

2. **`HttpMethodTestCase`** - Dataclass for parametrizing synchronous HTTP method tests
   - Fields: `method_name`, `method_func`, `client_method`, `status_code`, `test_url`, `supports_body`
   - Used to test all HTTP methods with the same test logic

3. **`AsyncHttpMethodTestCase`** - Dataclass for parametrizing asynchronous HTTP method tests
   - Similar to `HttpMethodTestCase` but for async functions

4. **`HTTP_METHODS`** - List of pytest parameters for all synchronous HTTP methods
   - Includes GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
   - Each with appropriate test URLs and expected status codes

5. **`HTTP_METHODS_ASYNC`** - List of pytest parameters for all async HTTP methods
   - Async versions of all HTTP methods
   - Used with `@pytest.mark.asyncio` and `@pytest.mark.parametrize`

**Example Usage:**
```python
from tests.helpers import HTTP_METHODS, HttpMethodTestCase

@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_successful_request_with_custom_client(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test successful request with custom client."""
    # Test logic that works for all HTTP methods
    response = test_case.method_func(TEST_URL, client=mock_client)
    assert response.status_code == test_case.status_code
```

## Key Patterns and Best Practices

### Parametrized Testing

The test suite heavily uses pytest parametrization to:
- Test all HTTP methods with the same test logic
- Reduce code duplication
- Ensure consistent behavior across methods
- Make it easy to add new HTTP methods

Example from `test_core.py`:
```python
@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_successful_request_with_custom_client(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test successful request with custom client."""
    # Single test definition that runs for all HTTP methods
```

### Async Test Markers

All async tests use the `@pytest.mark.asyncio` decorator:
```python
@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", HTTP_METHODS_ASYNC)
async def test_async_function(test_case: AsyncHttpMethodTestCase) -> None:
    """Async test example."""
    response = await test_case.method_func(TEST_URL)
```

### Docstring Standards

Test modules include comprehensive module-level docstrings explaining:
- Purpose of the test module
- Testing strategy (parametrization, etc.)
- Related test files
- Special considerations

Example from `test_core.py`:
```python
r"""Parametrized unit tests for core functionality in all HTTP method
wrappers.

This test module uses pytest parametrization to test core functionality
across all HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
in a consistent and maintainable way. Tests that are common to all
methods are defined here to reduce duplication.

Method-specific tests remain in their respective test files:
- test_get.py: GET-specific tests (e.g., params support)
- test_post.py: POST-specific tests (e.g., data/form submission)
...
```

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Unit Tests Only
```bash
pytest tests/unit/
```

### Run Integration Tests Only
```bash
pytest tests/integration/
```

### Run Specific Feature Tests
```bash
pytest tests/unit/test_retry_if.py
pytest tests/unit/test_retry_if_async.py
```

### Run Synchronous Tests Only
```bash
pytest tests/ -k "not async"
```

### Run Asynchronous Tests Only
```bash
pytest tests/ -k "async"
```

### Run with Coverage
```bash
pytest tests/ --cov=aresilient --cov-report=html
```

## Test Statistics

To get current test statistics, run:
```bash
# Get total test count
pytest tests/ --collect-only

# Count test files by category
find tests/unit -type f -name "*.py" ! -name "__init__.py" | wc -l      # Unit test files
find tests/integration -type f -name "*.py" ! -name "__init__.py" | wc -l  # Integration test files
find tests -type f -name "*_async.py" | wc -l                            # Async test files
```

## Adding New Tests

When adding new features to the library:

1. **Create unit tests first** in `tests/unit/`
   - Mock external dependencies
   - Test edge cases and error conditions
   - Create both sync (`test_<feature>.py`) and async (`test_<feature>_async.py`) versions

2. **Add integration tests** in `tests/integration/`
   - Test against real HTTP endpoints when applicable
   - Verify end-to-end functionality

3. **Update parametrization** if adding new HTTP methods
   - Add to `HTTP_METHODS` and `HTTP_METHODS_ASYNC` in `helpers.py`
   - Existing parametrized tests will automatically cover the new method

4. **Follow naming conventions**
   - Use `test_<feature>.py` for sync tests
   - Use `test_<feature>_async.py` for async tests
   - Use descriptive test function names

5. **Add fixtures if needed**
   - Shared fixtures go in `conftest.py`
   - Feature-specific helpers go in the test file or `helpers.py`

## Related Documentation

- See `tests/unit/test_core.py` for examples of parametrized testing
- See `tests/helpers.py` for test utilities and data structures
- See `conftest.py` for shared fixtures
- See individual test files for feature-specific testing patterns
