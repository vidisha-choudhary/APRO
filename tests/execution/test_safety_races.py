"""Unit tests for safety invariants, race conditions, and block-path isolation."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Execution, Payment, RecoveryAction, RecoveryCase
from apro.execution.exceptions import (
    ExecutionAuthorizationError,
    ExecutionStateError,
)
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.execution.registry import ExecutorRegistry
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import PolicyDecision
from apro.recovery_prediction.enums import RecoveryAction as PredictRecoveryAction


def _fixture(
    payment_status: PaymentStatus = PaymentStatus.FAILED,
) -> tuple[PolicyDecision, RecoveryAction, RecoveryCase, Payment]:
    now = datetime.now(UTC)
    pol = PolicyDecision(
        policy_decision_id="pol_safe_01",
        case_id="case_safe_01",
        payment_id="pay_safe_01",
        decision_id="dec_safe_01",
        requested_action=PredictRecoveryAction.RETRY,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=PredictRecoveryAction.RETRY,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Policy approved",
        idempotency_key="idem_safe_01",
        payment_state_observed=payment_status,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        created_at=now,
    )
    act = RecoveryAction(
        action_id="act_safe_01",
        case_id="case_safe_01",
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_safe_01",
        payment_id="pay_safe_01",
        customer_id="cust_safe_01",
        status=RecoveryCaseStatus.ACTION_APPROVED,
        opened_at=now,
        updated_at=now,
    )
    pay = Payment(
        payment_id="pay_safe_01",
        customer_id="cust_safe_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=payment_status,
        created_at=now,
        updated_at=now,
    )
    return pol, act, case, pay


@pytest.mark.asyncio
async def test_dynamic_payment_capture_race_during_execution_pipeline() -> None:
    """Verify true race: payment is FAILED at auth, but CAPTURED in-flight."""
    pol, act, case, pay = _fixture(PaymentStatus.FAILED)

    mock_executor = MagicMock()
    mock_executor.action_type = RecoveryActionType.RETRY
    mock_executor.supported_modes = {ExecutionMode.SIMULATION}
    mock_executor.validate = MagicMock()
    mock_executor.execute = AsyncMock()

    registry = ExecutorRegistry()
    registry.register(mock_executor)
    orchestrator = ExecutionOrchestrator(registry=registry)

    # Hook simulates a concurrent payment capture arriving mid-pipeline
    def simulate_concurrent_capture() -> None:
        pay.status = PaymentStatus.CAPTURED
        pay.captured_at = datetime.now(UTC)

    orchestrator._pre_gate_hook = simulate_concurrent_capture

    with pytest.raises(ExecutionStateError, match="CAPTURED"):
        await orchestrator.execute(
            policy_decision=pol,
            recovery_action=act,
            recovery_case=case,
            payment=pay,
            execution_mode=ExecutionMode.SIMULATION,
        )

    # Assert that despite valid initial ALLOW, executor was NEVER dispatched
    assert mock_executor.execute.call_count == 0


@pytest.mark.asyncio
async def test_captured_payment_static_precondition_blocked() -> None:
    """Verify static precondition: already CAPTURED payment rejected immediately."""
    pol, act, case, pay = _fixture(PaymentStatus.CAPTURED)

    mock_executor = MagicMock()
    mock_executor.action_type = RecoveryActionType.RETRY
    mock_executor.supported_modes = {ExecutionMode.SIMULATION}
    mock_executor.validate = MagicMock()
    mock_executor.execute = AsyncMock()

    registry = ExecutorRegistry()
    registry.register(mock_executor)
    orchestrator = ExecutionOrchestrator(registry=registry)

    with pytest.raises(ExecutionStateError, match="CAPTURED"):
        await orchestrator.execute(
            policy_decision=pol,
            recovery_action=act,
            recovery_case=case,
            payment=pay,
            execution_mode=ExecutionMode.SIMULATION,
        )

    assert mock_executor.execute.call_count == 0


@pytest.mark.asyncio
async def test_block_policy_isolation_zero_executor_invocations() -> None:
    """Verify PolicyOutcome.BLOCK never invokes any executor."""
    pol, act, case, pay = _fixture(PaymentStatus.FAILED)
    pol_blocked = pol.model_copy(
        update={"policy_outcome": PolicyOutcome.BLOCK, "effective_action": None}
    )

    mock_executor = MagicMock()
    mock_executor.action_type = RecoveryActionType.RETRY
    mock_executor.supported_modes = {ExecutionMode.SIMULATION}
    mock_executor.validate = MagicMock()
    mock_executor.execute = AsyncMock()

    registry = ExecutorRegistry()
    registry.register(mock_executor)
    orchestrator = ExecutionOrchestrator(registry=registry)

    with pytest.raises(ExecutionAuthorizationError, match="BLOCK"):
        await orchestrator.execute(
            policy_decision=pol_blocked,
            recovery_action=act,
            recovery_case=case,
            payment=pay,
            execution_mode=ExecutionMode.SIMULATION,
        )

    assert mock_executor.execute.call_count == 0


@pytest.mark.asyncio
async def test_unapproved_human_approval_isolation_zero_executor_invocations() -> None:
    """Verify REQUIRE_HUMAN_APPROVAL without approval ref never invokes executor."""
    pol, act, case, pay = _fixture(PaymentStatus.FAILED)
    pol_approval = pol.model_copy(
        update={
            "policy_outcome": PolicyOutcome.REQUIRE_HUMAN_APPROVAL,
            "approval_reference": None,
        }
    )

    mock_executor = MagicMock()
    mock_executor.action_type = RecoveryActionType.RETRY
    mock_executor.supported_modes = {ExecutionMode.SIMULATION}
    mock_executor.validate = MagicMock()
    mock_executor.execute = AsyncMock()

    registry = ExecutorRegistry()
    registry.register(mock_executor)
    orchestrator = ExecutionOrchestrator(registry=registry)

    with pytest.raises(ExecutionAuthorizationError, match="requires human approval"):
        await orchestrator.execute(
            policy_decision=pol_approval,
            recovery_action=act,
            recovery_case=case,
            payment=pay,
            execution_mode=ExecutionMode.SIMULATION,
        )

    assert mock_executor.execute.call_count == 0


@pytest.mark.asyncio
async def test_explicit_execution_cancellation() -> None:
    """Verify cancel_execution explicitly updates action and execution to CANCELLED."""
    now = datetime.now(UTC)
    act = RecoveryAction(
        action_id="act_cancel_test",
        case_id="case_cancel_test",
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.EXECUTING,
        created_at=now,
        updated_at=now,
    )
    exc = Execution(
        execution_id="exec_cancel_test",
        action_id="act_cancel_test",
        case_id="case_cancel_test",
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.RUNNING,
        started_at=now,
    )

    orchestrator = ExecutionOrchestrator()
    cancelled_act, cancelled_exc = await orchestrator.cancel_execution(
        recovery_action=act,
        execution=exc,
        current_time=now,
    )

    assert cancelled_act.status == RecoveryActionStatus.CANCELLED
    assert cancelled_exc.status == ExecutionStatus.CANCELLED
