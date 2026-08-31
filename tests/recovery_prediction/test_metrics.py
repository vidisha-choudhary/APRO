"""Unit tests for Phase 8 recovery outcome prediction evaluation metrics."""

from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    PredictionUncertaintyState,
    RecoveryAction,
)
from apro.recovery_prediction.metrics import (
    calculate_recovery_outcome_metrics,
)
from apro.recovery_prediction.traces import RecoveryPredictionTrace


def test_empty_traces_metrics() -> None:
    """AC-15: Test metric calculations on empty trace list."""
    metrics = calculate_recovery_outcome_metrics([])
    assert metrics.case_count == 0
    assert metrics.accuracy == 0.0
    assert metrics.macro_f1 == 0.0
    assert metrics.potential_outcome_metrics.oracle_gap == 0.0


def test_recovery_outcome_metrics_calculation() -> None:
    """AC-15, AC-16: Test metrics calculation on synthetic traces."""
    traces = [
        # Scenario 1 - RETRY succeeds (Actual: 5000, Pred: 5000)
        RecoveryPredictionTrace(
            prediction_id="p1",
            record_id="r1",
            scenario_id="s1",
            action=RecoveryAction.RETRY,
            dataset_version="d1",
            feature_schema_version="f1",
            action_schema_version="a1",
            diagnosis_model_version="diag1",
            model_version="v1",
            predicted_success_probability=0.85,
            predicted_outcome_state=PredictedOutcomeState.SUCCESS,
            predicted_recovered_amount=5000,
            confidence=0.85,
            uncertainty_state=PredictionUncertaintyState.HIGH_CONFIDENCE,
            actual_outcome_state=PredictedOutcomeState.SUCCESS,
            actual_recovered_amount=5000,
            is_correct_outcome=True,
            amount_error=0,
            scenario_family="PSP_OUTAGE",
            payment_method="card",
            payment_value_tier="LOW_VALUE",
            scenario_difficulty="EASY",
            decision_latency_ms=1.0,
        ),
        # Scenario 1 - STOP fails (Actual: 0, Pred: 0)
        RecoveryPredictionTrace(
            prediction_id="p2",
            record_id="r1",
            scenario_id="s1",
            action=RecoveryAction.STOP,
            dataset_version="d1",
            feature_schema_version="f1",
            action_schema_version="a1",
            diagnosis_model_version="diag1",
            model_version="v1",
            predicted_success_probability=0.0,
            predicted_outcome_state=PredictedOutcomeState.FAILURE,
            predicted_recovered_amount=0,
            confidence=1.0,
            uncertainty_state=PredictionUncertaintyState.HIGH_CONFIDENCE,
            actual_outcome_state=PredictedOutcomeState.FAILURE,
            actual_recovered_amount=0,
            is_correct_outcome=True,
            amount_error=0,
            scenario_family="PSP_OUTAGE",
            payment_method="card",
            payment_value_tier="LOW_VALUE",
            scenario_difficulty="EASY",
            decision_latency_ms=0.5,
        ),
    ]

    best_values = {"s1": 5000}
    metrics = calculate_recovery_outcome_metrics(
        traces, best_achievable_values=best_values
    )

    assert metrics.case_count == 2
    assert metrics.scenario_count == 1
    assert metrics.accuracy == 1.0
    assert metrics.macro_f1 == 1.0
    assert metrics.mae == 0.0
    assert metrics.potential_outcome_metrics.oracle_gap == 0.0
    assert metrics.potential_outcome_metrics.counterfactual_regret == 0.0
