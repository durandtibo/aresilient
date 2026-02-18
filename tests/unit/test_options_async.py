r"""Unit tests for options_async function.

This file contains tests that are specific to the async OPTIONS HTTP method.
Common tests across all async HTTP methods are in test_core_async.py.

Note: OPTIONS requests are used to query supported methods and headers.
The core async tests cover all the retry logic and error handling. Currently,
there are no OPTIONS-specific tests needed beyond what's in test_core_async.py.
"""

from __future__ import annotations

# No async OPTIONS-specific tests needed at this time.
# All core functionality is tested in test_core_async.py with parametrized tests.
