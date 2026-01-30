# Design Documentation

This directory contains design documents and proposals for the aresnet library.

## Active Documents

- **[LIBRARY_STRUCTURE_PROPOSAL_2026.md](LIBRARY_STRUCTURE_PROPOSAL_2026.md)** - Current library structure analysis and recommendations (January 2026)
  - Comprehensive review of the library's structure with 16 modules and ~1,350 lines
  - Analysis of sync/async architecture patterns
  - Recommendations for current and future structure
  - Clear thresholds for when to consider restructuring

## Historical Documents

- **[LIBRARY_STRUCTURE_PROPOSAL.md](LIBRARY_STRUCTURE_PROPOSAL.md)** - Original proposal from 2025
  - Analyzed the library at ~900 lines and 12 modules
  - Recommended flat structure (which was adopted)
  - Superseded by the 2026 update but kept for historical reference

## Summary

The aresnet library currently maintains a **flat structure** with clear separation between synchronous and asynchronous implementations using the `*_async.py` naming convention. This structure is recommended to continue until the library reaches approximately 2,500 lines or 20 files, at which point a modular sub-package structure should be considered.

For the latest recommendations, see [LIBRARY_STRUCTURE_PROPOSAL_2026.md](LIBRARY_STRUCTURE_PROPOSAL_2026.md).
