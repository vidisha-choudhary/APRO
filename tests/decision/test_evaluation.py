"""Unit tests for the decision evaluation engine, metrics, and segments."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.dataset.models import GovernedDataset
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.enums import DecisionStatus, RecoveryAction
from apro.decision.evaluation import (
    EconomicDecisionEvaluator,
    calculate_decision_metrics,
)
from apro.decision.models import ActionEligibility, ActionUtility
from apro.decision.traces import RecoveryDecisionTrace
from apro.diagnosis.classifiers.decision_tree import (
    DecisionTreeDiagnosisModel,
)
from apro.recovery_prediction.classifiers.logistic import (
    LogisticRegressionOutcomeModel,
)


def _generate_mini_dataset(
    dataset_type: DatasetType, seed: int = 42
) -> GovernedDataset:
    gen = DatasetGenerator()
    return gen.generate_dataset(
        dataset_type=dataset_type,
        dataset_version=f"mini-{dataset_type.value}-v1",
        seeds=[seed],
        cases_per_seed=20,
    )


def test_evaluator_workflow_and_segments() -> None:
    """Verify evaluator computes metrics, segments, and error analysis."""
    train_ds = _generate_mini_dataset(DatasetType.TRAINING, seed=42)
    test_ds = _generate_mini_dataset(DatasetType.HELD_OUT_TEST, seed=43)

    # 1. Fit Model A on Training
    diag_model = DecisionTreeDiagnosisModel(max_depth=4)
    diag_model.fit_on_dataset(train_ds)

    # 2. Fit Model B on Training
    outcome_model = LogisticRegressionOutcomeModel(max_iter=50)
    outcome_model.fit_on_dataset(train_ds, diagnosis_model=diag_model)

    # 3. Evaluate Decision Engine on Held-Out Test
    engine = EconomicDecisionEngine()
    evaluator = EconomicDecisionEvaluator()
    metrics, traces = evaluator.evaluate(
        decision_engine=engine,
        dataset=test_ds,
        diagnosis_model=diag_model,
        outcome_model=outcome_model,
    )

    assert metrics.case_count == 20
    assert 0.0 <= metrics.decision_accuracy_vs_oracle <= 1.0
    assert 0.0 <= metrics.recovery_rate <= 1.0
    assert metrics.constraint_violation_count == 0
    assert len(traces) == 20

    # Verify oracle gap formula on each trace:
    # max(0, oracle_best_value - selected_erv)
    for t in traces:
        s_erv = (
            t.expected_recovery_value if t.expected_recovery_value is not None else 0
        )
        expected_gap = max(0, t.oracle_best_value - s_erv)
        assert t.oracle_gap == expected_gap
        expected_regret = max(0, t.oracle_best_value - t.realized_value_under_selected)
        assert t.decision_regret == expected_regret

    # 4. Evaluate Segments across all 8 required dimensions
    segments = evaluator.evaluate_segments(traces)
    expected_dimensions = [
        "scenario_family",
        "payment_method",
        "payment_value_tier",
        "scenario_difficulty",
        "failure_diagnosis",
        "diagnosis_confidence_tier",
        "selected_action",
        "seed",
    ]
    for dim in expected_dimensions:
        assert dim in segments, f"Missing required segment dimension: {dim}"
        assert len(segments[dim]) > 0

    # 5. Error Analysis
    err_analysis = evaluator.perform_error_analysis(traces)
    assert "total_cases" in err_analysis
    assert "total_oracle_disagreements" in err_analysis
    assert "high_confidence_wrong_count" in err_analysis
    assert "negative_utility_count" in err_analysis
    assert "near_tie_decision_count" in err_analysis
    assert "policy_filtered_best_prediction_count" in err_analysis
    assert "large_regret_count" in err_analysis
    assert "ineligible_selection_count" in err_analysis
    assert "constraint_violation_count" in err_analysis


def test_constraint_violation_and_ineligible_metrics_detection() -> None:
    """Verify metrics calculation derives constraint violations from traces."""
    u_map = {
        RecoveryAction.RETRY: ActionUtility(
            action=RecoveryAction.RETRY,
            eligible=False,
            reason_if_ineligible="Blocked by max retries",
            predicted_success_probability=0.8,
            predicted_recovered_amount=100000,
            expected_gross_recovery=80000,
            action_cost=500,
            operational_cost=200,
            customer_friction_cost=300,
            risk_penalty=200,
            expected_recovery_value=78800,
        )
    }
    e_map = {
        RecoveryAction.RETRY: ActionEligibility(
            action=RecoveryAction.RETRY,
            is_eligible=False,
            reason="Blocked by max retries",
            policy_rule="RULE_H7_MAX_RETRY_LIMIT",
        )
    }

    # Construct trace with an intentionally ineligible selection
    tampered_trace = RecoveryDecisionTrace(
        decision_id="dec_tampered_01",
        record_id="rec_01",
        scenario_id="sc_01",
        selected_action=RecoveryAction.RETRY,
        decision_status=DecisionStatus.ACTION_SELECTED,
        utility_by_action=u_map,
        eligibility_by_action=e_map,
        expected_recovery_value=78800,
        expected_gross_recovery=80000,
        expected_cost=1200,
        decision_confidence=0.85,
        rationale="Tampered decision.",
        decision_latency_ms=1.0,
        diagnosis_model_version="v1.0",
        outcome_model_version="v1.0",
        dataset_version="test-v1",
        oracle_best_action=RecoveryAction.STOP,
        oracle_best_value=0,
        realized_value_under_selected=0,
        decision_regret=0,
        oracle_gap=0,
        is_oracle_match=False,
        is_unnecessary_intervention=True,
        is_ineligible_selection=True,
        is_constraint_violation=True,
        scenario_family="PSP_OUTAGE",
        payment_method="card",
        payment_value_tier="MEDIUM_VALUE",
        scenario_difficulty="MEDIUM",
        failure_diagnosis="SYSTEM_FAILURE",
        diagnosis_confidence_tier="HIGH_CONFIDENCE",
        seed=42,
        historical_failure_count=1,
        metadata_completeness=1.0,
    )

    metrics = calculate_decision_metrics([tampered_trace])
    assert metrics.constraint_violation_count == 1
    assert metrics.ineligible_selection_rate == 1.0
