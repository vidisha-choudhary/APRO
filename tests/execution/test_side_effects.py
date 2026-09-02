"""Unit tests for side effect guards, network isolation, and determinism."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from apro.domain.enums import (
    ExecutionMode,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Payment, RecoveryAction, RecoveryCase
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.execution.validation import FORBIDDEN_SECRET_KEYS
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import PolicyDecision
from apro.recovery_prediction.enums import RecoveryAction as PredictRecoveryAction


def _fixture(
    action_type: RecoveryActionType = RecoveryActionType.RETRY,
) -> tuple[PolicyDecision, RecoveryAction, RecoveryCase, Payment]:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    pred_action = (
        PredictRecoveryAction(action_type.value)
        if action_type != RecoveryActionType.ALTERNATE_RECOVERY
        else PredictRecoveryAction.PAYMENT_LINK
    )

    pol = PolicyDecision(
        policy_decision_id="pol_side_01",
        case_id="case_side_01",
        payment_id="pay_side_01",
        decision_id="dec_side_01",
        requested_action=pred_action,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=pred_action,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Policy approved",
        idempotency_key=f"idem_case_side_01_{action_type.value}_1",
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        created_at=now,
    )
    act = RecoveryAction(
        action_id="act_side_01",
        case_id="case_side_01",
        action_type=action_type,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_side_01",
        payment_id="pay_side_01",
        customer_id="cust_side_01",
        status=RecoveryCaseStatus.ACTION_APPROVED,
        opened_at=now,
        updated_at=now,
    )
    pay = Payment(
        payment_id="pay_side_01",
        customer_id="cust_side_01",
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
async def test_zero_network_effects_during_execution() -> None:
    """Verify Phase 11 execution attempts produce zero outbound network calls."""
    mock_net = MagicMock()
    with (
        patch("socket.socket.connect", mock_net),
        patch("urllib.request.urlopen", mock_net),
        patch("http.client.HTTPConnection.connect", mock_net),
    ):
        orchestrator = ExecutionOrchestrator()
        actions = (
            RecoveryActionType.RETRY,
            RecoveryActionType.ALTERNATE_RECOVERY,
            RecoveryActionType.OUTREACH,
        )
        for action in actions:
            pol, act, case, pay = _fixture(action)
            await orchestrator.execute(pol, act, case, pay, ExecutionMode.SIMULATION)

        assert mock_net.call_count == 0


@pytest.mark.asyncio
async def test_simulation_determinism_identical_results() -> None:
    """Verify identical frozen simulation requests produce identical results."""
    pol, act, case, pay = _fixture(RecoveryActionType.RETRY)
    frozen_time = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)

    orch1 = ExecutionOrchestrator()
    orch2 = ExecutionOrchestrator()

    res1 = await orch1.execute(
        pol, act, case, pay, ExecutionMode.SIMULATION, current_time=frozen_time
    )
    res2 = await orch2.execute(
        pol, act, case, pay, ExecutionMode.SIMULATION, current_time=frozen_time
    )

    assert res1.status == res2.status
    assert res1.execution_mode == res2.execution_mode
    assert res1.executor_name == res2.executor_name
    assert res1.metadata == res2.metadata


@pytest.mark.asyncio
async def test_secret_isolation_in_execution_results() -> None:
    """Verify execution results and metadata contain no sensitive credentials."""
    pol, act, case, pay = _fixture(RecoveryActionType.RETRY)
    orchestrator = ExecutionOrchestrator()
    result = await orchestrator.execute(pol, act, case, pay, ExecutionMode.SIMULATION)

    res_str = str(result.model_dump()).lower()
    for forbidden in FORBIDDEN_SECRET_KEYS:
        assert forbidden not in res_str
