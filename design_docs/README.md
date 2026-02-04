# Design Documentation

This directory contains design documents and proposals for the aresilient library.

## Active Documents

- **[LIBRARY_STRUCTURE_PROPOSAL.md](LIBRARY_STRUCTURE_PROPOSAL.md)** - Library structure analysis and recommendations
  - Comprehensive review of the library's structure with 18 modules and ~1,500 lines
  - Analysis of sync/async architecture patterns
  - Recommendations for current and future structure
  - Clear thresholds for when to consider restructuring
  - **Updated:** January 2026

- **[REQUEST_FUNCTION_SIMPLIFICATION.md](REQUEST_FUNCTION_SIMPLIFICATION.md)** - Request function complexity reduction
  - Analysis of `request_with_automatic_retry` and `request_with_automatic_retry_async` complexity issues
  - Five proposed approaches for reducing branches and statements
  - Recommended approach: Extract retry_if handling to helper functions
  - Alternative class-based composition approach for future consideration
  - Implementation plan with phases and expected outcomes
  - Target: Reduce from 19 branches to ~11-12 and 58 statements to ~43-48

- **[MISSING_FUNCTIONALITIES.md](MISSING_FUNCTIONALITIES.md)** - Missing features analysis and roadmap
  - Comprehensive analysis of missing functionalities compared to similar libraries
  - Categorization by priority (High, Medium, Low)
  - Implementation recommendations
  - Status tracking of implemented features
  - **Updated:** February 2026 - Context Manager API implemented

## Recent Implementations

### Context Manager API (February 2026)

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

## Summary

The aresilient library currently maintains a **flat structure** with clear separation between synchronous and asynchronous implementations using the `*_async.py` naming convention. This structure is recommended to continue until the library reaches approximately 2,500 lines or 20 files, at which point a modular sub-package structure should be considered.

Recent analysis has identified complexity issues in the core request functions that need simplification to meet code quality standards and improve maintainability.

**Recent Addition:** The Context Manager API (`ResilientClient` and `AsyncResilientClient`) has been implemented (February 2026), adding convenient context manager support for batch requests with automatic resource cleanup.

For details:
- Library structure: [LIBRARY_STRUCTURE_PROPOSAL.md](LIBRARY_STRUCTURE_PROPOSAL.md)
- Request function simplification: [REQUEST_FUNCTION_SIMPLIFICATION.md](REQUEST_FUNCTION_SIMPLIFICATION.md)
- Feature roadmap: [MISSING_FUNCTIONALITIES.md](MISSING_FUNCTIONALITIES.md)
