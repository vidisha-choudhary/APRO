"""Unit tests for Phase 10 distribution-shift policy governance robustness."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.dataset.models import GovernedDataset
from apro.diagnosis.classifiers.decision_tree import DecisionTreeDiagnosisModel
from apro.policy.config import PolicyConfig
from apro.policy.engine import PolicyEngine
from apro.policy.evaluation import (
    compare_distribution_shift,
    evaluate_policy_on_dataset,
)
from apro.recovery_prediction.classifiers.logistic import (
    LogisticRegressionOutcomeModel,
)


def _generate_dataset(
    dataset_type: DatasetType, seed: int, count: int
) -> GovernedDataset:
    gen = DatasetGenerator()
    return gen.generate_dataset(
        dataset_type=dataset_type,
        dataset_version=f"{dataset_type.value.lower()}-v1",
        seeds=[seed],
        cases_per_seed=count,
    )


def test_distribution_shift_comparison():
    """Verify policy engine maintains zero constraint violations
    and computes complete distribution-shift comparison.
    """
    train_ds = _generate_dataset(DatasetType.TRAINING, seed=42, count=30)
    in_dist_dataset = _generate_dataset(DatasetType.BENCHMARK, seed=43, count=25)
    shift_dataset = _generate_dataset(DatasetType.HELD_OUT_TEST, seed=99, count=25)

    diag_model = DecisionTreeDiagnosisModel(max_depth=4)
    diag_model.fit_on_dataset(train_ds)

    outcome_model = LogisticRegressionOutcomeModel(max_iter=50)
    outcome_model.fit_on_dataset(train_ds, diagnosis_model=diag_model)

    engine = PolicyEngine()
    cfg = PolicyConfig()

    in_metrics, _, _ = evaluate_policy_on_dataset(
        in_dist_dataset,
        engine,
        cfg,
        diagnosis_model=diag_model,
        outcome_model=outcome_model,
    )
    shift_metrics, _, _ = evaluate_policy_on_dataset(
        shift_dataset,
        engine,
        cfg,
        diagnosis_model=diag_model,
        outcome_model=outcome_model,
    )

    assert in_metrics.constraint_violation_count == 0
    assert shift_metrics.constraint_violation_count == 0

    comp = compare_distribution_shift(in_metrics, shift_metrics)
    assert "in_distribution" in comp
    assert "distribution_shift" in comp
    assert "delta" in comp

    # Verify all required distribution-shift comparison fields
    in_d = comp["in_distribution"]
    shift_d = comp["distribution_shift"]
    delta_d = comp["delta"]

    for d in (in_d, shift_d):
        assert "allow_rate" in d
        assert "block_rate" in d
        assert "require_human_approval_rate" in d
        assert "constraint_violations" in d
        assert "captured_payment_blocks" in d
        assert "invalid_output_blocks" in d
        assert "reconciliation_rate" in d
        assert "ineligible_selection_rate" in d
        assert "action_distribution_after_policy" in d
        assert "safety_counters" in d

    assert "allow_rate_delta" in delta_d
    assert "block_rate_delta" in delta_d
    assert "approval_rate_delta" in delta_d
    assert "constraint_violations_delta" in delta_d
    assert "captured_payment_blocks_delta" in delta_d
    assert "invalid_output_blocks_delta" in delta_d
    assert "reconciliation_rate_delta" in delta_d
