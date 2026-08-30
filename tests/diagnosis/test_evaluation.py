"""Unit and integration tests for DiagnosisEvaluator (Phase 7)."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.classifiers import (
    MultinomialLogisticRegressionDiagnosisModel,
)
from apro.diagnosis.enums import DiagnosisCategory
from apro.diagnosis.evaluation import (
    DiagnosisEvaluator,
    select_best_candidate,
)
from apro.diagnosis.metrics import DiagnosisMetrics, PerClassMetric


def test_diagnosis_evaluator_workflow() -> None:
    """AC-16, AC-17: Test full evaluation workflow and error analysis."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-eval-v1", [1, 2], 30)
    test_ds = gen.generate_dataset(DatasetType.HELD_OUT_TEST, "test-eval-v1", [3], 20)

    model = MultinomialLogisticRegressionDiagnosisModel(max_iter=50)
    model.fit_on_dataset(train_ds)

    evaluator = DiagnosisEvaluator()
    metrics, traces = evaluator.evaluate_model(model, test_ds)

    assert metrics.case_count == 20
    assert len(traces) == 20
    assert metrics.accuracy >= 0.0

    # Segments
    segments = evaluator.evaluate_segments(traces)
    assert "scenario_family" in segments
    assert "payment_method" in segments
    assert "payment_value_tier" in segments

    # Error analysis
    err = evaluator.perform_error_analysis(traces)
    assert err["total_cases"] == 20
    assert "error_rate" in err
    assert "high_confidence_wrong_count" in err


def test_select_best_candidate_criteria_and_tie_breaking() -> None:
    """Correction D: Verify model selection uses primary metric and tie-breaker."""
    dummy_per_class = {
        c: PerClassMetric(category=c, precision=1.0, recall=1.0, f1=1.0, support=10)
        for c in DiagnosisCategory
    }

    m_a = DiagnosisMetrics(
        case_count=100,
        accuracy=0.90,
        balanced_accuracy=0.90,
        macro_precision=0.90,
        macro_recall=0.90,
        macro_f1=0.90,
        weighted_f1=0.90,
        log_loss=0.30,
        brier_score=0.10,
        expected_calibration_error=0.05,
        top_1_accuracy=0.90,
        top_2_accuracy=0.95,
        average_decision_latency_ms=0.01,
        per_class=dummy_per_class,
        confusion_matrix=[],
    )

    m_b = DiagnosisMetrics(
        case_count=100,
        accuracy=0.95,
        balanced_accuracy=0.95,
        macro_precision=0.95,
        macro_recall=0.95,
        macro_f1=0.95,
        weighted_f1=0.95,
        log_loss=0.20,
        brier_score=0.08,
        expected_calibration_error=0.04,
        top_1_accuracy=0.95,
        top_2_accuracy=0.98,
        average_decision_latency_ms=0.01,
        per_class=dummy_per_class,
        confusion_matrix=[],
    )

    m_c = DiagnosisMetrics(
        case_count=100,
        accuracy=0.95,
        balanced_accuracy=0.95,
        macro_precision=0.95,
        macro_recall=0.95,
        macro_f1=0.95,  # Same macro_f1 as m_b
        weighted_f1=0.95,
        log_loss=0.15,  # Better (lower) log_loss than m_b
        brier_score=0.06,
        expected_calibration_error=0.03,
        top_1_accuracy=0.95,
        top_2_accuracy=0.98,
        average_decision_latency_ms=0.01,
        per_class=dummy_per_class,
        confusion_matrix=[],
    )

    candidates = {
        "Model A": m_a,
        "Model B": m_b,
        "Model C": m_c,
    }

    # Model C should win: tied with B on macro_f1 (0.95),
    # but has lower log_loss (0.15 vs 0.20)
    best_name, rationale = select_best_candidate(
        candidates, primary_metric="macro_f1", tie_breaker_metric="log_loss"
    )
    assert best_name == "Model C"
    assert "Model C" in rationale
    assert "0.9500" in rationale

    # Empty candidate dict raises ValueError
    with pytest.raises(ValueError, match="empty candidate metrics"):
        select_best_candidate({})
