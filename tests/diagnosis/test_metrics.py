"""Unit tests for Phase 7 classification and calibration metrics."""

from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DiagnosisCategory,
    UncertaintyState,
)
from apro.diagnosis.metrics import calculate_diagnosis_metrics
from apro.diagnosis.traces import DiagnosisPredictionTrace
from apro.simulation.enums import (
    PaymentValueTier,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedPaymentMethod,
)


def _make_trace(
    pred: DiagnosisCategory,
    actual: DiagnosisCategory,
    conf: float,
    latency: float = 0.5,
) -> DiagnosisPredictionTrace:
    probs = {
        c: (conf if c == pred else (1.0 - conf) / 7.0) for c in DIAGNOSIS_TAXONOMY_ORDER
    }
    return DiagnosisPredictionTrace(
        prediction_id="p1",
        record_id="r1",
        scenario_id="s1",
        dataset_version="d1",
        feature_schema_version="f1",
        taxonomy_version="t1",
        model_name="test_model",
        model_version="v1.0",
        predicted_category=pred,
        class_probabilities=probs,
        confidence=conf,
        uncertainty_state=UncertaintyState.HIGH_CONFIDENCE,
        actual_category=actual,
        is_correct=(pred == actual),
        decision_latency_ms=latency,
        scenario_family=ScenarioFamily.TRANSIENT_FAILURE,
        payment_value_tier=PaymentValueTier.LOW_VALUE,
        payment_method=SimulatedPaymentMethod.UPI,
        scenario_difficulty=ScenarioDifficulty.EASY,
        seed=42,
    )


def test_empty_traces_metrics() -> None:
    """AC-14: Test metrics calculation on empty traces."""
    m = calculate_diagnosis_metrics([])
    assert m.case_count == 0
    assert m.accuracy == 0.0
    assert m.macro_f1 == 0.0
    assert len(m.confusion_matrix) == 8


def test_diagnosis_metrics_calculation_formulas() -> None:
    """AC-14, AC-15: Test metric calculations across mock predictions."""
    traces = [
        # 1. Correct TIMEOUT
        _make_trace(DiagnosisCategory.TIMEOUT, DiagnosisCategory.TIMEOUT, 0.90),
        # 2. Correct BANK_SIDE_FAILURE
        _make_trace(
            DiagnosisCategory.BANK_SIDE_FAILURE,
            DiagnosisCategory.BANK_SIDE_FAILURE,
            0.80,
        ),
        # 3. Wrong: Predicted AUTH, Actual TRANSIENT
        _make_trace(
            DiagnosisCategory.AUTHENTICATION_FAILURE,
            DiagnosisCategory.TRANSIENT_FAILURE,
            0.60,
        ),
        # 4. Correct TRANSIENT
        _make_trace(
            DiagnosisCategory.TRANSIENT_FAILURE,
            DiagnosisCategory.TRANSIENT_FAILURE,
            0.75,
        ),
    ]

    metrics = calculate_diagnosis_metrics(traces)

    assert metrics.case_count == 4
    # 3 correct out of 4 -> Accuracy = 0.75
    assert metrics.accuracy == 0.75
    assert metrics.top_1_accuracy == 0.75
    assert metrics.log_loss > 0.0
    assert metrics.brier_score > 0.0
    assert len(metrics.confusion_matrix) == 8
    assert len(metrics.confusion_matrix[0]) == 8
