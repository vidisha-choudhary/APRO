"""Exceptions for the APRO Execution Framework."""


class ExecutionError(Exception):
    """Base exception for all execution framework errors."""


class ExecutionAuthorizationError(ExecutionError):
    """Raised when an execution request lacks valid policy authorization."""


class ExecutionValidationError(ExecutionError):
    """Raised when execution parameters or entity bindings fail validation."""


class ExecutionStateError(ExecutionError):
    """Raised when payment or recovery case state prohibits execution."""


class ExecutorNotFoundError(ExecutionError):
    """Raised when no executor is registered for an action and mode."""


class IdempotencyConflictError(ExecutionError):
    """Raised when an idempotency key matches an incompatible existing execution."""


__all__ = [
    "ExecutionAuthorizationError",
    "ExecutionError",
    "ExecutionStateError",
    "ExecutionValidationError",
    "ExecutorNotFoundError",
    "IdempotencyConflictError",
]
