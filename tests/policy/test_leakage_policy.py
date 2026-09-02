"""Unit tests verifying zero simulator latent truth leakage
into live policy evaluation path.
"""

from datetime import UTC, datetime

from apro.decision.enums import DecisionStatus
from apro.decision.models import ActionEligibility, ActionUtility, RecoveryDecision
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Payment, RecoveryCase
from apro.policy.engine import PolicyEngine
from apro.policy.models import EventTrustState
from apro.recovery_prediction.enums import RecoveryAction


def test_zero_simulator_truth_leakage_in_policy_engine():
    """Verify live PolicyEngine never accesses or exposes latent truth fields."""
    now = datetime.now(UTC)
    payment = Payment(
        payment_id="pay_leak_01",
        customer_id="cust_leak_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_leak_01",
        payment_id="pay_leak_01",
        customer_id="cust_leak_01",
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
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
        decision_id="dec_leak_01",
        record_id="rec_leak_01",
        scenario_id="scen_leak_01",
        recovery_case_id="case_leak_01",
        selected_action=RecoveryAction.RETRY,
        decision_status=DecisionStatus.ACTION_SELECTED,
        expected_recovery_value=34800,
        utility_by_action=utilities,
        eligibility_by_action=eligibilities,
        decision_confidence=0.85,
        rationale="Anti-leakage test",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        dataset_version="dataset-v1",
    )

    engine = PolicyEngine()
    pol_dec, trace = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        event_trust=EventTrustState.TRUSTED,
    )

    # Convert trace and decision to verify absence of simulator hidden keys
    trace_dict = trace.model_dump()
    dec_dict = pol_dec.model_dump()

    forbidden_terms = (
        "potential_outcomes",
        "oracle_action",
        "ground_truth",
        "latent_state",
        "hidden_failure_cause",
    )

    for term in forbidden_terms:
        assert term not in trace_dict, f"Forbidden term '{term}' found in trace!"
        assert term not in dec_dict, (
            f"Forbidden term '{term}' found in policy decision!"
        )
