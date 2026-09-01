"""Unit tests for policy eligibility constraints and safety rules."""

from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.decision.eligibility import (
    PolicyConfiguration,
    PolicyEligibilityEngine,
)
from apro.decision.enums import RecoveryAction
from apro.diagnosis.enums import DiagnosisCategory, UncertaintyState
from apro.diagnosis.models import DiagnosisResult
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedPaymentMethod,
)


def _make_dummy_input(
    amount: int = 500000,
    attempt_count: int = 1,
    previous_recovery_count: int = 0,
) -> ModelInputRecord:
    feats = FeatureSnapshot(
        decision_timestamp="2026-09-01T00:00:00Z",
        payment_id="pay_test_001",
        payment_amount=amount,
        currency="INR",
        payment_method=SimulatedPaymentMethod.CARD,
        attempt_count=attempt_count,
        failure_reason="insufficient_funds",
        failure_code="BAD_REQUEST",
        customer_id="cust_001",
        previous_payment_count=2,
        previous_success_count=1,
        previous_failure_count=1,
        previous_recovery_count=previous_recovery_count,
        previous_retry_success=0,
        previous_payment_link_success=0,
        hour_of_day=10,
        day_of_week=2,
        is_weekend=False,
        candidate_actions=list(SimulatedActionType),
    )
    return ModelInputRecord(
        record_id="rec_test_001",
        dataset_type=DatasetType.TRAINING,
        dataset_version="train-test-v1",
        scenario_id="sc_test_001",
        generation_seed=42,
        scenario_version="scenario-v1",
        configuration_version="config-v1",
        feature_schema_version="feature-schema-v1",
        features=feats,
    )


def test_stop_and_escalate_always_eligible() -> None:
    """Verify STOP and ESCALATE are unconditionally eligible."""
    engine = PolicyEligibilityEngine()
    rec = _make_dummy_input()

    elig_stop = engine.evaluate_action_eligibility(rec, RecoveryAction.STOP)
    assert elig_stop.is_eligible is True
    assert elig_stop.policy_rule == "RULE_ALWAYS_ELIGIBLE_STOP"

    elig_esc = engine.evaluate_action_eligibility(rec, RecoveryAction.ESCALATE)
    assert elig_esc.is_eligible is True
    assert elig_esc.policy_rule == "RULE_ALWAYS_ELIGIBLE_ESCALATE"


def test_max_retries_constraint() -> None:
    """Verify RETRY is blocked when attempt_count >= max_retries."""
    config = PolicyConfiguration(max_retries=3)
    engine = PolicyEligibilityEngine(config)

    rec_ok = _make_dummy_input(attempt_count=2)
    assert (
        engine.evaluate_action_eligibility(rec_ok, RecoveryAction.RETRY).is_eligible
        is True
    )

    rec_limit = _make_dummy_input(attempt_count=3)
    elig_limit = engine.evaluate_action_eligibility(rec_limit, RecoveryAction.RETRY)
    assert elig_limit.is_eligible is False
    assert elig_limit.policy_rule == "RULE_H7_MAX_RETRY_LIMIT"


def test_diagnosis_retry_restriction() -> None:
    """Verify RETRY is blocked for customer-side and payment method failures."""
    engine = PolicyEligibilityEngine()
    rec = _make_dummy_input()

    diag_customer = DiagnosisResult(
        prediction_id="diag_01",
        record_id="rec_test_001",
        scenario_id="sc_test_001",
        model_name="DiagModel",
        model_version="v1.0",
        dataset_version="train-test-v1",
        feature_schema_version="feature-schema-v1",
        predicted_category=DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
        class_probabilities=dict.fromkeys(DiagnosisCategory, 0.1),
        confidence=0.85,
        uncertainty_state=UncertaintyState.HIGH_CONFIDENCE,
    )
    elig = engine.evaluate_action_eligibility(
        rec, RecoveryAction.RETRY, diagnosis_result=diag_customer
    )
    assert elig.is_eligible is False
    assert elig.policy_rule == "RULE_DIAGNOSIS_RETRY_RESTRICTION"

    # Other actions remain eligible
    assert (
        engine.evaluate_action_eligibility(
            rec, RecoveryAction.PAYMENT_LINK, diagnosis_result=diag_customer
        ).is_eligible
        is True
    )


def test_high_value_transaction_guardrail() -> None:
    """Verify high-value transactions block aggressive automated retries."""
    config = PolicyConfiguration(high_value_threshold=10000000)  # Rs 1,00,000
    engine = PolicyEligibilityEngine(config)

    rec_high = _make_dummy_input(amount=15000000)  # Rs 1,50,000
    elig_retry = engine.evaluate_action_eligibility(rec_high, RecoveryAction.RETRY)
    assert elig_retry.is_eligible is False
    assert elig_retry.policy_rule == "RULE_H11_HIGH_VALUE_THRESHOLD"

    elig_outreach = engine.evaluate_action_eligibility(
        rec_high, RecoveryAction.OUTREACH
    )
    assert elig_outreach.is_eligible is False
    assert elig_outreach.policy_rule == "RULE_H11_HIGH_VALUE_THRESHOLD"


def test_low_value_outreach_restriction() -> None:
    """Verify low-value transactions block expensive customer outreach."""
    config = PolicyConfiguration(min_outreach_amount=50000)  # Rs 500
    engine = PolicyEligibilityEngine(config)

    rec_low = _make_dummy_input(amount=20000)  # Rs 200
    elig_outreach = engine.evaluate_action_eligibility(rec_low, RecoveryAction.OUTREACH)
    assert elig_outreach.is_eligible is False
    assert elig_outreach.policy_rule == "RULE_LOW_VALUE_OUTREACH_RESTRICTION"
