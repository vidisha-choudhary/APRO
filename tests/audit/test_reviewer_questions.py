"""Tests validating the 7 Reviewer Questions from reconstruction."""

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
    Payment,
    PolicyDecision,
    RecoveryCase,
)


@pytest.mark.asyncio
async def test_reviewer_seven_questions_answered() -> None:
    """CaseReconstructionService answers all 7 reviewer questions completely."""
    case_id = "case_rev_7"
    now = datetime.now(UTC)

    case = RecoveryCase(
        case_id=case_id,
        payment_id="pay_rev_7",
        customer_id="cust_rev_7",
        status=RecoveryCaseStatus.RECOVERED,
        opened_at=now,
        updated_at=now,
        recovery_amount=20000,
    )
    payment = Payment(
        payment_id="pay_rev_7",
        customer_id="cust_rev_7",
        provider="razorpay",
        amount=20000,
        currency="INR",
        method="card",
        status=pytest.importorskip("apro.domain.enums").PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    diag = Diagnosis(
        diagnosis_id="diag_rev_7",
        case_id=case_id,
        category=FailureCategory.CUSTOMER_SIDE,
        confidence=0.94,
        model_name="diag_v1",
        model_version="1.0.0",
        created_at=now,
    )
    dec = Decision(
        decision_id="dec_rev_7",
        case_id=case_id,
        recommended_action=RecoveryActionType.ALTERNATE_RECOVERY,
        confidence=0.96,
        expected_recovery_value=18000,
        reason="Maximum expected recovery value",
        model_name="decision_engine",
        model_version="1.0.0",
        created_at=now,
    )
    pol = PolicyDecision(
        policy_decision_id="pol_rev_7",
        decision_id="dec_rev_7",
        case_id=case_id,
        result=PolicyDecisionResult.ALLOW,
        reason="H1_MAX_ATTEMPTS: ALLOW",
        policy_version="policy-v1",
        created_at=now,
    )
    exc = Execution(
        execution_id="exec_rev_7",
        action_id="act_rev_7",
        case_id=case_id,
        execution_type="payment_link_executor",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SUCCEEDED,
        provider_reference="plink_rev_7",
        started_at=now,
        completed_at=now,
    )
    out = Outcome(
        outcome_id="out_rev_7",
        case_id=case_id,
        execution_id="exec_rev_7",
        type=OutcomeType.RECOVERED,
        amount_recovered=20000,
        evidence_reference="captured",
        observed_at=now,
    )

    trace = await CaseReconstructionService.reconstruct_case(
        case_id=case_id,
        case=case,
        payment=payment,
        diagnosis=diag,
        decisions=[dec],
        policy_decisions=[pol],
        executions=[exc],
        outcomes=[out],
    )

    q = trace.reviewer_answers
    # 1. What happened?
    assert q["Q1_what_happened"]["case_id"] == case_id
    assert q["Q1_what_happened"]["amount"] == 20000

    # 2. Why was it interpreted that way?
    assert q["Q2_why_interpreted"]["category"] == "CUSTOMER_SIDE"
    assert q["Q2_why_interpreted"]["confidence"] == 0.94

    # 3. What was considered?
    assert "Q3_what_considered" in q

    # 4. What was recommended?
    assert q["Q4_what_recommended"][0]["selected_action"] == "ALTERNATE_RECOVERY"

    # 5. What did policy allow?
    assert q["Q5_what_policy_allowed"][0]["policy_outcome"] == "ALLOW"

    # 6. What executed?
    assert q["Q6_what_executed"][0]["execution_id"] == "exec_rev_7"
    assert q["Q6_what_executed"][0]["provider_reference"] == "plink_rev_7"

    # 7. What happened afterward?
    assert q["Q7_what_happened_afterward"]["final_case_status"] == "RECOVERED"
    assert q["Q7_what_happened_afterward"]["total_amount_recovered"] == 20000
