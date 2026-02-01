# Design Documentation

This directory contains design documents and proposals for the aresilient library.

## Active Documents

- **[LIBRARY_STRUCTURE_PROPOSAL.md](LIBRARY_STRUCTURE_PROPOSAL.md)** - Library structure analysis and recommendations
  - Comprehensive review of the library's structure with 16 modules and ~1,350 lines
  - Analysis of sync/async architecture patterns
  - Recommendations for current and future structure
  - Clear thresholds for when to consider restructuring

- **[REQUEST_FUNCTION_SIMPLIFICATION.md](REQUEST_FUNCTION_SIMPLIFICATION.md)** - Request function complexity reduction
  - Analysis of `request_with_automatic_retry` and `request_with_automatic_retry_async` complexity issues
  - Five proposed approaches for reducing branches and statements
  - Recommended approach: Extract retry_if handling to helper functions
  - Alternative class-based composition approach for future consideration
  - Implementation plan with phases and expected outcomes
  - Target: Reduce from 19 branches to ~11-12 and 58 statements to ~43-48

## Summary

The aresilient library currently maintains a **flat structure** with clear separation between synchronous and asynchronous implementations using the `*_async.py` naming convention. This structure is recommended to continue until the library reaches approximately 2,500 lines or 20 files, at which point a modular sub-package structure should be considered.

Recent analysis has identified complexity issues in the core request functions that need simplification to meet code quality standards and improve maintainability.

For details:
- Library structure: [LIBRARY_STRUCTURE_PROPOSAL.md](LIBRARY_STRUCTURE_PROPOSAL.md)
- Request function simplification: [REQUEST_FUNCTION_SIMPLIFICATION.md](REQUEST_FUNCTION_SIMPLIFICATION.md)
