"""Exceptions hierarchy for APRO Phase 13 Recovery Loop."""


class RecoveryLoopError(Exception):
    """Base exception for recovery loop errors."""


class TerminalCaseReopenError(RecoveryLoopError):
    """Raised when attempting to reopen or transition a case in terminal state."""


class InvalidOutcomeEvidenceError(RecoveryLoopError):
    """Raised when outcome evidence is missing required fields or malformed."""


class EntityMismatchError(RecoveryLoopError):
    """Raised when case, execution, or payment entity bindings do not match."""


class UnboundedLoopError(RecoveryLoopError):
    """Raised when loop exceeds maximum safety iteration bounds."""


class IdempotentOutcomeDuplicateError(RecoveryLoopError):
    """Raised when an identical outcome has already been durably recorded."""


class CaptureRaceDetectedError(RecoveryLoopError):
    """Raised when payment is observed CAPTURED while execution was attempted."""


class StalePolicyDecisionError(RecoveryLoopError):
    """Raised when attempting to reuse a PolicyDecision from a previous cycle."""
