r"""Unit tests for head function.

This file contains tests that are specific to the HEAD HTTP method.
Common tests across all HTTP methods are in test_core.py.

Note: HEAD requests are typically identical to GET requests except they
don't return a response body. The core tests cover all the retry logic
and error handling. Currently, there are no HEAD-specific tests needed
beyond what's in test_core.py.
"""

from __future__ import annotations

# No HEAD-specific tests needed at this time.
# All core functionality is tested in test_core.py with parametrized tests.
