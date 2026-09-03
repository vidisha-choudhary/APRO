"""Tests verifying finite loop boundedness and termination limits in Phase 13."""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import (
    PaymentStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Payment, RecoveryCase
from apro.recovery_loop.enums import LoopTerminationReason
from apro.recovery_loop.exceptions import UnboundedLoopError
from apro.recovery_loop.guards import LoopSafetyGuard
from apro.recovery_loop.models import ActionHistoryRecord


def test_attempt_limit_exceeded_triggers_finite_termination() -> None:
    guard = LoopSafetyGuard(max_attempts=3)
    now = datetime.now(UTC)
    case = RecoveryCase(
        case_id="case_bound_01",
        payment_id="pay_bound_01",
        customer_id="cust_bound_01",
        status=RecoveryCaseStatus.EVALUATING,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=3,
    )
    payment = Payment(
        payment_id="pay_bound_01",
        customer_id="cust_bound_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    history = [
        ActionHistoryRecord(
            action_id=f"act_0{i}",
            action_type=RecoveryActionType.RETRY,
            execution_id=f"exec_0{i}",
            observed_at=now,
            attempt_order=i,
        )
        for i in range(1, 4)
    ]

    can_continue, reason = guard.evaluate_loop_bounds(
        case=case,
        payment=payment,
        history=history,
        cycle_number=3,
    )
    assert can_continue is False
    assert reason == LoopTerminationReason.ATTEMPT_LIMIT_EXCEEDED


def test_hard_cycle_ceiling_prevents_infinite_recursion() -> None:
    guard = LoopSafetyGuard(hard_cycle_ceiling=10)
    now = datetime.now(UTC)
    case = RecoveryCase(
        case_id="case_bound_02",
        payment_id="pay_bound_02",
        customer_id="cust_bound_02",
        status=RecoveryCaseStatus.EVALUATING,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )
    payment = Payment(
        payment_id="pay_bound_02",
        customer_id="cust_bound_02",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(UnboundedLoopError):
        guard.evaluate_loop_bounds(
            case=case,
            payment=payment,
            history=[],
            cycle_number=11,
        )
