from __future__ import annotations

# Use httpbin.org for real HTTP testing
HTTPBIN_URL = "https://httpbin.org"


#################################################
#     Tests for delete_with_automatic_retry     #
#################################################
# Note: Common tests (successful request, non-retryable status, headers, query params)
# are now in test_core.py to avoid duplication across HTTP methods.
# This file contains DELETE-specific tests only (currently none - all tests were common).
