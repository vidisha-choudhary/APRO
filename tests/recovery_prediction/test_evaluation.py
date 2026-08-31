"""Unit tests for Phase 8 evaluation runner and candidate selection."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.recovery_prediction.classifiers import (
    DecisionTreeOutcomeModel,
    LogisticRegressionOutcomeModel,
)
from apro.recovery_prediction.evaluation import (
    RecoveryOutcomeEvaluator,
    select_best_candidate,
)


def test_evaluator_workflow_and_segments() -> None:
    """AC-15, AC-17, AC-19: Test evaluation workflow, segments, and error analysis."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-eval-b-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-eval-b-v1", [101], 15)

    model = LogisticRegressionOutcomeModel(max_iter=30)
    model.fit_on_dataset(train_ds)

    evaluator = RecoveryOutcomeEvaluator()
    metrics, traces = evaluator.evaluate_model(model, val_ds)

    assert metrics.case_count == 75  # 15 scenarios * 5 actions
    assert metrics.scenario_count == 15
    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.macro_f1 <= 1.0
    assert len(traces) == 75

    # Test segment evaluation across 5 dimensions
    segments = evaluator.evaluate_segments(traces)
    assert "action" in segments
    assert "scenario_family" in segments
    assert "payment_method" in segments
    assert "payment_value_tier" in segments
    assert "scenario_difficulty" in segments

    # Test error analysis
    err_analysis = evaluator.perform_error_analysis(traces)
    assert "total_cases" in err_analysis
    assert "total_errors" in err_analysis
    assert "high_confidence_wrong_count" in err_analysis
    assert "action_error_breakdown" in err_analysis


def test_select_best_candidate() -> None:
    """AC-20: Test model selection rule on primary metric with tie breaker."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-sel-b-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-sel-b-v1", [101], 15)

    m1 = LogisticRegressionOutcomeModel(max_iter=20)
    m1.fit_on_dataset(train_ds)

    m2 = DecisionTreeOutcomeModel(max_depth=4)
    m2.fit_on_dataset(train_ds)

    evaluator = RecoveryOutcomeEvaluator()
    met1, _ = evaluator.evaluate_model(m1, val_ds)
    met2, _ = evaluator.evaluate_model(m2, val_ds)

    candidates = {m1.model_name: met1, m2.model_name: met2}
    best_name, rationale = select_best_candidate(
        candidates, primary_metric="macro_f1", tie_breaker_metric="log_loss"
    )

    assert best_name in (m1.model_name, m2.model_name)
    assert "Selected" in rationale
    assert "primary_metric='macro_f1'" in rationale
