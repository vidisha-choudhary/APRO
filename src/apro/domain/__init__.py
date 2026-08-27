"""APRO domain layer package."""

from apro.domain.enums import (
    AuditActor,
    ExecutionMode,
    ExecutionStatus,
    FailureCategory,
    OutcomeType,
    PaymentStatus,
    PolicyDecisionResult,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.exceptions import (
    CapturedPaymentRecoveryError,
    DomainException,
    DomainValidationError,
    ImmutableRecordError,
    InvalidStateTransitionError,
    InvariantViolationError,
)
from apro.domain.models import (
    ActionEvaluation,
    AuditEvent,
    Customer,
    Decision,
    Diagnosis,
    Execution,
    Outcome,
    Payment,
    PaymentEvent,
    PolicyDecision,
    RecoveryAction,
    RecoveryCase,
)
from apro.domain.state_machines import (
    transition_execution,
    transition_payment,
    transition_recovery_action,
    transition_recovery_case,
    validate_payment_recovery_eligibility,
)

__all__ = [
    # Enums
    "PaymentStatus",
    "RecoveryCaseStatus",
    "RecoveryActionType",
    "RecoveryActionStatus",
    "PolicyDecisionResult",
    "ExecutionStatus",
    "ExecutionMode",
    "OutcomeType",
    "AuditActor",
    "FailureCategory",
    # Exceptions
    "DomainException",
    "InvalidStateTransitionError",
    "InvariantViolationError",
    "CapturedPaymentRecoveryError",
    "ImmutableRecordError",
    "DomainValidationError",
    # Models
    "Customer",
    "Payment",
    "PaymentEvent",
    "RecoveryCase",
    "Diagnosis",
    "ActionEvaluation",
    "Decision",
    "PolicyDecision",
    "RecoveryAction",
    "Execution",
    "Outcome",
    "AuditEvent",
    # State Machines
    "validate_payment_recovery_eligibility",
    "transition_payment",
    "transition_recovery_case",
    "transition_recovery_action",
    "transition_execution",
]
