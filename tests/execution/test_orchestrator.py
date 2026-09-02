"""Unit tests for the ExecutionOrchestrator."""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Payment, RecoveryAction, RecoveryCase
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import PolicyDecision
from apro.recovery_prediction.enums import RecoveryAction as PredictRecoveryAction


def _fixture(
    action_type: RecoveryActionType = RecoveryActionType.RETRY,
    case_status: RecoveryCaseStatus = RecoveryCaseStatus.ACTION_APPROVED,
) -> tuple[PolicyDecision, RecoveryAction, RecoveryCase, Payment]:
    now = datetime.now(UTC)
    pred_action = (
        PredictRecoveryAction(action_type.value)
        if action_type != RecoveryActionType.ALTERNATE_RECOVERY
        else PredictRecoveryAction.PAYMENT_LINK
    )

    pol = PolicyDecision(
        policy_decision_id="pol_dec_orch_01",
        case_id="case_orch_01",
        payment_id="pay_orch_01",
        decision_id="dec_orch_01",
        requested_action=pred_action,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=pred_action,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Policy approved",
        idempotency_key=f"idem_case_orch_01_{action_type.value}_1",
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        created_at=now,
    )
    act = RecoveryAction(
        action_id="act_orch_01",
        case_id="case_orch_01",
        action_type=action_type,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_orch_01",
        payment_id="pay_orch_01",
        customer_id="cust_orch_01",
        status=case_status,
        opened_at=now,
        updated_at=now,
    )
    pay = Payment(
        payment_id="pay_orch_01",
        customer_id="cust_orch_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    return pol, act, case, pay


@pytest.mark.asyncio
async def test_orchestrator_retry_execution_success():
    """Verify orchestrator runs RETRY and updates case to OBSERVING."""
    pol, act, case, pay = _fixture(RecoveryActionType.RETRY)
    orchestrator = ExecutionOrchestrator()

    result = await orchestrator.execute(
        policy_decision=pol,
        recovery_action=act,
        recovery_case=case,
        payment=pay,
        execution_mode=ExecutionMode.SIMULATION,
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.executor_name == "SimulationRetryExecutor"


@pytest.mark.asyncio
async def test_orchestrator_stop_execution_success():
    """Verify orchestrator runs STOP and updates case to STOPPED."""
    pol, act, case, pay = _fixture(RecoveryActionType.STOP)
    orchestrator = ExecutionOrchestrator()

    result = await orchestrator.execute(
        policy_decision=pol,
        recovery_action=act,
        recovery_case=case,
        payment=pay,
        execution_mode=ExecutionMode.INTERNAL,
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.executor_name == "NoOpExecutor"


@pytest.mark.asyncio
async def test_orchestrator_escalation_execution_success():
    """Verify orchestrator runs ESCALATE and updates case to ESCALATED."""
    pol, act, case, pay = _fixture(RecoveryActionType.ESCALATE)
    orchestrator = ExecutionOrchestrator()

    result = await orchestrator.execute(
        policy_decision=pol,
        recovery_action=act,
        recovery_case=case,
        payment=pay,
        execution_mode=ExecutionMode.INTERNAL,
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.executor_name == "EscalationExecutor"


@pytest.mark.asyncio
async def test_orchestrator_idempotency_reuse():
    """Verify repeated execution with same idempotency key reuses existing execution."""
    pol, act, case, pay = _fixture(RecoveryActionType.RETRY)
    orchestrator = ExecutionOrchestrator()

    res1 = await orchestrator.execute(
        policy_decision=pol,
        recovery_action=act,
        recovery_case=case,
        payment=pay,
        execution_mode=ExecutionMode.SIMULATION,
    )

    res2 = await orchestrator.execute(
        policy_decision=pol,
        recovery_action=act,
        recovery_case=case,
        payment=pay,
        execution_mode=ExecutionMode.SIMULATION,
    )

    assert res1.execution_id == res2.execution_id
    assert res1.status == res2.status
