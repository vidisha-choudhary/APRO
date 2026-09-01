"""Unit tests for bit-for-bit decision reproducibility."""

from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.enums import RecoveryAction
from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    PredictionUncertaintyState,
)
from apro.recovery_prediction.models import OutcomePrediction
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedPaymentMethod,
)


def _make_dummy_input() -> ModelInputRecord:
    feats = FeatureSnapshot(
        decision_timestamp="2026-09-01T00:00:00Z",
        payment_id="pay_test_001",
        payment_amount=500000,
        currency="INR",
        payment_method=SimulatedPaymentMethod.CARD,
        attempt_count=1,
        failure_reason="insufficient_funds",
        failure_code="BAD_REQUEST",
        customer_id="cust_001",
        previous_payment_count=2,
        previous_success_count=1,
        previous_failure_count=1,
        previous_recovery_count=0,
        previous_retry_success=0,
        previous_payment_link_success=0,
        hour_of_day=10,
        day_of_week=2,
        is_weekend=False,
        candidate_actions=list(SimulatedActionType),
    )
    return ModelInputRecord(
        record_id="rec_rep_001",
        dataset_type=DatasetType.TRAINING,
        dataset_version="train-test-v1",
        scenario_id="sc_rep_001",
        generation_seed=42,
        scenario_version="scenario-v1",
        configuration_version="config-v1",
        feature_schema_version="feature-schema-v1",
        features=feats,
    )


def _make_predictions() -> dict[RecoveryAction, OutcomePrediction]:
    probs = {
        RecoveryAction.RETRY: 0.80,
        RecoveryAction.PAYMENT_LINK: 0.50,
        RecoveryAction.OUTREACH: 0.30,
        RecoveryAction.STOP: 0.0,
        RecoveryAction.ESCALATE: 0.10,
    }
    preds: dict[RecoveryAction, OutcomePrediction] = {}
    for act, p in probs.items():
        preds[act] = OutcomePrediction(
            prediction_id=f"pred_{act.value.lower()}",
            record_id="rec_rep_001",
            scenario_id="sc_rep_001",
            action=act,
            model_name="OutcomeModel",
            model_version="v1.0",
            dataset_version="train-test-v1",
            feature_schema_version="feature-schema-v1",
            predicted_success_probability=p,
            predicted_outcome_state=(
                PredictedOutcomeState.SUCCESS
                if p >= 0.5
                else PredictedOutcomeState.FAILURE
            ),
            predicted_recovered_amount=int(round(p * 500000)),
            confidence=max(p, 1.0 - p),
            uncertainty_state=PredictionUncertaintyState.HIGH_CONFIDENCE,
        )
    return preds


def test_bit_for_bit_reproducibility() -> None:
    """Verify decision runs on frozen inputs yield identical RecoveryDecision."""
    engine = EconomicDecisionEngine()
    rec = _make_dummy_input()
    preds = _make_predictions()

    dec1 = engine.decide(
        model_input=rec, diagnosis_result=None, outcome_predictions=preds
    )
    dec2 = engine.decide(
        model_input=rec, diagnosis_result=None, outcome_predictions=preds
    )

    assert dec1.decision_id == dec2.decision_id
    assert dec1.selected_action == dec2.selected_action
    assert dec1.decision_status == dec2.decision_status
    assert dec1.expected_recovery_value == dec2.expected_recovery_value
    assert dec1.expected_gross_recovery == dec2.expected_gross_recovery
    assert dec1.expected_cost == dec2.expected_cost
    assert dec1.decision_confidence == dec2.decision_confidence
    assert dec1.rationale == dec2.rationale
