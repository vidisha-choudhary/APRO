"""Payment state guards, stale-event protections, and verification gates."""

from datetime import datetime

from apro.domain.enums import PaymentStatus
from apro.domain.models import Payment
from apro.policy.enums import PolicyReasonCode
from apro.recovery_prediction.enums import RecoveryAction


def is_payment_captured(payment: Payment) -> bool:
    """Check whether the payment is already in CAPTURED state."""
    return payment.status == PaymentStatus.CAPTURED


def is_stale_or_inconsistent_event(
    event_timestamp: datetime,
    payment: Payment,
) -> bool:
    """Check whether an incoming failure event is stale relative to state."""
    if payment.status == PaymentStatus.CAPTURED:
        # If payment was already captured, an older failure event is stale
        if payment.captured_at and event_timestamp < payment.captured_at:
            return True
        if payment.updated_at and event_timestamp < payment.updated_at:
            return True
    elif payment.updated_at and event_timestamp < payment.updated_at:
        # Event is older than current known payment update
        return True
    return False


def is_payment_recoverable(payment: Payment) -> bool:
    """Check whether payment is in a recoverable state (e.g. FAILED, PENDING)."""
    return payment.status in (PaymentStatus.FAILED, PaymentStatus.PENDING)


def check_pre_execution_state_gate(
    payment_or_status: Payment | PaymentStatus,
    approved_action: RecoveryAction,
) -> tuple[bool, PolicyReasonCode | None, str | None]:
    """Perform final pre-execution state recheck before action dispatch."""
    status = (
        payment_or_status.status
        if isinstance(payment_or_status, Payment)
        else payment_or_status
    )
    if status == PaymentStatus.CAPTURED:
        return (
            False,
            PolicyReasonCode.PAYMENT_ALREADY_RECOVERED,
            f"Pre-execution recheck blocked: payment is currently {status.value}. "
            f"Execution of '{approved_action.value}' is prohibited.",
        )

    if status not in (PaymentStatus.FAILED, PaymentStatus.PENDING):
        return (
            False,
            PolicyReasonCode.RECONCILIATION_REQUIRED,
            f"Pre-execution recheck blocked: payment status '{status.value}' "
            "is non-recoverable or unknown.",
        )

    return True, None, None


class StateGuard:
    """Namespace container for payment state consistency checks."""

    @staticmethod
    def is_captured(payment: Payment) -> bool:
        return is_payment_captured(payment)

    @staticmethod
    def is_stale(event_timestamp: datetime, payment: Payment) -> bool:
        return is_stale_or_inconsistent_event(event_timestamp, payment)

    @staticmethod
    def is_recoverable(payment: Payment) -> bool:
        return is_payment_recoverable(payment)

    @staticmethod
    def recheck_current_state(
        payment_or_status: Payment | PaymentStatus,
        approved_action: RecoveryAction,
    ) -> tuple[bool, PolicyReasonCode | None, str | None]:
        """Verify current state immediately before execution dispatch."""
        return check_pre_execution_state_gate(payment_or_status, approved_action)

    @staticmethod
    def recheck(
        payment_or_status: Payment | PaymentStatus,
        approved_action: RecoveryAction,
    ) -> tuple[bool, PolicyReasonCode | None, str | None]:
        return check_pre_execution_state_gate(payment_or_status, approved_action)


__all__ = [
    "StateGuard",
    "check_pre_execution_state_gate",
    "is_payment_captured",
    "is_payment_recoverable",
    "is_stale_or_inconsistent_event",
]
