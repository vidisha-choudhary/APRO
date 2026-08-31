"""Unit tests for Phase 8 evaluation under governed distribution shift."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.recovery_prediction.classifiers import (
    DecisionTreeOutcomeModel,
)
from apro.recovery_prediction.evaluation import RecoveryOutcomeEvaluator


def test_distribution_shift_evaluation() -> None:
    """AC-18: Test Model B evaluation against shifted benchmark distribution."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-shift-v1", [42], 30)
    test_ds = gen.generate_dataset(
        DatasetType.HELD_OUT_TEST, "test-shift-v1", [101], 15
    )
    shifted_bench_ds = gen.generate_dataset(
        DatasetType.BENCHMARK, "bench-shift-v1", [999], 15
    )

    model = DecisionTreeOutcomeModel(max_depth=5)
    model.fit_on_dataset(train_ds)

    evaluator = RecoveryOutcomeEvaluator()
    in_metrics, _ = evaluator.evaluate_model(model, test_ds)
    shifted_metrics, _ = evaluator.evaluate_model(model, shifted_bench_ds)

    comparison = evaluator.compare_distribution_shift(in_metrics, shifted_metrics)

    assert "in_distribution" in comparison
    assert "shifted_distribution" in comparison
    assert "deltas" in comparison
    assert "macro_f1_delta" in comparison["deltas"]
    assert "accuracy_delta" in comparison["deltas"]
    assert "mae_delta" in comparison["deltas"]
    assert "oracle_gap_delta" in comparison["deltas"]
