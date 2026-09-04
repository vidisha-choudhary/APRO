"""Tests for multi-cycle adaptive recovery loop reconstruction."""

from datetime import UTC, datetime

import pytest

from apro.audit.reconstruction import CaseReconstructionService
from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    FailureCategory,
    OutcomeType,
    PolicyDecisionResult,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import (
    Decision,
    Diagnosis,
    Execution,
    Outcome,
    PolicyDecision,
    RecoveryCase,
)


@pytest.mark.asyncio
async def test_adaptive_multi_cycle_reconstruction() -> None:
    """CaseReconstructionService reconstructs distinct Cycle 1 and Cycle 2 records."""
    case_id = "case_adaptive_test"
    now = datetime.now(UTC)

    case = RecoveryCase(
        case_id=case_id,
        payment_id="pay_1",
        customer_id="cust_1",
        status=RecoveryCaseStatus.RECOVERED,
        opened_at=now,
        updated_at=now,
        recovery_amount=10000,
    )

    diag = Diagnosis(
        diagnosis_id="diag_1",
        case_id=case_id,
        category=FailureCategory.CUSTOMER_SIDE,
        confidence=0.92,
        model_name="diag_v1",
        model_version="1.0.0",
        created_at=now,
    )

    # Cycle 1: Action 1 = RETRY -> FAILED
    dec1 = Decision(
        decision_id="dec_c1",
        case_id=case_id,
        recommended_action=RecoveryActionType.RETRY,
        confidence=0.85,
        expected_recovery_value=3000,
        reason="Initial attempt retry",
        model_name="decision_v1",
        model_version="1.0.0",
        created_at=now,
    )
    pol1 = PolicyDecision(
        policy_decision_id="pol_c1",
        decision_id="dec_c1",
        case_id=case_id,
        result=PolicyDecisionResult.ALLOW,
        reason="H1_MAX_ATTEMPTS: Allowed",
        policy_version="policy-v1",
        created_at=now,
    )
    exec1 = Execution(
        execution_id="exec_c1",
        action_id="act_c1",
        case_id=case_id,
        execution_type="retry_executor",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SUCCEEDED,
        started_at=now,
        completed_at=now,
    )
    out1 = Outcome(
        outcome_id="out_c1",
        case_id=case_id,
        execution_id="exec_c1",
        type=OutcomeType.FAILED,
        amount_recovered=0,
        evidence_reference="retry failed",
        observed_at=now,
    )

    # Cycle 2: Action 2 = ALTERNATE_RECOVERY -> RECOVERED
    dec2 = Decision(
        decision_id="dec_c2",
        case_id=case_id,
        recommended_action=RecoveryActionType.ALTERNATE_RECOVERY,
        confidence=0.95,
        expected_recovery_value=9000,
        reason="Adaptive fallback to payment link",
        model_name="decision_v2",
        model_version="2.0.0",
        created_at=now,
    )
    pol2 = PolicyDecision(
        policy_decision_id="pol_c2",
        decision_id="dec_c2",
        case_id=case_id,
        result=PolicyDecisionResult.ALLOW,
        reason="H2_COOLDOWN: Allowed",
        policy_version="policy-v1",
        created_at=now,
    )
    exec2 = Execution(
        execution_id="exec_c2",
        action_id="act_c2",
        case_id=case_id,
        execution_type="payment_link_executor",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SUCCEEDED,
        started_at=now,
        completed_at=now,
    )
    out2 = Outcome(
        outcome_id="out_c2",
        case_id=case_id,
        execution_id="exec_c2",
        type=OutcomeType.RECOVERED,
        amount_recovered=10000,
        evidence_reference="payment captured",
        observed_at=now,
    )

    trace = await CaseReconstructionService.reconstruct_case(
        case_id=case_id,
        case=case,
        diagnosis=diag,
        decisions=[dec1, dec2],
        policy_decisions=[pol1, pol2],
        executions=[exec1, exec2],
        outcomes=[out1, out2],
    )

    assert len(trace.cycles) == 2
    # Cycle 1
    assert trace.cycles[0].cycle_number == 1
    assert trace.cycles[0].decision is not None
    assert trace.cycles[0].decision.selected_action == "RETRY"
    assert trace.cycles[0].outcome is not None
    assert trace.cycles[0].outcome.outcome_type == "FAILED"

    # Cycle 2
    assert trace.cycles[1].cycle_number == 2
    assert trace.cycles[1].decision is not None
    assert trace.cycles[1].decision.selected_action == "ALTERNATE_RECOVERY"
    assert trace.cycles[1].outcome is not None
    assert trace.cycles[1].outcome.outcome_type == "RECOVERED"
    assert trace.final_case_status == "RECOVERED"
    assert trace.total_amount_recovered == 10000
