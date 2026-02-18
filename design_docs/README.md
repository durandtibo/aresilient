# Design Documentation

This directory contains design documents and proposals for the aresilient library.

## Active Documents

- **[HTTPX_COMPATIBLE_CLIENT_API.md](HTTPX_COMPATIBLE_CLIENT_API.md)** - httpx client wrapper design
  proposal
    - Proposes modifying `ResilientClient` and `AsyncResilientClient` to accept existing httpx
      clients
    - Enables wrapping pre-configured httpx.Client instances to add resilience features
    - Preserves all httpx configuration (auth, headers, cookies, proxy, HTTP/2, etc.)
    - Maintains backward compatibility (auto-creates client if not provided)
    - User controls lifecycle of wrapped clients
    - Minimal API change (single optional `client` parameter)
    - **Status:** 📋 Proposal (Updated)
    - **Created:** February 2026

- **[SYNC_ASYNC_ARCHITECTURE_REVIEW.md](SYNC_ASYNC_ARCHITECTURE_REVIEW.md)** - Sync/async
  architecture review and improvement proposal
    - Comprehensive analysis of code duplication between sync and async implementations (~4,000
      lines, 61% of codebase)
    - Identifies structural issues: maintenance burden, risk of divergence, testing redundancy
    - Proposes three architectural alternatives with detailed trade-off analysis
    - **Recommended approach:** Extract shared logic (Option A) - 50% code reduction for moderate
      effort
    - Migration strategy with 5-phase implementation roadmap
    - Backward compatibility guarantees and success metrics
    - **Status:** 🔄 Under Review
    - **Created:** February 2026

- **[LIBRARY_STRUCTURE_PROPOSAL.md](LIBRARY_STRUCTURE_PROPOSAL.md)** - Library structure evolution
  and analysis
    - Comprehensive review of the library's modular structure with 40 modules and ~6,600 lines
    - Documentation of transition from flat to modular architecture
    - Analysis of subdirectory organization (backoff/, retry/, utils/)
    - Clear thresholds for future structural changes
    - **Updated:** February 2026

- **[REQUEST_FUNCTION_SIMPLIFICATION.md](REQUEST_FUNCTION_SIMPLIFICATION.md)** - Request function
  complexity reduction
    - Analysis of `request_with_automatic_retry` and `request_with_automatic_retry_async` complexity
      issues
    - Five proposed approaches for reducing branches and statements
    - Recommended approach: Extract retry_if handling to helper functions
    - Alternative class-based composition approach for future consideration
    - Implementation plan with phases and expected outcomes
    - Target: Reduce from 19 branches to ~11-12 and 58 statements to ~43-48
    - **Status:** Partially addressed through retry/ module refactoring

- **[MISSING_FUNCTIONALITIES.md](MISSING_FUNCTIONALITIES.md)** - Missing features analysis and
  roadmap
    - Comprehensive analysis of missing functionalities compared to similar libraries
    - Categorization by priority (High, Medium, Low)
    - Implementation recommendations
    - Status tracking of implemented features
    - **Updated:** February 2026 - Context Manager API, Circuit Breaker, Custom Retry Predicates
      implemented

- **[UNIT_TEST_IMPROVEMENT_OPTIONS.md](UNIT_TEST_IMPROVEMENT_OPTIONS.md)** - Test suite enhancement
  strategies
    - Analysis of current test suite structure and coverage
    - Evaluation of improvement options (parametrization, utilities, fixtures)
    - Recommendations for test organization and maintenance
    - **Status:** Test utilities and fixtures already implemented
    - **Updated:** February 2026

## Recent Implementations (2025-2026)

### Modular Structure Refactoring (Mid-2025 to Early 2026)

The library successfully transitioned from a flat structure (~1,350 lines, 18 files) to a modular
organization (~7,032 lines, 43 files):

- **backoff/** - Backoff strategy implementations (Exponential, Linear, Fibonacci, Constant)
- **core/** - Shared configuration, HTTP method logic, retry decision logic, and validation
- **retry/** - Comprehensive retry execution framework with managers, executors, and decision logic
- **utils/** - Utility functions for exceptions, response handling, retry-after parsing, and retry
  predicates

Benefits:

- Clear feature separation and organization
- Improved scalability for future growth
- Maintained backward compatibility through comprehensive re-exports
- Better code navigation and maintenance

### Context Manager API (Early 2026)

The Context Manager API has been implemented, providing:

- **ResilientClient** - Synchronous context manager for batch requests
- **AsyncResilientClient** - Asynchronous context manager for batch requests
- Automatic resource cleanup with `__enter__`/`__exit__` and `__aenter__`/`__aexit__`
- Shared configuration across multiple requests
- Per-request override capability

Example:

```python
from aresilient import ResilientClient

with ResilientClient(max_retries=5, timeout=30) as client:
    response1 = client.get("https://api.example.com/data1")
    response2 = client.post("https://api.example.com/data2", json={"key": "value"})
```

### Circuit Breaker Pattern (2025-2026)

Full circuit breaker implementation with three states (CLOSED, OPEN, HALF_OPEN):

- Prevents cascading failures
- Configurable failure thresholds and recovery timeouts
- Integration with all HTTP methods
- 467 lines of implementation in `circuit_breaker.py`

### Custom Retry Predicates (2025-2026)

Implemented `retry_if` functionality allowing custom retry logic:

- User-defined functions to determine retry based on response/exception
- Separate handling module in `utils/retry_if_handler.py`
- Full integration with retry execution framework

## Summary

The aresilient library has evolved significantly from its initial flat structure to a well-organized
modular architecture. The library now maintains a **modular structure** with clear separation of
concerns using subdirectories for backoff, core, retry, and utility functionality. This structure is
optimal for the current size (~7,032 lines, 43 files) and provides excellent scalability for future
growth.

**Key Achievements:**

- ✅ Modular structure with backoff/, core/, retry/, utils/ subdirectories
- ✅ Context Manager API for batch requests
- ✅ Circuit Breaker pattern for preventing cascading failures
- ✅ Custom retry predicates for flexible retry logic
- ✅ Comprehensive backoff strategies (Exponential, Linear, Fibonacci, Constant)
- ✅ Full async support across all features
- ✅ Backward compatibility maintained through re-exports

**Current Focus:**

- Maintaining comprehensive documentation
- Ensuring complete test coverage
- Code quality and consistency improvements
- Keeping design documents up-to-date
- **NEW:** Addressing sync/async code duplication (~4,000 lines, 61% of codebase)

For details:

- **Sync/async architecture review:
  ** [SYNC_ASYNC_ARCHITECTURE_REVIEW.md](SYNC_ASYNC_ARCHITECTURE_REVIEW.md) 🆕
- Library structure evolution: [LIBRARY_STRUCTURE_PROPOSAL.md](LIBRARY_STRUCTURE_PROPOSAL.md)
- Request function
  simplification: [REQUEST_FUNCTION_SIMPLIFICATION.md](REQUEST_FUNCTION_SIMPLIFICATION.md)
- Feature roadmap: [MISSING_FUNCTIONALITIES.md](MISSING_FUNCTIONALITIES.md)
- Test suite improvements: [UNIT_TEST_IMPROVEMENT_OPTIONS.md](UNIT_TEST_IMPROVEMENT_OPTIONS.md)
