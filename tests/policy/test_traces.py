"""Unit tests for Phase 10 PolicyEvaluationTrace completeness and sanitization."""

from datetime import UTC, datetime

from apro.decision.enums import DecisionStatus
from apro.decision.models import ActionEligibility, ActionUtility, RecoveryDecision
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Payment, RecoveryCase
from apro.policy.engine import PolicyEngine
from apro.policy.enums import PolicyOutcome
from apro.policy.models import EventTrustState
from apro.recovery_prediction.enums import RecoveryAction


def test_trace_generation_and_fields():
    """Verify PolicyEvaluationTrace includes all required audit and schema fields."""
    engine = PolicyEngine()
    now = datetime.now(UTC)
    payment = Payment(
        payment_id="pay_tr_01",
        customer_id="cust_tr_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_tr_01",
        payment_id="pay_tr_01",
        customer_id="cust_tr_01",
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
    )
    utilities = {
        act: ActionUtility(
            action=act,
            eligible=True,
            predicted_success_probability=0.80,
            predicted_recovered_amount=50000,
            expected_gross_recovery=40000,
            action_cost=150,
            operational_cost=50,
            customer_friction_cost=0,
            risk_penalty=0,
            expected_recovery_value=39800,
        )
        for act in RecoveryAction
    }
    eligibilities = {
        act: ActionEligibility(action=act, is_eligible=True) for act in RecoveryAction
    }
    decision = RecoveryDecision(
        decision_id="dec_tr_01",
        record_id="rec_tr_01",
        scenario_id="scen_tr_01",
        recovery_case_id="case_tr_01",
        selected_action=RecoveryAction.RETRY,
        decision_status=DecisionStatus.ACTION_SELECTED,
        expected_recovery_value=39800,
        utility_by_action=utilities,
        eligibility_by_action=eligibilities,
        decision_confidence=0.88,
        rationale="Trace test rationale",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        dataset_version="dataset-v1",
    )

    pol_dec, trace = engine.evaluate(
        decision, payment, case, event_trust=EventTrustState.TRUSTED, current_time=now
    )

    assert trace.policy_decision_id == pol_dec.policy_decision_id
    assert trace.case_id == "case_tr_01"
    assert trace.payment_id == "pay_tr_01"
    assert trace.policy_outcome == PolicyOutcome.ALLOW
    assert trace.effective_action == RecoveryAction.RETRY
    assert trace.rules_evaluated is not None
    assert len(trace.rules_evaluated) == 22
    assert trace.idempotency_key == "idem_case_tr_01_RETRY_1"
    assert trace.trace_schema_version == "policy-trace-v1"
    assert trace.evaluation_latency_ms >= 0.0
