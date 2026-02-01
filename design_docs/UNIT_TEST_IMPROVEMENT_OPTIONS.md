# Unit Test Structure Improvement Options

**Document Date:** 2026-02-01
**Current Test Structure:** See `tests/TESTS.md` for the current design

## Executive Summary

This document proposes options to improve the maintainability of the `aresilient` test suite. The current structure effectively separates unit and integration tests, and uses parametrization to reduce duplication. However, there are opportunities to further improve maintainability, reduce code duplication, and make the test suite easier to extend.

## Current State Analysis

### Strengths

1. **Clear separation of concerns:**
   - Unit tests (mocked) vs. integration tests (real HTTP)
   - Synchronous vs. asynchronous tests clearly separated
   - Feature-specific test organization

2. **Effective use of parametrization:**
   - `test_core.py` and `test_core_async.py` use parametrization to test all HTTP methods
   - Shared test helpers in `helpers.py` with `HTTP_METHODS` and `HTTP_METHODS_ASYNC`
   - Reduces duplication for common functionality

3. **Good documentation:**
   - Comprehensive `TESTS.md` documentation
   - Module-level docstrings explaining test strategy
   - Clear naming conventions

### Challenges and Pain Points

1. **Significant duplication in HTTP method-specific tests:**
   - Files like `test_post.py` and `test_put.py` are nearly identical (only differ in method name)
   - Same pattern repeated for `test_post_async.py` vs `test_put_async.py`
   - Integration test files show similar duplication
   - Each HTTP method has 2-4 test files (unit sync, unit async, integration sync, integration async)

2. **Parallel sync/async test maintenance:**
   - Every test written for sync functions needs an async equivalent
   - Test logic is duplicated between `test_*.py` and `test_*_async.py`
   - Risk of divergence when updating one but not the other
   - Total of 54 test files (60 including helpers), many are duplicates

3. **Fixture duplication:**
   - `mock_client` fixture defined in multiple test files
   - Could be centralized in `conftest.py`

4. **Large test files:**
   - `test_request.py` (1087 lines) and `test_request_async.py` (690 lines) are very large
   - `test_utils.py` (836 lines) is large
   - Difficult to navigate and maintain

5. **Limited reuse of test logic:**
   - Similar test scenarios (e.g., "with custom headers", "large request body") written separately for each HTTP method
   - Integration tests have some duplication despite common tests in `test_core.py`

## Improvement Options

### Option 1: Enhanced Parametrization (Recommended - Low Risk)

**Description:** Extend parametrization to cover more test scenarios, reducing method-specific test files.

**Implementation:**

1. **Move more tests to parametrized core files:**
   - Expand `test_core.py` to include tests currently in method-specific files
   - Example: Tests for "with data/form submission" can be parametrized with a condition on `supports_body`
   - Example: Tests for headers, large payloads can apply to all methods

2. **Reduce or eliminate HTTP method-specific test files:**
   - Keep only truly method-specific tests (e.g., GET with query params, HEAD response body handling)
   - Many method files could be eliminated entirely

3. **Consolidate integration tests similarly:**
   - Move common integration tests to `test_core.py` (already started)
   - Keep only method-specific integration tests in separate files

**Example Code:**

```python
# In test_core.py
@pytest.mark.parametrize("test_case", HTTP_METHODS)
def test_request_with_custom_headers(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test request with custom headers (works for all methods)."""
    mock_response = Mock(spec=httpx.Response, status_code=test_case.status_code)
    mock_client = Mock(spec=httpx.Client)
    setattr(mock_client, test_case.client_method, Mock(return_value=mock_response))

    headers = {"X-Custom": "value"}
    response = test_case.method_func(TEST_URL, client=mock_client, headers=headers)

    assert response.status_code == test_case.status_code
    client_method = getattr(mock_client, test_case.client_method)
    client_method.assert_called_once_with(url=TEST_URL, headers=headers)


@pytest.mark.parametrize("test_case", [tc for tc in HTTP_METHODS if tc.supports_body])
def test_request_with_body_data(
    test_case: HttpMethodTestCase,
    mock_sleep: Mock,
) -> None:
    """Test request with body data (only for methods that support bodies)."""
    # Test logic here - only runs for POST, PUT, PATCH
```

**Benefits:**
- Reduces number of test files significantly (could eliminate ~20-30 files)
- Single source of truth for common test logic
- Easier to ensure all methods are tested consistently
- New HTTP methods automatically tested with existing scenarios

**Drawbacks:**
- Requires refactoring existing tests
- May make some tests slightly less readable (need to understand parametrization)
- Risk of breaking existing tests during refactoring

**Effort:** Medium (2-3 days)
**Risk:** Low
**Impact:** High

---

### Option 2: Shared Test Base Classes (Alternative - Medium Risk)

**Description:** Create base test classes that can be inherited to test each HTTP method with common logic.

**Implementation:**

1. **Create abstract base test classes:**
   ```python
   # tests/base_tests.py
   class HttpMethodTestBase:
       """Base class for HTTP method tests."""

       @property
       @abstractmethod
       def method_func(self):
           """The function to test."""
           pass

       @property
       @abstractmethod
       def client_method(self):
           """The client method name."""
           pass

       def test_successful_request(self, mock_sleep):
           """Test successful request."""
           # Shared test logic
           response = self.method_func(TEST_URL, client=self.mock_client)
           assert response.status_code == self.expected_status
   ```

2. **Implement for each method:**
   ```python
   # tests/unit/test_get.py
   class TestGet(HttpMethodTestBase):
       method_func = get_with_automatic_retry
       client_method = "get"
       expected_status = 200
   ```

**Benefits:**
- Familiar OOP pattern
- Clear inheritance structure
- Can override specific tests for special cases

**Drawbacks:**
- pytest doesn't naturally work with test classes (less idiomatic)
- More boilerplate code
- Harder to understand test execution flow
- May conflict with pytest fixtures and markers

**Effort:** Medium (2-3 days)
**Risk:** Medium
**Impact:** Medium

---

### Option 3: Unified Sync/Async Test Framework (Advanced - High Risk)

**Description:** Create a framework to define tests once and run them for both sync and async variants automatically.

**Implementation:**

1. **Create test definition decorators:**
   ```python
   # tests/test_framework.py
   def for_sync_and_async(test_func):
       """Decorator to run test in both sync and async modes."""

       def sync_test(*args, **kwargs):
           return test_func(*args, **kwargs, is_async=False)

       async def async_test(*args, **kwargs):
           return await test_func(*args, **kwargs, is_async=True)

       return pytest.mark.parametrize("mode", ["sync", "async"])(
           lambda mode: async_test if mode == "async" else sync_test
       )
   ```

2. **Write tests once:**
   ```python
   @for_sync_and_async
   async def test_successful_request(test_case, is_async):
       if is_async:
           response = await test_case.async_method_func(TEST_URL)
       else:
           response = test_case.method_func(TEST_URL)
       assert response.status_code == test_case.status_code
   ```

**Benefits:**
- Eliminates ~50% of test files (no separate async files)
- Single source of truth for test logic
- Impossible for sync and async tests to diverge

**Drawbacks:**
- Complex framework to build and maintain
- May be confusing for new contributors
- Harder to debug when tests fail
- May not integrate well with pytest's asyncio plugin
- High risk of introducing bugs in test framework itself

**Effort:** High (5-7 days)
**Risk:** High
**Impact:** High

---

###
(Complementary - Low Risk)

**Description:** Extract common test patterns into reusable utility functions that can be called from multiple tests.

**Implementation:**

1. **Create test utilities:**
   ```python
   # tests/test_utils.py
   def assert_successful_request(method_func, url, client, expected_status=200, **kwargs):
       """Reusable assertion for successful requests."""
       response = method_func(url, client=client, **kwargs)
       assert response.status_code == expected_status
       return response


   def setup_mock_client_for_method(
       client_method: str, status_code: int = 200
   ) -> tuple[Mock, Mock]:
       """Create mock client with specified method."""
       mock_response = Mock(spec=httpx.Response, status_code=status_code)
       mock_client = Mock(spec=httpx.Client)
       setattr(mock_client, client_method, Mock(return_value=mock_response))
       return mock_client, mock_response
   ```

2. **Use in tests:**
   ```python
   def test_get_with_headers(mock_sleep):
       client, _ = setup_mock_client_for_method("get")
       assert_successful_request(
           get_with_automatic_retry, TEST_URL, client, headers={"X-Custom": "value"}
       )
   ```

**Benefits:**
- Easy to implement incrementally
- Reduces boilerplate in tests
- Improves test readability
- Can be combined with other options

**Drawbacks:**
- Doesn't eliminate file duplication
- Test logic is less explicit
- May hide important test details

**Effort:** Low (1-2 days)
**Risk:** Low
**Impact:** Low-Medium

---

### Option 5: Reorganize by Feature (Alternative Structure - High Risk)

**Description:** Reorganize tests by feature rather than by HTTP method and sync/async.

**Current Structure:**
```
tests/
  unit/
    test_get.py
    test_get_async.py
    test_post.py
    test_post_async.py
    test_retry.py
    test_retry_async.py
```

**Proposed Structure:**
```
tests/
  unit/
    http_methods/
      test_all_methods.py        # Parametrized for all methods
      test_get_specific.py       # Only GET-specific tests
      test_post_specific.py      # Only POST-specific tests
    retry/
      test_retry_logic.py        # Both sync and async
      test_retry_if.py
      test_retry_after.py
    callbacks/
      test_callback_system.py
      test_http_callbacks.py
```

**Benefits:**
- More logical grouping by functionality
- Easier to find related tests
- Clearer separation of common vs specific tests

**Drawbacks:**
- Major restructuring effort
- Risk of breaking existing test discovery
- May confuse contributors familiar with current structure
- Doesn't directly reduce duplication

**Effort:** High (4-5 days)
**Risk:** High
**Impact:** Medium

---

### Option 6: Consolidate Fixtures (Complementary - Low Risk)

**Description:** Move all shared fixtures to `conftest.py` to avoid duplication.

**Implementation:**

1. **Move common fixtures to conftest.py:**
   ```python
   # tests/conftest.py
   @pytest.fixture
   def mock_client() -> httpx.Client:
       """Create a mock httpx.Client for testing."""
       return Mock(spec=httpx.Client)


   @pytest.fixture
   def mock_async_client() -> httpx.AsyncClient:
       """Create a mock httpx.AsyncClient for testing."""
       return Mock(spec=httpx.AsyncClient, aclose=AsyncMock())


   @pytest.fixture
   def mock_response_200() -> httpx.Response:
       """Create a mock 200 response."""
       return Mock(spec=httpx.Response, status_code=200)
   ```

2. **Remove fixture definitions from individual test files**

**Benefits:**
- Single source of truth for fixtures
- Easier to update fixture behavior globally
- Reduces boilerplate in test files

**Drawbacks:**
- All fixtures in one place may become cluttered
- Less obvious what fixtures are available for a specific test file

**Effort:** Low (half day)
**Risk:** Very Low
**Impact:** Low

---

### Option 7: Split Large Test Files (Complementary - Low Risk)

**Description:** Break down large test files into smaller, focused modules.

**Implementation:**

1. **Split `test_request.py` by feature:**
   ```
   test_request/
     __init__.py
     test_basic_functionality.py
     test_retry_logic.py
     test_error_handling.py
     test_callbacks.py
     test_configuration.py
   ```

2. **Split `test_utils.py` by utility category:**
   ```
   test_utils/
     __init__.py
     test_retry_predicates.py
     test_backoff_calculation.py
     test_helper_functions.py
   ```

**Benefits:**
- Easier to navigate and understand
- Faster test file loading and editing
- Better organization of related tests
- Easier to run specific test subsets

**Drawbacks:**
- More files to manage
- Need to decide on split criteria
- May complicate test discovery slightly

**Effort:** Low (1 day)
**Risk:** Very Low
**Impact:** Low-Medium

---

## Recommendations

### Recommended Approach: Hybrid Strategy

Combine multiple low-risk, high-impact options for best results:

**Phase 1: Quick Wins (Week 1)**
1. **Consolidate Fixtures (Option 6)** - Move all shared fixtures to `conftest.py`
2. **Add Test Utilities (Option 4)** - Create helper functions for common patterns
3. **Split Large Files (Option 7)** - Break down `test_request.py` and `test_utils.py`

**Phase 2: Major Improvements (Weeks 2-3)**
4. **Enhanced Parametrization (Option 1)** - Expand parametrized tests in core files
   - Move common tests from method-specific files to `test_core.py`/`test_core_async.py`
   - Eliminate unnecessary method-specific files
   - Target: Reduce test file count by 30-40%

**Phase 3: Ongoing (As needed)**
5. **Continue refactoring** based on lessons learned
6. **Monitor** for new duplication patterns
7. **Document** testing best practices for contributors

### Why This Approach?

1. **Incremental improvement:** Low risk changes first, building confidence
2. **Immediate benefits:** Each phase delivers value
3. **Compatible:** Options work well together
4. **Proven patterns:** Uses established pytest best practices
5. **Maintainable:** Doesn't introduce complex frameworks

### Metrics for Success

Track these metrics before and after improvements:

- **Test file count:** Target reduction of 15-20 files (from 54 to ~35-40)
- **Lines of test code:** Target reduction of 20-30%
- **Test execution time:** Should remain constant or improve
- **Code coverage:** Should remain at 100% or improve
- **Time to add new HTTP method:** Should decrease significantly

---

## Detailed Implementation Plan for Recommended Approach

### Phase 1: Quick Wins

#### Step 1.1: Consolidate Fixtures (1-2 hours)
- [ ] Move `mock_client` fixture from test files to `conftest.py`
- [ ] Move `mock_async_client` fixture to `conftest.py`
- [ ] Add common response fixtures (200, 204, 404, 500, etc.)
- [ ] Update test files to remove local fixture definitions
- [ ] Run full test suite to verify

#### Step 1.2: Create Test Utilities (4-6 hours)
- [ ] Create `tests/test_helpers.py` with utility functions
- [ ] Add `setup_mock_client_for_method()` helper
- [ ] Add `assert_successful_request()` helper
- [ ] Add `assert_retry_behavior()` helper
- [ ] Document usage in docstrings
- [ ] Refactor 2-3 test files to use utilities as proof of concept

#### Step 1.3: Split Large Files (4-6 hours)
- [ ] Create `tests/unit/test_request/` directory
- [ ] Split `test_request.py` into 4-5 focused modules
- [ ] Update imports and references
- [ ] Create `tests/unit/test_utils/` directory
- [ ] Split `test_utils.py` into 3-4 focused modules
- [ ] Run full test suite to verify
- [ ] Update `TESTS.md` to reflect new structure

### Phase 2: Enhanced Parametrization

#### Step 2.1: Audit Current Tests (2-3 hours)
- [ ] Review all method-specific test files
- [ ] Identify tests that could be parametrized
- [ ] Create matrix of tests vs HTTP methods
- [ ] Prioritize by impact (tests that appear in most files)

#### Step 2.2: Expand Core Test Files (8-12 hours)
- [ ] Add 10-15 new parametrized tests to `test_core.py`
  - Custom headers test
  - Large payload test (with `supports_body` filter)
  - Multiple retry scenarios
  - Error handling scenarios
- [ ] Add corresponding tests to `test_core_async.py`
- [ ] Run tests frequently to ensure no regression

#### Step 2.3: Remove Redundant Tests (4-6 hours)
- [ ] Delete redundant tests from method-specific files
- [ ] For HTTP methods with only 1-2 specific tests, move them to core file with special handling
- [ ] Delete empty or near-empty test files
- [ ] Update imports and references

#### Step 2.4: Apply to Integration Tests (4-6 hours)
- [ ] Expand `tests/integration/test_core.py` with more scenarios
- [ ] Remove redundant integration tests from method-specific files
- [ ] Keep only truly method-specific integration tests

### Phase 3: Documentation and Validation

#### Step 3.1: Update Documentation (2-3 hours)
- [ ] Update `tests/TESTS.md` with new structure
- [ ] Document new testing utilities and patterns
- [ ] Add examples of how to add tests for new features
- [ ] Update contribution guidelines if needed

#### Step 3.2: Validate Improvements (2-3 hours)
- [ ] Measure test file count reduction
- [ ] Measure lines of code reduction
- [ ] Verify 100% code coverage maintained
- [ ] Run full test suite on multiple Python versions
- [ ] Performance benchmark (should be same or faster)

#### Step 3.3: Knowledge Transfer (1-2 hours)
- [ ] Create PR with detailed description of changes
- [ ] Add comments explaining new patterns
- [ ] Consider creating a migration guide for contributors

---

## Alternative Considerations

### If the Team Prefers More Radical Change

Consider **Option 3 (Unified Sync/Async Framework)** if:
- Team has strong Python and pytest expertise
- Willing to invest in custom test infrastructure
- Long-term maintenance is a priority
- Similar pattern would be used in other projects

This would require:
- Dedicated time to build and test the framework
- Comprehensive documentation
- Training for contributors
- Fallback plan if framework proves problematic

### If the Team Prefers Minimal Change

Focus only on **Phase 1** (Quick Wins):
- Provides immediate benefits
- Very low risk
- Can be done in parallel with other work
- Serves as proof of concept for larger changes

---

## Risk Mitigation

### For All Changes

1. **Maintain 100% test coverage** throughout refactoring
2. **Run full test suite** after each change
3. **Use feature branches** for each phase
4. **Review changes carefully** before merging
5. **Keep git history clean** for easy rollback if needed

### For Parametrization Changes

1. **Start with least critical tests** (e.g., integration tests)
2. **Verify test names** are still descriptive with parametrization
3. **Ensure failure messages** clearly indicate which parameter failed
4. **Keep some redundancy** initially, remove gradually

### For Structural Changes

1. **Update CI/CD** to work with new structure
2. **Update IDE test discovery** configurations
3. **Communicate changes** to all contributors
4. **Provide migration examples** for common patterns

---

## Conclusion

The current test structure is well-organized but has opportunities for significant improvement. The **recommended hybrid approach** balances risk, effort, and impact to deliver meaningful improvements in maintainability while preserving the strengths of the current design.

Key benefits of the recommended approach:
- **30-40% reduction in test files** (from ~54 to ~35-40 files)
- **20-30% reduction in test code** through better reuse
- **Easier maintenance** with single source of truth for common tests
- **Better extensibility** when adding new HTTP methods or features
- **Lower risk** through incremental, proven changes

The test suite will become more maintainable, more consistent, and easier for contributors to understand and extend, while maintaining 100% code coverage and test reliability.
