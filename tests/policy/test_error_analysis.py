"""Unit tests for Phase 10 evaluator-side policy error analysis."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.classifiers.decision_tree import DecisionTreeDiagnosisModel
from apro.policy.evaluation import (
    PolicyErrorAnalysisReport,
    evaluate_policy_on_dataset,
    perform_policy_error_analysis,
)
from apro.recovery_prediction.classifiers.logistic import (
    LogisticRegressionOutcomeModel,
)


def test_perform_policy_error_analysis_on_benchmark_dataset():
    """Verify evaluator-side error analysis generates comprehensive
    diagnostics across all 8 required categories.
    """
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(
        dataset_type=DatasetType.TRAINING,
        dataset_version="train-err-v1",
        seeds=[101],
        cases_per_seed=25,
    )
    eval_ds = gen.generate_dataset(
        dataset_type=DatasetType.BENCHMARK,
        dataset_version="benchmark-err-v1",
        seeds=[102],
        cases_per_seed=25,
    )

    diag_model = DecisionTreeDiagnosisModel(max_depth=4)
    diag_model.fit_on_dataset(train_ds)

    outcome_model = LogisticRegressionOutcomeModel(max_iter=50)
    outcome_model.fit_on_dataset(train_ds, diagnosis_model=diag_model)

    _metrics, decisions, traces = evaluate_policy_on_dataset(
        dataset=eval_ds,
        diagnosis_model=diag_model,
        outcome_model=outcome_model,
    )

    report = perform_policy_error_analysis(
        dataset=eval_ds,
        decisions=decisions,
        policy_decisions=decisions,
        traces=traces,
    )

    assert isinstance(report, PolicyErrorAnalysisReport)
    assert report.total_cases_analyzed == 25
    assert len(report.wrong_policy_outcomes) == 0
    assert len(report.negative_utility_incorrectly_permitted) == 0
    assert isinstance(report.near_threshold_decisions, list)
    assert isinstance(report.policy_filtered_selections, list)
    assert isinstance(report.stale_state_protections, list)
    assert isinstance(report.model_failure_protections, list)
    assert isinstance(report.shift_sensitive_cases, list)


def test_error_analysis_zero_simulator_truth_leakage():
    """Verify error analysis report does not leak latent simulator fields."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(
        dataset_type=DatasetType.TRAINING,
        dataset_version="train-leak-v1",
        seeds=[103],
        cases_per_seed=15,
    )
    eval_ds = gen.generate_dataset(
        dataset_type=DatasetType.BENCHMARK,
        dataset_version="benchmark-leak-v1",
        seeds=[104],
        cases_per_seed=10,
    )

    diag_model = DecisionTreeDiagnosisModel(max_depth=4)
    diag_model.fit_on_dataset(train_ds)

    outcome_model = LogisticRegressionOutcomeModel(max_iter=50)
    outcome_model.fit_on_dataset(train_ds, diagnosis_model=diag_model)

    _metrics, decisions, traces = evaluate_policy_on_dataset(
        dataset=eval_ds,
        diagnosis_model=diag_model,
        outcome_model=outcome_model,
    )
    report = perform_policy_error_analysis(
        dataset=eval_ds,
        decisions=decisions,
        policy_decisions=decisions,
        traces=traces,
    )

    report_dict = report.model_dump()
    forbidden_terms = (
        "potential_outcomes",
        "oracle_action",
        "latent_state",
        "hidden_failure_cause",
    )
    for term in forbidden_terms:
        assert term not in str(report_dict)
