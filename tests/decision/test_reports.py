"""Unit tests for report generation, traces JSONL, and manifests."""

from pathlib import Path

from apro.decision.artifacts import DecisionEngineArtifact
from apro.decision.enums import DecisionStatus, RecoveryAction
from apro.decision.evaluation import DecisionEvaluationMetrics
from apro.decision.models import ActionEligibility, ActionUtility
from apro.decision.reports import (
    save_decision_reports,
)
from apro.decision.traces import RecoveryDecisionTrace


def _make_dummy_trace() -> RecoveryDecisionTrace:
    u_map = {
        RecoveryAction.RETRY: ActionUtility(
            action=RecoveryAction.RETRY,
            eligible=True,
            predicted_success_probability=0.85,
            predicted_recovered_amount=500000,
            expected_gross_recovery=425000,
            action_cost=500,
            operational_cost=200,
            customer_friction_cost=300,
            risk_penalty=200,
            expected_recovery_value=423800,
        )
    }
    e_map = {
        RecoveryAction.RETRY: ActionEligibility(
            action=RecoveryAction.RETRY,
            is_eligible=True,
            reason="Eligible under policy.",
        )
    }
    return RecoveryDecisionTrace(
        decision_id="dec_01",
        record_id="rec_01",
        scenario_id="sc_01",
        selected_action=RecoveryAction.RETRY,
        decision_status=DecisionStatus.ACTION_SELECTED,
        utility_by_action=u_map,
        eligibility_by_action=e_map,
        expected_recovery_value=423800,
        expected_gross_recovery=425000,
        expected_cost=1200,
        decision_confidence=0.85,
        rationale="Selected RETRY.",
        decision_latency_ms=1.2,
        diagnosis_model_version="v1.0",
        outcome_model_version="v1.0",
        dataset_version="test-v1",
        oracle_best_action=RecoveryAction.RETRY,
        oracle_best_value=500000,
        realized_value_under_selected=500000,
        decision_regret=0,
        oracle_gap=76200,
        is_oracle_match=True,
        is_unnecessary_intervention=False,
        is_ineligible_selection=False,
        is_constraint_violation=False,
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


def test_generate_and_save_decision_reports(tmp_path: Path) -> None:
    """Verify Markdown report generation and file persistence."""
    metrics = DecisionEvaluationMetrics(
        case_count=10,
        decision_accuracy_vs_oracle=0.90,
        mean_utility=40000.0,
        median_utility=38000.0,
        mean_decision_regret=5000.0,
        median_decision_regret=0.0,
        oracle_gap=10000.0,
        recovery_rate=0.90,
        total_recovered_amount=4500000,
        mean_recovered_amount=450000.0,
        intervention_rate=0.90,
        no_intervention_rate=0.10,
        unnecessary_intervention_rate=0.0,
        ineligible_selection_rate=0.0,
        constraint_violation_count=0,
        selected_action_distribution={"RETRY": 9, "STOP": 1},
    )

    artifact = DecisionEngineArtifact.create()
    trace = _make_dummy_trace()

    out_paths = save_decision_reports(
        output_dir=tmp_path,
        metrics=metrics,
        baseline_metrics={"Engine": metrics},
        segment_metrics={
            "payment_method": {
                "card": {
                    "case_count": 10,
                    "decision_accuracy_vs_oracle": 0.9,
                    "mean_utility": 40000,
                    "mean_decision_regret": 5000,
                    "recovery_rate": 0.9,
                }
            }
        },
        shift_comparison={
            "in_distribution": metrics.model_dump(),
            "shifted_distribution": metrics.model_dump(),
            "deltas": {},
        },
        error_analysis={
            "total_cases": 10,
            "total_oracle_disagreements": 1,
            "oracle_disagreement_rate": 0.1,
            "large_regret_count": 0,
            "unnecessary_intervention_count": 0,
        },
        artifact=artifact,
        traces=[trace],
    )

    assert out_paths["markdown_report"].exists()
    assert out_paths["json_metrics"].exists()
    assert out_paths["traces_jsonl"].exists()
    assert out_paths["manifest_json"].exists()

    md_text = out_paths["markdown_report"].read_text(encoding="utf-8")
    assert "# APRO Phase 9" in md_text
    assert "## 6. Error & Constraint Analysis" in md_text
