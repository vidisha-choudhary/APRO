"""Unit tests for Phase 10 bit-for-bit evaluation reproducibility."""

from datetime import UTC, datetime

from apro.decision.enums import DecisionStatus
from apro.decision.models import ActionEligibility, ActionUtility, RecoveryDecision
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Payment, RecoveryCase
from apro.policy.config import PolicyConfig
from apro.policy.engine import PolicyEngine
from apro.policy.models import ActionExecutionHistory, EventTrustState
from apro.recovery_prediction.enums import RecoveryAction


def test_bit_for_bit_policy_decision_reproducibility():
    """Verify evaluating identical frozen inputs across multiple runs
    yields 100% bit-for-bit identical decision outputs and canonical traces.
    """
    eval_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)
    cfg = PolicyConfig(max_retries=3, high_value_threshold=100000)

    payment = Payment(
        payment_id="pay_repro_01",
        customer_id="cust_repro_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=eval_time,
        updated_at=eval_time,
    )
    case = RecoveryCase(
        case_id="case_repro_01",
        payment_id="pay_repro_01",
        customer_id="cust_repro_01",
        status=RecoveryCaseStatus.NEW,
        opened_at=eval_time,
        updated_at=eval_time,
    )
    utilities = {
        act: ActionUtility(
            action=act,
            eligible=True,
            predicted_success_probability=0.70,
            predicted_recovered_amount=50000,
            expected_gross_recovery=35000,
            action_cost=150,
            operational_cost=50,
            customer_friction_cost=0,
            risk_penalty=0,
            expected_recovery_value=34800,
        )
        for act in RecoveryAction
    }
    eligibilities = {
        act: ActionEligibility(action=act, is_eligible=True) for act in RecoveryAction
    }
    decision = RecoveryDecision(
        decision_id="dec_repro_01",
        record_id="rec_repro_01",
        scenario_id="scen_repro_01",
        recovery_case_id="case_repro_01",
        selected_action=RecoveryAction.RETRY,
        decision_status=DecisionStatus.ACTION_SELECTED,
        expected_recovery_value=34800,
        utility_by_action=utilities,
        eligibility_by_action=eligibilities,
        decision_confidence=0.82,
        rationale="Reproducibility test",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        dataset_version="dataset-v1",
    )
    history = ActionExecutionHistory(retry_count=1)

    engine1 = PolicyEngine()
    engine2 = PolicyEngine()

    dec1, trace1 = engine1.evaluate(
        decision,
        payment,
        case,
        current_time=eval_time,
        config=cfg,
        history=history,
        event_trust=EventTrustState.TRUSTED,
    )
    dec2, trace2 = engine2.evaluate(
        decision,
        payment,
        case,
        current_time=eval_time,
        config=cfg,
        history=history,
        event_trust=EventTrustState.TRUSTED,
    )

    # 1. Exact decision identity & complete model dictionary equality
    assert dec1.policy_decision_id == dec2.policy_decision_id
    assert dec1.model_dump() == dec2.model_dump()

    # 2. Canonical trace equality excluding runtime measurement latency
    assert trace1.policy_decision_id == trace2.policy_decision_id
    assert trace1.model_dump(exclude={"evaluation_latency_ms"}) == trace2.model_dump(
        exclude={"evaluation_latency_ms"}
    )
    assert trace1.evaluation_latency_ms >= 0.0
    assert trace2.evaluation_latency_ms >= 0.0
