"""Unit tests for Phase 10 benchmark policy evaluation and segment compliance."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.dataset.models import GovernedDataset
from apro.diagnosis.classifiers.decision_tree import DecisionTreeDiagnosisModel
from apro.policy.config import PolicyConfig
from apro.policy.engine import PolicyEngine
from apro.policy.evaluation import (
    evaluate_policy_on_dataset,
    evaluate_policy_segments,
)
from apro.recovery_prediction.classifiers.logistic import (
    LogisticRegressionOutcomeModel,
)


def _generate_test_dataset(
    dataset_type: DatasetType = DatasetType.BENCHMARK,
    seed: int = 42,
    count: int = 25,
) -> GovernedDataset:
    gen = DatasetGenerator()
    return gen.generate_dataset(
        dataset_type=dataset_type,
        dataset_version=f"{dataset_type.value.lower()}-test-v1",
        seeds=[seed],
        cases_per_seed=count,
    )


def test_evaluate_policy_on_benchmark_dataset():
    """Verify policy evaluation over benchmark scenarios produces
    zero constraint violations.
    """
    train_ds = _generate_test_dataset(
        dataset_type=DatasetType.TRAINING, seed=42, count=30
    )
    test_ds = _generate_test_dataset(
        dataset_type=DatasetType.BENCHMARK, seed=43, count=30
    )

    # Fit Model A & B on TRAINING dataset
    diag_model = DecisionTreeDiagnosisModel(max_depth=4)
    diag_model.fit_on_dataset(train_ds)

    outcome_model = LogisticRegressionOutcomeModel(max_iter=50)
    outcome_model.fit_on_dataset(train_ds, diagnosis_model=diag_model)

    engine = PolicyEngine()
    cfg = PolicyConfig()

    metrics, decisions, traces = evaluate_policy_on_dataset(
        dataset=test_ds,
        engine=engine,
        config=cfg,
        diagnosis_model=diag_model,
        outcome_model=outcome_model,
    )

    assert metrics.total_evaluations == 30
    assert len(decisions) == 30
    assert len(traces) == 30
    assert metrics.constraint_violation_count == 0
    assert (
        metrics.allow_count + metrics.block_count + metrics.require_human_approval_count
        == 30
    )
    assert 0.0 <= metrics.allow_rate <= 1.0
    assert 0.0 <= metrics.block_rate <= 1.0


def test_evaluate_policy_segments():
    """Verify segment evaluation across scenario families and payment methods."""
    train_ds = _generate_test_dataset(
        dataset_type=DatasetType.TRAINING, seed=44, count=30
    )
    test_ds = _generate_test_dataset(
        dataset_type=DatasetType.BENCHMARK, seed=45, count=25
    )

    diag_model = DecisionTreeDiagnosisModel(max_depth=4)
    diag_model.fit_on_dataset(train_ds)

    outcome_model = LogisticRegressionOutcomeModel(max_iter=50)
    outcome_model.fit_on_dataset(train_ds, diagnosis_model=diag_model)

    metrics, decisions, _ = evaluate_policy_on_dataset(
        dataset=test_ds,
        diagnosis_model=diag_model,
        outcome_model=outcome_model,
    )

    segments = evaluate_policy_segments(test_ds, decisions)
    assert len(segments) > 0
    for _seg_key, seg_data in segments.items():
        assert (
            seg_data["count"]
            == seg_data["allow"] + seg_data["block"] + seg_data["require_approval"]
        )
