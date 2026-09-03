"""Tests verifying captured payment race safety in Phase 13."""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import (
    ExecutionMode,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.exceptions import CapturedPaymentRecoveryError
from apro.domain.models import Payment, RecoveryAction, RecoveryCase
from apro.execution.exceptions import ExecutionStateError
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import PolicyDecision
from apro.recovery_loop.guards import LoopSafetyGuard
from apro.recovery_prediction.enums import RecoveryAction as PredictorAction


@pytest.mark.asyncio
async def test_dynamic_capture_race_blocks_phase_11_dispatch() -> None:
    """If payment becomes CAPTURED during re-evaluation, StateGuard blocks execution."""
    orchestrator = ExecutionOrchestrator()
    now = datetime.now(UTC)

    # Payment has been dynamically captured out-of-band
    captured_payment = Payment(
        payment_id="pay_race_01",
        customer_id="cust_race_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.CAPTURED,
        created_at=now,
        updated_at=now,
        captured_at=now,
    )
    case = RecoveryCase(
        case_id="case_race_01",
        payment_id="pay_race_01",
        customer_id="cust_race_01",
        status=RecoveryCaseStatus.ACTION_APPROVED,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )
    policy_decision = PolicyDecision(
        policy_decision_id="pol_dec_race_01",
        case_id="case_race_01",
        payment_id="pay_race_01",
        decision_id="dec_race_01",
        requested_action=PredictorAction.PAYMENT_LINK,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=PredictorAction.PAYMENT_LINK,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Rule allow",
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        created_at=now,
    )
    action = RecoveryAction(
        action_id="act_race_01",
        case_id="case_race_01",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
        execution_mode=ExecutionMode.SIMULATION,
        parameters={"amount": 50000},
    )

    with pytest.raises((ExecutionStateError, CapturedPaymentRecoveryError)):
        await orchestrator.execute(
            policy_decision=policy_decision,
            recovery_action=action,
            recovery_case=case,
            payment=captured_payment,
            execution_mode=ExecutionMode.SIMULATION,
            current_time=now,
            parameters={"amount": 50000},
        )


def test_loop_safety_guard_blocks_captured_payment() -> None:
    """LoopSafetyGuard detects captured payment and prohibits further execution."""
    guard = LoopSafetyGuard()
    now = datetime.now(UTC)
    captured_payment = Payment(
        payment_id="pay_race_02",
        customer_id="cust_race_02",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.CAPTURED,
        created_at=now,
        updated_at=now,
        captured_at=now,
    )
    case = RecoveryCase(
        case_id="case_race_02",
        payment_id="pay_race_02",
        customer_id="cust_race_02",
        status=RecoveryCaseStatus.EVALUATING,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )

    can_continue, reason = guard.evaluate_loop_bounds(
        case=case,
        payment=captured_payment,
        history=[],
        cycle_number=2,
    )
    assert can_continue is False
