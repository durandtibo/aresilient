r"""Parameter validation utilities for HTTP request retry logic.

This module provides validation functions for retry parameters to ensure
they meet the required constraints before being used in HTTP request
retry logic.

.. deprecated:: 0.0.1a1
    This module re-exports validation functions from aresilient.core.validation
    for backward compatibility. Import directly from aresilient.core.validation
    instead.
"""

from __future__ import annotations

__all__ = ["validate_retry_params"]

# Re-export from core for backward compatibility
from aresilient.core.validation import validate_retry_params
