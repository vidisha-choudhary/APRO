"""Unit tests for decision sensitivity analysis across all 5 dimensions."""

from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.enums import RecoveryAction
from apro.decision.sensitivity import DecisionSensitivityAnalyzer
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


def test_sensitivity_analysis_robust_winner() -> None:
    """Verify clearly dominant decision remains stable under perturbations."""
    engine = EconomicDecisionEngine()
    analyzer = DecisionSensitivityAnalyzer(engine)
    rec = _make_dummy_input()

    # Clear winner: RETRY with high probability
    preds = _make_predictions(
        {
            RecoveryAction.RETRY: 0.95,
            RecoveryAction.PAYMENT_LINK: 0.20,
            RecoveryAction.OUTREACH: 0.10,
            RecoveryAction.STOP: 0.0,
            RecoveryAction.ESCALATE: 0.05,
        }
    )

    result = analyzer.analyze(rec, diagnosis_result=None, outcome_predictions=preds)
    assert result.baseline_action == RecoveryAction.RETRY
    assert result.is_stable is True

    dims = {p.dimension for p in result.perturbations}
    expected_dims = {
        "predicted_success_probability",
        "predicted_recovered_amount",
        "action_cost",
        "risk_penalty",
        "minimum_utility_threshold",
    }
    assert dims == expected_dims


def test_sensitivity_analysis_detects_switch() -> None:
    """Verify analyzer detects action switch when candidate margins are close."""
    engine = EconomicDecisionEngine()
    analyzer = DecisionSensitivityAnalyzer(engine)
    rec = _make_dummy_input(amount=10000)

    # Close margin between RETRY and PAYMENT_LINK
    # RETRY ERV = 0.50 * 10000 - 1200 = 3800
    # PAYMENT_LINK ERV = 0.70 * 10000 - 3500 = 3500
    preds = _make_predictions(
        {
            RecoveryAction.RETRY: 0.50,
            RecoveryAction.PAYMENT_LINK: 0.70,
            RecoveryAction.OUTREACH: 0.10,
            RecoveryAction.STOP: 0.0,
            RecoveryAction.ESCALATE: 0.0,
        },
        amounts={
            RecoveryAction.RETRY: 10000,
            RecoveryAction.PAYMENT_LINK: 10000,
            RecoveryAction.OUTREACH: 10000,
            RecoveryAction.STOP: 0,
            RecoveryAction.ESCALATE: 0,
        },
    )

    result = analyzer.analyze(rec, diagnosis_result=None, outcome_predictions=preds)
    assert result.baseline_action == RecoveryAction.RETRY
    # A negative perturbation on RETRY probability should switch to PAYMENT_LINK
    switches = [p for p in result.perturbations if p.is_action_switched]
    assert len(switches) > 0
    assert result.is_stable is False
