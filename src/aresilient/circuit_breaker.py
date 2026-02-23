r"""Circuit Breaker Pattern implementation for preventing cascading
failures.

This module provides a circuit breaker pattern implementation that can be used
with HTTP requests to prevent overwhelming failing services. The circuit breaker
has three states:

- CLOSED: Normal operation, requests go through
- OPEN: After N consecutive failures, requests fail fast without being attempted
- HALF_OPEN: After recovery timeout, try one request to check if service recovered

Example:
    ```pycon
    >>> from aresilient import get
    >>> from aresilient.circuit_breaker import CircuitBreaker
    >>> from aresilient.core import ClientConfig
    >>> circuit_breaker = CircuitBreaker(
    ...     failure_threshold=5,
    ...     recovery_timeout=60.0,
    ... )
    >>> response = get(
    ...     "https://api.example.com/data",
    ...     config=ClientConfig(circuit_breaker=circuit_breaker),
    ... )  # doctest: +SKIP

    ```
"""

from __future__ import annotations

__all__ = ["CircuitBreaker", "CircuitBreakerError", "CircuitState"]

import logging
import threading
import time
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger: logging.Logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states.

    Attributes:
        CLOSED: Normal operation, requests are allowed.
        OPEN: Circuit is open, requests fail fast without being attempted.
        HALF_OPEN: Testing if service recovered, allows one test request.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(RuntimeError):
    """Exception raised when circuit breaker is open.

    This exception is raised when attempting to make a request while the
    circuit breaker is in the OPEN state, preventing the request from being
    attempted to protect the failing service.

    Args:
        message: A descriptive error message.

    Example:
        ```pycon
        >>> from aresilient.circuit_breaker import CircuitBreakerError
        >>> raise CircuitBreakerError("Circuit breaker is open")
        Traceback (most recent call last):
            ...
        aresilient.circuit_breaker.CircuitBreakerError: Circuit breaker is open

        ```
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class CircuitBreaker:
    r"""Circuit breaker for preventing cascading failures.

    The circuit breaker pattern stops making requests after consecutive failures
    to prevent overwhelming a failing service. It has three states:

    - CLOSED: Normal operation, requests go through
    - OPEN: After N consecutive failures, stop making requests (fail fast)
    - HALF_OPEN: After timeout, try one request to check recovery

    Thread-safe implementation using locks.

    Args:
        failure_threshold: Number of consecutive failures before opening
            the circuit. Must be > 0. Default is 5.
        recovery_timeout: Time in seconds to wait in OPEN state before
            transitioning to HALF_OPEN to test recovery. Must be > 0.
            Default is 60.0 seconds.
        expected_exception: Optional exception type or tuple of exception types
            that should count as failures. If None, any exception counts as
            a failure. Default is None.
        on_state_change: Optional callback function called when circuit state
            changes. Receives (old_state: CircuitState, new_state: CircuitState).

    Attributes:
        state: Current circuit state (CLOSED, OPEN, or HALF_OPEN).
        failure_count: Current count of consecutive failures.
        last_failure_time: Timestamp of the last failure (None if no failures).

    Raises:
        ValueError: If failure_threshold or recovery_timeout are invalid.

    Example:
        Basic usage with default settings:

        ```pycon
        >>> from aresilient.circuit_breaker import CircuitBreaker
        >>> cb = CircuitBreaker()
        >>> cb.state
        <CircuitState.CLOSED: 'closed'>
        >>> # Simulate failures
        >>> for _ in range(5):
        ...     cb.record_failure(Exception("error"))
        ...
        >>> cb.state
        <CircuitState.OPEN: 'open'>

        ```

        Custom configuration:

        ```pycon
        >>> from aresilient import HttpRequestError
        >>> from aresilient.circuit_breaker import CircuitBreaker
        >>> def on_change(old_state, new_state):
        ...     print(f"Circuit {old_state.value} -> {new_state.value}")
        ...
        >>> cb = CircuitBreaker(
        ...     failure_threshold=3,
        ...     recovery_timeout=30.0,
        ...     expected_exception=HttpRequestError,
        ...     on_state_change=on_change,
        ... )

        ```

        Usage with HTTP requests:

        ```pycon
        >>> from aresilient import get
        >>> from aresilient.circuit_breaker import CircuitBreaker
        >>> from aresilient.core import ClientConfig
        >>> circuit_breaker = CircuitBreaker(
        ...     failure_threshold=5,
        ...     recovery_timeout=60.0,
        ... )
        >>> response = get(
        ...     "https://api.example.com/data",
        ...     config=ClientConfig(circuit_breaker=circuit_breaker),
        ... )  # doctest: +SKIP

        ```
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] | tuple[type[Exception], ...] | None = None,
        on_state_change: Callable[[CircuitState, CircuitState], None] | None = None,
    ) -> None:
        if failure_threshold <= 0:
            msg = f"failure_threshold must be > 0, got {failure_threshold}"
            raise ValueError(msg)
        if recovery_timeout <= 0:
            msg = f"recovery_timeout must be > 0, got {recovery_timeout}"
            raise ValueError(msg)

        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._expected_exception = expected_exception
        self._on_state_change = on_state_change

        # State tracking (protected by lock)
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Get the current circuit state.

        Thread-safe property that returns the current state.

        Returns:
            The current circuit state (CLOSED, OPEN, or HALF_OPEN).
        """
        with self._lock:
            return self._state

    @property
    def failure_count(self) -> int:
        """Get the current failure count.

        Thread-safe property that returns the number of consecutive failures.

        Returns:
            The current consecutive failure count.
        """
        with self._lock:
            return self._failure_count

    @property
    def last_failure_time(self) -> float | None:
        """Get the timestamp of the last failure.

        Thread-safe property that returns when the last failure occurred.

        Returns:
            The timestamp of the last failure, or None if no failures have occurred.
        """
        with self._lock:
            return self._last_failure_time

    def _change_state(self, new_state: CircuitState) -> None:
        """Change the circuit state and invoke callback.

        Internal method to transition between states. Must be called with lock held.

        Args:
            new_state: The new state to transition to.
        """
        old_state = self._state
        if old_state != new_state:
            self._state = new_state
            logger.debug(f"Circuit breaker state changed: {old_state.value} -> {new_state.value}")

            # Call state change callback if provided
            if self._on_state_change is not None:
                try:
                    self._on_state_change(old_state, new_state)
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Error in circuit breaker state change callback: {e}")

    def _handle_open_state(self) -> None:
        """Handle OPEN state: transition to HALF_OPEN or raise.

        Checks whether the recovery timeout has elapsed. If it has, transitions
        the circuit to HALF_OPEN to allow a test request. Otherwise raises
        CircuitBreakerError to fail fast.

        Must be called with ``self._lock`` held.

        Raises:
            CircuitBreakerError: If the recovery timeout has not yet elapsed.
        """
        if self._last_failure_time is not None:
            time_since_failure = time.time() - self._last_failure_time
            if time_since_failure >= self._recovery_timeout:
                # Transition to HALF_OPEN to test recovery
                self._change_state(CircuitState.HALF_OPEN)
            else:
                # Still in OPEN state, fail fast
                msg = (
                    f"Circuit breaker is OPEN (failed {self._failure_count} times). "
                    f"Retry after {self._recovery_timeout - time_since_failure:.1f}s"
                )
                raise CircuitBreakerError(msg)
        else:
            # This shouldn't happen, but handle gracefully
            msg = "Circuit breaker is OPEN"
            raise CircuitBreakerError(msg)

    def check(self) -> None:
        """Check if the circuit allows requests to proceed.

        This method checks the circuit breaker state and raises an exception if
        the circuit is OPEN. If the recovery timeout has elapsed, it transitions
        to HALF_OPEN state to allow a test request.

        Raises:
            CircuitBreakerError: If the circuit is OPEN and recovery timeout has not elapsed.

        Example:
            ```pycon
            >>> from aresilient.circuit_breaker import CircuitBreaker
            >>> cb = CircuitBreaker(failure_threshold=2)
            >>> cb.check()  # Passes when circuit is CLOSED
            >>> cb.record_failure(Exception("error"))
            >>> cb.record_failure(Exception("error"))
            >>> cb.check()  # Raises CircuitBreakerError when circuit is OPEN
            Traceback (most recent call last):
                ...
            aresilient.circuit_breaker.CircuitBreakerError: Circuit breaker is OPEN...

            ```
        """
        with self._lock:
            current_state = self._state

            if current_state == CircuitState.OPEN:
                self._handle_open_state()

    def call(self, func: Callable[[], object]) -> object:
        """Execute a function through the circuit breaker.

        This is the primary method to use when protecting calls with the
        circuit breaker. It checks the circuit state, executes the function
        if allowed, and records success or failure.

        Args:
            func: A callable function to execute through the circuit breaker.
                The function should take no arguments.

        Returns:
            The return value from the executed function.

        Raises:
            CircuitBreakerError: If the circuit is OPEN and not ready for retry.
            Any exception raised by the function will be propagated after
                recording the failure.

        Example:
            ```pycon
            >>> from aresilient.circuit_breaker import CircuitBreaker
            >>> cb = CircuitBreaker(failure_threshold=3)
            >>> def my_request():
            ...     return "success"
            ...
            >>> result = cb.call(my_request)
            >>> result
            'success'

            ```
        """
        # Check if we can make the request
        with self._lock:
            if self._state == CircuitState.OPEN:
                self._handle_open_state()

        # Execute the function
        try:
            result = func()
        except Exception as e:
            # Failure - record it
            self.record_failure(e)
            raise
        else:
            # Success - record it
            self.record_success()
            return result

    def record_success(self) -> None:
        """Record a successful request.

        Resets the failure count and closes the circuit if it was HALF_OPEN.
        Thread-safe.

        Example:
            ```pycon
            >>> from aresilient.circuit_breaker import CircuitBreaker
            >>> cb = CircuitBreaker()
            >>> cb.record_success()
            >>> cb.failure_count
            0
            >>> cb.state
            <CircuitState.CLOSED: 'closed'>

            ```
        """
        with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                # Recovery successful, close the circuit
                self._change_state(CircuitState.CLOSED)
                logger.debug("Circuit breaker recovery successful, circuit CLOSED")

    def record_failure(self, exception: Exception) -> None:
        """Record a failed request.

        Increments the failure count and opens the circuit if threshold is reached.
        Thread-safe.

        Args:
            exception: The exception that caused the failure. If expected_exception
                was configured, only matching exceptions will count as failures.

        Example:
            ```pycon
            >>> from aresilient.circuit_breaker import CircuitBreaker
            >>> cb = CircuitBreaker(failure_threshold=2)
            >>> cb.record_failure(Exception("error"))
            >>> cb.failure_count
            1
            >>> cb.state
            <CircuitState.CLOSED: 'closed'>
            >>> cb.record_failure(Exception("error"))
            >>> cb.state
            <CircuitState.OPEN: 'open'>

            ```
        """
        # Check if this exception type should count as a failure
        if self._expected_exception is not None and not isinstance(
            exception, self._expected_exception
        ):
            # This exception type doesn't count, ignore it
            logger.debug(
                f"Circuit breaker ignoring exception type {type(exception).__name__} "
                f"(expected {self._expected_exception})"
            )
            return

        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            logger.debug(
                f"Circuit breaker recorded failure "
                f"({self._failure_count}/{self._failure_threshold})"
            )

            # Check if we should open the circuit
            if self._failure_count >= self._failure_threshold and self._state != CircuitState.OPEN:
                self._change_state(CircuitState.OPEN)
                logger.warning(
                    f"Circuit breaker OPENED after {self._failure_count} consecutive failures"
                )

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state.

        Resets failure count and closes the circuit. Use with caution in
        production - typically you want the circuit to recover naturally.
        Thread-safe.

        Example:
            ```pycon
            >>> from aresilient.circuit_breaker import CircuitBreaker
            >>> cb = CircuitBreaker(failure_threshold=1)
            >>> cb.record_failure(Exception("error"))
            >>> cb.state
            <CircuitState.OPEN: 'open'>
            >>> cb.reset()
            >>> cb.state
            <CircuitState.CLOSED: 'closed'>
            >>> cb.failure_count
            0

            ```
        """
        with self._lock:
            old_state = self._state
            self._failure_count = 0
            self._last_failure_time = None
            if old_state != CircuitState.CLOSED:
                self._change_state(CircuitState.CLOSED)
                logger.info("Circuit breaker manually reset to CLOSED state")
