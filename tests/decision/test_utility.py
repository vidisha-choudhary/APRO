"""Unit tests for utility calculator and strict recovery bounds validation."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.decision.economics import EconomicConfiguration
from apro.decision.enums import RecoveryAction
from apro.decision.models import ActionEligibility
from apro.decision.utility import UtilityCalculator
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


def test_utility_calculator_bounds_validation() -> None:
    """Verify out-of-bound amounts raise explicit ValueError."""
    calc = UtilityCalculator()
    rec = _make_dummy_input(amount=500000)
    econ = EconomicConfiguration()
    elig = ActionEligibility(action=RecoveryAction.RETRY, is_eligible=True)

    # Invalid recovered amount > payment_amount (exceeds 500000)
    pred_invalid_v = OutcomePrediction(
        prediction_id="p02",
        record_id="rec_test_001",
        scenario_id="sc_test_001",
        action=RecoveryAction.RETRY,
        model_name="TestModel",
        model_version="v1.0",
        dataset_version="train-test-v1",
        feature_schema_version="feature-schema-v1",
        predicted_success_probability=0.80,
        predicted_outcome_state=PredictedOutcomeState.SUCCESS,
        predicted_recovered_amount=600000,
        confidence=0.80,
        uncertainty_state=PredictionUncertaintyState.HIGH_CONFIDENCE,
    )
    with pytest.raises(ValueError, match="Invalid predicted recovered amount"):
        calc.compute_action_utility(
            rec, RecoveryAction.RETRY, pred_invalid_v, elig, econ
        )


def test_utility_calculator_full_decomposition() -> None:
    """Verify correct calculation of ActionUtility fields and cost components."""
    calc = UtilityCalculator()
    rec = _make_dummy_input(amount=500000)
    econ = EconomicConfiguration()
    elig = ActionEligibility(action=RecoveryAction.RETRY, is_eligible=True)

    pred = OutcomePrediction(
        prediction_id="p03",
        record_id="rec_test_001",
        scenario_id="sc_test_001",
        action=RecoveryAction.RETRY,
        model_name="TestModel",
        model_version="v1.0",
        dataset_version="train-test-v1",
        feature_schema_version="feature-schema-v1",
        predicted_success_probability=0.75,
        predicted_outcome_state=PredictedOutcomeState.SUCCESS,
        predicted_recovered_amount=500000,
        confidence=0.75,
        uncertainty_state=PredictionUncertaintyState.HIGH_CONFIDENCE,
    )
    u = calc.compute_action_utility(rec, RecoveryAction.RETRY, pred, elig, econ)

    assert u.action == RecoveryAction.RETRY
    assert u.eligible is True
    assert u.predicted_success_probability == 0.75
    assert u.predicted_recovered_amount == 500000
    assert u.expected_gross_recovery == int(round(0.75 * 500000))  # 375000
    assert u.action_cost == 500
    assert u.operational_cost == 200
    assert u.customer_friction_cost == 300
    assert u.risk_penalty == 200
    assert u.total_cost == 1200
    assert u.expected_recovery_value == 375000 - 1200
