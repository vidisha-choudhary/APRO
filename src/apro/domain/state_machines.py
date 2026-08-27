"""Pure state transition engines and invariant validation for APRO."""

from datetime import UTC, datetime

from apro.domain.enums import (
    ExecutionStatus,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryCaseStatus,
)
from apro.domain.exceptions import (
    CapturedPaymentRecoveryError,
    InvalidStateTransitionError,
)
from apro.domain.models import Execution, Payment, RecoveryAction, RecoveryCase

# Allowed state transition mappings

_PAYMENT_ALLOWED_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.CREATED: {
        PaymentStatus.AUTHORIZED,
        PaymentStatus.FAILED,
        PaymentStatus.PENDING,
    },
    PaymentStatus.AUTHORIZED: {
        PaymentStatus.CAPTURED,
        PaymentStatus.FAILED,
    },
    PaymentStatus.FAILED: {
        PaymentStatus.PENDING,
    },
    PaymentStatus.PENDING: {
        PaymentStatus.CAPTURED,
        PaymentStatus.FAILED,
    },
    PaymentStatus.CAPTURED: set(),  # Terminal state
}

_RECOVERY_CASE_ALLOWED_TRANSITIONS: dict[
    RecoveryCaseStatus, set[RecoveryCaseStatus]
] = {
    RecoveryCaseStatus.NEW: {
        RecoveryCaseStatus.DIAGNOSING,
        RecoveryCaseStatus.STOPPED,
        RecoveryCaseStatus.ESCALATED,
    },
    RecoveryCaseStatus.DIAGNOSING: {
        RecoveryCaseStatus.EVALUATING,
        RecoveryCaseStatus.STOPPED,
        RecoveryCaseStatus.ESCALATED,
    },
    RecoveryCaseStatus.EVALUATING: {
        RecoveryCaseStatus.DECISION_PENDING,
        RecoveryCaseStatus.STOPPED,
        RecoveryCaseStatus.ESCALATED,
    },
    RecoveryCaseStatus.DECISION_PENDING: {
        RecoveryCaseStatus.POLICY_CHECK,
        RecoveryCaseStatus.STOPPED,
        RecoveryCaseStatus.ESCALATED,
    },
    RecoveryCaseStatus.POLICY_CHECK: {
        RecoveryCaseStatus.ACTION_APPROVED,
        RecoveryCaseStatus.STOPPED,
        RecoveryCaseStatus.ESCALATED,
    },
    RecoveryCaseStatus.ACTION_APPROVED: {
        RecoveryCaseStatus.EXECUTING,
        RecoveryCaseStatus.STOPPED,
        RecoveryCaseStatus.ESCALATED,
    },
    RecoveryCaseStatus.EXECUTING: {
        RecoveryCaseStatus.OBSERVING,
        RecoveryCaseStatus.STOPPED,
        RecoveryCaseStatus.ESCALATED,
    },
    RecoveryCaseStatus.OBSERVING: {
        RecoveryCaseStatus.RECOVERED,
        RecoveryCaseStatus.EVALUATING,
        RecoveryCaseStatus.STOPPED,
        RecoveryCaseStatus.ESCALATED,
    },
    RecoveryCaseStatus.RECOVERED: set(),  # Terminal state
    RecoveryCaseStatus.STOPPED: set(),  # Terminal state
    RecoveryCaseStatus.ESCALATED: set(),  # Terminal state
}

_RECOVERY_ACTION_ALLOWED_TRANSITIONS: dict[
    RecoveryActionStatus, set[RecoveryActionStatus]
] = {
    RecoveryActionStatus.CANDIDATE: {
        RecoveryActionStatus.RECOMMENDED,
        RecoveryActionStatus.BLOCKED,
    },
    RecoveryActionStatus.RECOMMENDED: {
        RecoveryActionStatus.APPROVED,
        RecoveryActionStatus.BLOCKED,
    },
    RecoveryActionStatus.APPROVED: {
        RecoveryActionStatus.EXECUTING,
        RecoveryActionStatus.CANCELLED,
    },
    RecoveryActionStatus.EXECUTING: {
        RecoveryActionStatus.COMPLETED,
        RecoveryActionStatus.FAILED,
        RecoveryActionStatus.CANCELLED,
    },
    RecoveryActionStatus.BLOCKED: set(),  # Terminal state
    RecoveryActionStatus.COMPLETED: set(),  # Terminal state
    RecoveryActionStatus.FAILED: set(),  # Terminal state
    RecoveryActionStatus.CANCELLED: set(),  # Terminal state
}

_EXECUTION_ALLOWED_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.RUNNING: {
        ExecutionStatus.SUCCEEDED,
        ExecutionStatus.FAILED,
        ExecutionStatus.UNKNOWN,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.SUCCEEDED: set(),  # Terminal state
    ExecutionStatus.FAILED: set(),  # Terminal state
    ExecutionStatus.UNKNOWN: set(),  # Terminal state
    ExecutionStatus.CANCELLED: set(),  # Terminal state
}

_RECOVERY_CASE_TERMINAL_STATES = {
    RecoveryCaseStatus.RECOVERED,
    RecoveryCaseStatus.STOPPED,
    RecoveryCaseStatus.ESCALATED,
}

_RECOVERY_CASE_EXECUTION_ELIGIBILITY_STATES = {
    RecoveryCaseStatus.ACTION_APPROVED,
    RecoveryCaseStatus.EXECUTING,
}


def validate_payment_recovery_eligibility(payment: Payment) -> None:
    """Validate that a payment is eligible for recovery.

    Raises:
        CapturedPaymentRecoveryError: If the payment is already CAPTURED.
    """
    if payment.status == PaymentStatus.CAPTURED:
        msg = f"Payment {payment.payment_id} is CAPTURED and ineligible for recovery."
        raise CapturedPaymentRecoveryError(msg)


def transition_payment(
    payment: Payment, new_status: PaymentStatus, now: datetime | None = None
) -> Payment:
    """Transition a Payment to a new status.

    Raises:
        InvalidStateTransitionError: If the transition is prohibited.
    """
    current_status = payment.status
    allowed = _PAYMENT_ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed:
        if current_status == PaymentStatus.CAPTURED:
            msg = f"Cannot transition Payment from CAPTURED to {new_status}."
            raise CapturedPaymentRecoveryError(msg)
        msg = f"Invalid Payment transition from {current_status} to {new_status}."
        raise InvalidStateTransitionError(msg)

    timestamp = now or datetime.now(UTC)
    updated_fields: dict[str, str | datetime] = {
        "status": new_status,
        "updated_at": timestamp,
    }

    if new_status == PaymentStatus.CAPTURED:
        updated_fields["captured_at"] = timestamp
    elif new_status == PaymentStatus.FAILED:
        updated_fields["failed_at"] = timestamp

    return payment.model_copy(update=updated_fields)


def transition_recovery_case(
    case: RecoveryCase,
    payment: Payment,
    new_status: RecoveryCaseStatus,
    now: datetime | None = None,
) -> RecoveryCase:
    """Transition a RecoveryCase to a new status while enforcing invariants.

    Raises:
        CapturedPaymentRecoveryError: If payment is CAPTURED and execution attempted.
        InvalidStateTransitionError: If transition is prohibited or case is terminal.
    """
    # Safety Check: CAPTURED payment attempting recovery execution eligibility
    if (
        payment.status == PaymentStatus.CAPTURED
        and new_status in _RECOVERY_CASE_EXECUTION_ELIGIBILITY_STATES
    ):
        msg = (
            f"Cannot transition RecoveryCase {case.case_id} to {new_status} "
            f"because Payment {payment.payment_id} is CAPTURED."
        )
        raise CapturedPaymentRecoveryError(msg)

    current_status = case.status
    if current_status in _RECOVERY_CASE_TERMINAL_STATES:
        msg = f"Cannot transition RecoveryCase from terminal state {current_status}."
        raise InvalidStateTransitionError(msg)

    allowed = _RECOVERY_CASE_ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        msg = f"Invalid RecoveryCase transition from {current_status} to {new_status}."
        raise InvalidStateTransitionError(msg)

    timestamp = now or datetime.now(UTC)
    updated_fields: dict[str, str | datetime] = {
        "status": new_status,
        "updated_at": timestamp,
    }

    if new_status in _RECOVERY_CASE_TERMINAL_STATES:
        updated_fields["closed_at"] = timestamp

    return case.model_copy(update=updated_fields)


def transition_recovery_action(
    action: RecoveryAction,
    new_status: RecoveryActionStatus,
    now: datetime | None = None,
) -> RecoveryAction:
    """Transition a RecoveryAction to a new status.

    Raises:
        InvalidStateTransitionError: If transition is prohibited or action is terminal.
    """
    current_status = action.status
    allowed = _RECOVERY_ACTION_ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed:
        msg = (
            f"Invalid RecoveryAction transition from {current_status} to {new_status}."
        )
        raise InvalidStateTransitionError(msg)

    timestamp = now or datetime.now(UTC)
    return action.model_copy(
        update={
            "status": new_status,
            "updated_at": timestamp,
        }
    )


def transition_execution(
    execution: Execution,
    new_status: ExecutionStatus,
    now: datetime | None = None,
) -> Execution:
    """Transition an Execution to a new status.

    Raises:
        InvalidStateTransitionError: If transition is prohibited or execution is done.
    """
    current_status = execution.status
    allowed = _EXECUTION_ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed:
        msg = f"Invalid Execution transition from {current_status} to {new_status}."
        raise InvalidStateTransitionError(msg)

    timestamp = now or datetime.now(UTC)
    updated_fields: dict[str, str | datetime] = {
        "status": new_status,
    }

    if new_status in {
        ExecutionStatus.SUCCEEDED,
        ExecutionStatus.FAILED,
        ExecutionStatus.UNKNOWN,
        ExecutionStatus.CANCELLED,
    }:
        updated_fields["completed_at"] = timestamp

    return execution.model_copy(update=updated_fields)
