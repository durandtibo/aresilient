from __future__ import annotations

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#################################################
#     Tests for options_with_automatic_retry     #
#################################################
# Note: Common tests (successful request, headers)
# are now in test_core.py to avoid duplication across HTTP methods.
# This file contains OPTIONS-specific tests only (currently none - all tests were common).
