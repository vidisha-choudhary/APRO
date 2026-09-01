"""Unit tests for the Economic Decision Engine, tie-breaking, and threshold logic."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.decision.economics import EconomicConfiguration
from apro.decision.eligibility import PolicyConfiguration
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.enums import (
    DecisionStatus,
    RecoveryAction,
)
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
    amount: int = 500000,
) -> dict[RecoveryAction, OutcomePrediction]:
    preds: dict[RecoveryAction, OutcomePrediction] = {}
    for act, p in probs.items():
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
            predicted_recovered_amount=amount if p > 0.0 else 0,
            confidence=max(p, 1.0 - p),
            uncertainty_state=PredictionUncertaintyState.HIGH_CONFIDENCE,
        )
    return preds


def test_decision_engine_clear_winner() -> None:
    """Verify engine selects clear highest ERV action."""
    engine = EconomicDecisionEngine()
    rec = _make_dummy_input(amount=500000)
    preds = _make_predictions(
        {
            RecoveryAction.RETRY: 0.85,  # gross=425000, cost=1200 -> ERV=423800
            RecoveryAction.PAYMENT_LINK: 0.50,  # gross=250000, cost=3500 -> ERV=246500
            RecoveryAction.OUTREACH: 0.40,  # gross=200000, cost=11000 -> ERV=189000
            RecoveryAction.STOP: 0.0,  # ERV=0
            RecoveryAction.ESCALATE: 0.10,  # gross=50000, cost=8000 -> ERV=42000
        }
    )

    dec = engine.decide(
        model_input=rec, diagnosis_result=None, outcome_predictions=preds
    )
    assert dec.decision_status == DecisionStatus.ACTION_SELECTED
    assert dec.selected_action == RecoveryAction.RETRY
    assert dec.expected_recovery_value == 423800
    assert dec.expected_gross_recovery == 425000
    assert dec.expected_cost == 1200


def test_economic_tradeoff_highest_prob_vs_highest_erv() -> None:
    """Verify engine selects higher ERV when costs flip simple probability ranking."""
    engine = EconomicDecisionEngine()
    rec = _make_dummy_input(amount=10000)  # Rs 100.00 = 10,000 paise
    preds = _make_predictions(
        {
            RecoveryAction.RETRY: 0.70,
            RecoveryAction.PAYMENT_LINK: 0.60,
            RecoveryAction.OUTREACH: 0.90,  # higher prob but net negative ERV
            RecoveryAction.STOP: 0.0,
            RecoveryAction.ESCALATE: 0.0,
        },
        amount=10000,
    )

    dec = engine.decide(
        model_input=rec, diagnosis_result=None, outcome_predictions=preds
    )
    assert dec.selected_action == RecoveryAction.RETRY
    assert dec.expected_recovery_value == 7000 - 1200


def test_negative_utility_threshold() -> None:
    """Verify engine returns NO_POSITIVE_UTILITY when all actions fail threshold."""
    econ = EconomicConfiguration(minimum_expected_recovery_value=1000)  # Rs 10
    engine = EconomicDecisionEngine(economic_config=econ)
    rec = _make_dummy_input(amount=1000)  # Rs 10.00
    preds = _make_predictions(
        {
            RecoveryAction.RETRY: 0.05,  # gross=50, cost=1200 -> ERV=-1150
            RecoveryAction.PAYMENT_LINK: 0.05,
            RecoveryAction.OUTREACH: 0.05,
            RecoveryAction.STOP: 0.0,  # ERV=0 < 1000 threshold
            RecoveryAction.ESCALATE: 0.0,
        },
        amount=1000,
    )

    dec = engine.decide(
        model_input=rec, diagnosis_result=None, outcome_predictions=preds
    )
    assert dec.decision_status == DecisionStatus.NO_POSITIVE_UTILITY
    assert dec.selected_action is None


def test_deterministic_tie_breaking() -> None:
    """Verify deterministic tie-breaking order (STOP > ESCALATE > RETRY ...)."""
    engine = EconomicDecisionEngine()
    rec = _make_dummy_input(amount=10000)
    preds = _make_predictions(
        {
            RecoveryAction.RETRY: 0.0,
            RecoveryAction.PAYMENT_LINK: 0.0,
            RecoveryAction.OUTREACH: 0.0,
            RecoveryAction.STOP: 0.0,
            RecoveryAction.ESCALATE: 0.0,
        },
        amount=10000,
    )

    dec = engine.decide(
        model_input=rec, diagnosis_result=None, outcome_predictions=preds
    )
    assert dec.decision_status == DecisionStatus.ACTION_SELECTED
    assert dec.selected_action == RecoveryAction.STOP


def test_schema_and_version_compatibility_validation() -> None:
    """Verify engine strictly validates version and schema compatibility."""
    engine = EconomicDecisionEngine()
    rec = _make_dummy_input()
    preds = _make_predictions(dict.fromkeys(RecoveryAction, 0.5))

    # 1. Missing action in outcome_predictions
    incomplete_preds = {RecoveryAction.STOP: preds[RecoveryAction.STOP]}
    with pytest.raises(
        ValueError, match="Missing Model B outcome prediction for action"
    ):
        engine.decide(rec, None, incomplete_preds)

    # 2. Action schema version mismatch
    bad_action_schema_preds = dict(preds)
    bad_action_schema_preds[RecoveryAction.RETRY] = preds[
        RecoveryAction.RETRY
    ].model_copy(update={"action_schema_version": "bad-action-v99"})
    with pytest.raises(ValueError, match="Incompatible action schema version"):
        engine.decide(rec, None, bad_action_schema_preds)

    # 3. Feature schema version mismatch
    bad_feat_schema_preds = dict(preds)
    bad_feat_schema_preds[RecoveryAction.RETRY] = preds[
        RecoveryAction.RETRY
    ].model_copy(update={"feature_schema_version": "bad-feat-v99"})
    with pytest.raises(
        ValueError,
        match="Incompatible outcome prediction feature schema version",
    ):
        engine.decide(rec, None, bad_feat_schema_preds)

    # 4. Dataset version mismatch
    bad_ds_preds = dict(preds)
    bad_ds_preds[RecoveryAction.RETRY] = preds[RecoveryAction.RETRY].model_copy(
        update={"dataset_version": "mismatched-ds-v99"}
    )
    with pytest.raises(ValueError, match="Dataset version mismatch"):
        engine.decide(rec, None, bad_ds_preds)

    # 5. Diagnosis taxonomy version mismatch
    diag_bad = DiagnosisResult(
        prediction_id="d1",
        record_id="rec_test_001",
        scenario_id="sc_test_001",
        model_name="DiagModel",
        model_version="v1.0",
        dataset_version="train-test-v1",
        feature_schema_version="feature-schema-v1",
        taxonomy_version="bad-diag-tax-v99",
        predicted_category=DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
        class_probabilities=dict.fromkeys(DiagnosisCategory, 0.1),
        confidence=0.90,
        uncertainty_state=UncertaintyState.HIGH_CONFIDENCE,
    )
    with pytest.raises(ValueError, match="Incompatible diagnosis taxonomy version"):
        engine.decide(rec, diag_bad, preds)

    # 6. Policy config version mismatch on engine init
    bad_policy_cfg = PolicyConfiguration(policy_version="bad-policy-v99")
    with pytest.raises(ValueError, match="Incompatible policy config version"):
        EconomicDecisionEngine(policy_config=bad_policy_cfg)

    # 7. Economic config version mismatch on engine init
    bad_econ_cfg = EconomicConfiguration(config_version="bad-econ-v99")
    with pytest.raises(ValueError, match="Incompatible economic config version"):
        EconomicDecisionEngine(economic_config=bad_econ_cfg)
