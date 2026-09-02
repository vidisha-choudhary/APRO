"""Unit tests for Phase 10 payment state guards, stale event protection,
and pre-execution gate.
"""

from datetime import UTC, datetime, timedelta

from apro.domain.enums import PaymentStatus
from apro.domain.models import Payment
from apro.policy.enums import PolicyReasonCode
from apro.policy.state_guard import (
    StateGuard,
    is_payment_captured,
    is_stale_or_inconsistent_event,
)
from apro.recovery_prediction.enums import RecoveryAction


def make_payment(
    status: PaymentStatus,
    captured_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Payment:
    now = datetime.now(UTC)
    return Payment(
        payment_id="pay_001",
        customer_id="cust_001",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=status,
        created_at=now,
        updated_at=updated_at or now,
        captured_at=captured_at,
    )


def test_is_payment_captured():
    """Verify captured payment check."""
    p_cap = make_payment(PaymentStatus.CAPTURED)
    p_fail = make_payment(PaymentStatus.FAILED)

    assert is_payment_captured(p_cap) is True
    assert is_payment_captured(p_fail) is False
    assert StateGuard.is_captured(p_cap) is True


def test_is_stale_or_inconsistent_event_captured():
    """Verify stale failure event arriving after capture is detected."""
    now = datetime.now(UTC)
    t_cap = now
    t_event_old = now - timedelta(minutes=5)

    p_cap = make_payment(PaymentStatus.CAPTURED, captured_at=t_cap)
    assert is_stale_or_inconsistent_event(t_event_old, p_cap) is True


def test_is_stale_or_inconsistent_event_failed_updated():
    """Verify stale failure event arriving after newer payment update is detected."""
    now = datetime.now(UTC)
    t_updated = now
    t_event_old = now - timedelta(minutes=5)

    p_fail = make_payment(PaymentStatus.FAILED, updated_at=t_updated)
    assert is_stale_or_inconsistent_event(t_event_old, p_fail) is True


def test_check_pre_execution_state_gate_with_status():
    """Verify pre-execution gate blocks if payment became captured in interim."""
    valid, reason, _ = StateGuard.recheck_current_state(
        PaymentStatus.CAPTURED, RecoveryAction.RETRY
    )
    assert valid is False
    assert reason == PolicyReasonCode.PAYMENT_ALREADY_RECOVERED

    valid_ok, reason_ok, _ = StateGuard.recheck_current_state(
        PaymentStatus.FAILED, RecoveryAction.RETRY
    )
    assert valid_ok is True
    assert reason_ok is None


def test_check_pre_execution_state_gate_with_payment_entity():
    """Verify pre-execution gate accepting Payment domain entity."""
    p_cap = make_payment(PaymentStatus.CAPTURED)
    p_fail = make_payment(PaymentStatus.FAILED)

    valid_cap, reason_cap, _ = StateGuard.recheck_current_state(
        p_cap, RecoveryAction.RETRY
    )
    assert valid_cap is False
    assert reason_cap == PolicyReasonCode.PAYMENT_ALREADY_RECOVERED

    valid_fail, reason_fail, _ = StateGuard.recheck_current_state(
        p_fail, RecoveryAction.RETRY
    )
    assert valid_fail is True
    assert reason_fail is None
