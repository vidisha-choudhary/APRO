"""Unit tests for the 4 reference baseline decision strategies."""

from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.decision.baselines import (
    HighestRecoveryAmountBaseline,
    HighestSuccessProbabilityBaseline,
    NoInterventionBaseline,
    StaticActionRuleBaseline,
)
from apro.decision.enums import DecisionStatus, RecoveryAction
from apro.diagnosis.enums import DiagnosisCategory, UncertaintyState
from apro.diagnosis.models import DiagnosisResult
from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    PredictionUncertaintyState,
)
from apro.recovery_prediction.models import OutcomePrediction
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedPaymentMethod,
)


def _make_dummy_input(amount: int = 500000) -> ModelInputRecord:
    feats = FeatureSnapshot(
        decision_timestamp="2026-09-01T00:00:00Z",
        payment_id="pay_test_001",
        payment_amount=amount,
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


def _make_predictions(
    probs: dict[RecoveryAction, float],
    amounts: dict[RecoveryAction, int] | None = None,
) -> dict[RecoveryAction, OutcomePrediction]:
    preds: dict[RecoveryAction, OutcomePrediction] = {}
    for act, p in probs.items():
        amt = amounts[act] if amounts and act in amounts else int(round(p * 500000))
        preds[act] = OutcomePrediction(
            prediction_id=f"pred_{act.value.lower()}",
            record_id="rec_test_001",
            scenario_id="sc_test_001",
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
            predicted_recovered_amount=amt,
            confidence=max(p, 1.0 - p),
            uncertainty_state=PredictionUncertaintyState.HIGH_CONFIDENCE,
        )
    return preds


def test_no_intervention_baseline() -> None:
    """Verify Baseline 0 always selects STOP."""
    b0 = NoInterventionBaseline()
    rec = _make_dummy_input()
    preds = _make_predictions(dict.fromkeys(RecoveryAction, 0.8))

    dec = b0.decide(rec, diagnosis_result=None, outcome_predictions=preds)
    assert dec.decision_status == DecisionStatus.ACTION_SELECTED
    assert dec.selected_action == RecoveryAction.STOP


def test_highest_success_probability_baseline() -> None:
    """Verify Baseline 1 selects eligible action with highest probability."""
    b1 = HighestSuccessProbabilityBaseline()
    rec = _make_dummy_input()
    preds = _make_predictions(
        {
            RecoveryAction.RETRY: 0.60,
            RecoveryAction.PAYMENT_LINK: 0.95,
            RecoveryAction.OUTREACH: 0.40,
            RecoveryAction.STOP: 0.0,
            RecoveryAction.ESCALATE: 0.10,
        }
    )

    dec = b1.decide(rec, diagnosis_result=None, outcome_predictions=preds)
    assert dec.selected_action == RecoveryAction.PAYMENT_LINK


def test_highest_recovery_amount_baseline() -> None:
    """Verify Baseline 2 selects eligible action with highest predicted amount."""
    b2 = HighestRecoveryAmountBaseline()
    rec = _make_dummy_input()
    preds = _make_predictions(
        probs=dict.fromkeys(RecoveryAction, 0.5),
        amounts={
            RecoveryAction.RETRY: 100000,
            RecoveryAction.PAYMENT_LINK: 400000,
            RecoveryAction.OUTREACH: 200000,
            RecoveryAction.STOP: 0,
            RecoveryAction.ESCALATE: 50000,
        },
    )

    dec = b2.decide(rec, diagnosis_result=None, outcome_predictions=preds)
    assert dec.selected_action == RecoveryAction.PAYMENT_LINK


def test_static_action_rule_baseline() -> None:
    """Verify Baseline 3 executes deterministic context rules."""
    b3 = StaticActionRuleBaseline()
    rec = _make_dummy_input()
    preds = _make_predictions(dict.fromkeys(RecoveryAction, 0.5))

    # Rule 1: Attempt 1 + Card + Unknown diag -> RETRY
    dec = b3.decide(rec, diagnosis_result=None, outcome_predictions=preds)
    assert dec.selected_action == RecoveryAction.RETRY

    # Rule 2: Customer side failure -> PAYMENT_LINK
    diag_cust = DiagnosisResult(
        prediction_id="d1",
        record_id="rec_test_001",
        scenario_id="sc_test_001",
        model_name="DiagModel",
        model_version="v1.0",
        dataset_version="train-test-v1",
        feature_schema_version="feature-schema-v1",
        predicted_category=DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
        class_probabilities=dict.fromkeys(DiagnosisCategory, 0.1),
        confidence=0.90,
        uncertainty_state=UncertaintyState.HIGH_CONFIDENCE,
    )
    dec_cust = b3.decide(rec, diagnosis_result=diag_cust, outcome_predictions=preds)
    assert dec_cust.selected_action == RecoveryAction.PAYMENT_LINK
