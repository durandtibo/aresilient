r"""Unit tests for head_with_automatic_retry_async function.

This file contains tests that are specific to the async HEAD HTTP method.
Common tests across all async HTTP methods are in test_core_async.py.

Note: HEAD requests are typically identical to GET requests except they
don't return a response body. The core async tests cover all the retry logic
and error handling. Currently, there are no HEAD-specific tests needed
beyond what's in test_core_async.py.
"""

from __future__ import annotations

# No async HEAD-specific tests needed at this time.
# All core functionality is tested in test_core_async.py with parametrized tests.
