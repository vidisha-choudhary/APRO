"""Custom exceptions for the APRO domain layer."""


class DomainException(Exception):  # noqa: N818
    """Base exception for all APRO domain errors."""


class InvalidStateTransitionError(DomainException):
    """Raised when an invalid state transition is attempted."""


class InvariantViolationError(DomainException):
    """Raised when a core domain invariant is violated."""


class CapturedPaymentRecoveryError(InvariantViolationError):
    """Raised when attempting recovery execution on a CAPTURED payment."""


class ImmutableRecordError(DomainException):
    """Raised when attempting to mutate an immutable historical domain record."""


class DomainValidationError(DomainException):
    """Raised when domain field validation fails."""
