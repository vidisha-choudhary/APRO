"""Tests verifying strict anti-leakage isolation between simulator truth and
recovery loop.
"""

from datetime import UTC, datetime

from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Payment, RecoveryCase
from apro.recovery_loop.context import ReEvaluationContextBuilder
from apro.recovery_loop.enums import EvidenceType
from apro.recovery_loop.models import OutcomeEvidence
from apro.simulation.enums import SimulatedActionType, SimulatedPaymentMethod


def test_outcome_evidence_sanitization_rejects_latent_fields() -> None:
    now = datetime.now(UTC)
    raw = {
        "potential_outcomes": {"RETRY": "SUCCESS", "PAYMENT_LINK": "FAILURE"},
        "oracle_action": "RETRY",
        "hidden_recoverability": 0.95,
        "latent_customer_intent": 0.8,
        "latent_bank_condition": 0.9,
        "best_achievable_action": "RETRY",
        "best_achievable_value": 50000,
        "valid_key": "valid_value",
    }
    evidence = OutcomeEvidence(
        evidence_id="ev_leak_01",
        case_id="case_leak_01",
        evidence_type=EvidenceType.SIMULATION_OUTCOME,
        observed_at=now,
        raw_details=raw,
    )

    # Assert all simulator latent fields were completely stripped
    assert "potential_outcomes" not in evidence.raw_details
    assert "oracle_action" not in evidence.raw_details
    assert "hidden_recoverability" not in evidence.raw_details
    assert "latent_customer_intent" not in evidence.raw_details
    assert "latent_bank_condition" not in evidence.raw_details
    assert "best_achievable_action" not in evidence.raw_details
    assert evidence.raw_details["valid_key"] == "valid_value"


def test_re_evaluation_context_contains_zero_simulator_truth() -> None:
    now = datetime.now(UTC)
    features = FeatureSnapshot(
        feature_schema_version="feature-schema-v1",
        decision_timestamp=now.isoformat(),
        payment_id="pay_leak_01",
        payment_amount=50000,
        currency="INR",
        payment_method=SimulatedPaymentMethod.CARD,
        attempt_count=1,
        failure_reason="insufficient_funds",
        failure_code="BAD_REQUEST",
        customer_id="cust_leak_01",
        previous_payment_count=5,
        previous_success_count=4,
        previous_failure_count=1,
        previous_recovery_count=1,
        previous_retry_success=1,
        previous_payment_link_success=0,
        hour_of_day=14,
        day_of_week=2,
        is_weekend=False,
        candidate_actions=[
            SimulatedActionType.RETRY,
            SimulatedActionType.PAYMENT_LINK,
        ],
    )
    base_model_input = ModelInputRecord(
        record_id="rec_leak_01",
        dataset_type=DatasetType.BENCHMARK,
        dataset_version="dataset-v1",
        scenario_id="scen_leak_01",
        generation_seed=42,
        scenario_version="v1",
        configuration_version="v1",
        feature_schema_version="feature-schema-v1",
        features=features,
    )
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
        status=RecoveryCaseStatus.EVALUATING,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )

    builder = ReEvaluationContextBuilder()
    context = builder.build_context(
        case=case,
        payment=payment,
        cycle_number=2,
        history=(),
        latest_diagnosis=None,
        latest_outcome=None,
        base_model_input=base_model_input,
        now=now,
    )

    # Verify model_input dump contains zero hidden truth
    dump = context.model_input.model_dump()
    dump_str = str(dump)
    assert "potential_outcomes" not in dump_str
    assert "oracle_action" not in dump_str
    assert "hidden_recoverability" not in dump_str
    assert "latent_customer_intent" not in dump_str
