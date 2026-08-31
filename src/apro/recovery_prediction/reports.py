"""Report generation (JSON, Markdown, traces) for APRO Phase 8."""

import json
from typing import Any

from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_ORDER,
    RecoveryAction,
)
from apro.recovery_prediction.metrics import RecoveryOutcomeMetrics
from apro.recovery_prediction.models import RecoveryOutcomeModelArtifact
from apro.recovery_prediction.traces import RecoveryPredictionTrace


def generate_recovery_evaluation_json(metrics_dict: dict[str, Any]) -> str:
    """Serialize consolidated evaluation metrics to formatted JSON."""
    return json.dumps(metrics_dict, indent=2, sort_keys=True)


def generate_recovery_confusion_json(
    per_action_class: dict[RecoveryAction, Any],
) -> str:
    """Format per-action confusion matrices to JSON."""
    formatted = {
        "action_order": [a.value for a in RECOVERY_ACTION_ORDER],
        "format": "[[TN, FP], [FN, TP]]",
        "matrices": {
            act.value: per_action_class[act].confusion_matrix
            for act in RECOVERY_ACTION_ORDER
            if act in per_action_class
        },
    }
    return json.dumps(formatted, indent=2)


def generate_recovery_prediction_traces_jsonl(
    traces: list[RecoveryPredictionTrace],
) -> str:
    """Serialize prediction traces to JSON Lines format."""
    lines = [json.dumps(t.model_dump()) for t in traces]
    return "\n".join(lines) + "\n"


def generate_recovery_model_manifest_json(
    artifact: RecoveryOutcomeModelArtifact,
) -> str:
    """Generate machine-readable model manifest JSON."""
    manifest = {
        "manifest_version": "1.0",
        "model_name": artifact.model_name,
        "model_version": artifact.model_version,
        "algorithm": artifact.algorithm,
        "feature_schema_version": artifact.feature_schema_version,
        "action_schema_version": artifact.action_schema_version,
        "outcome_schema_version": artifact.outcome_schema_version,
        "training_dataset_version": artifact.training_dataset_version,
        "training_seed": artifact.training_seed,
        "diagnosis_model_version": artifact.diagnosis_model_version,
        "created_at": artifact.created_at,
        "deterministic_identity": artifact.deterministic_identity,
        "feature_count": len(artifact.feature_names),
        "calibration_method": artifact.calibration_method,
        "supported_actions": [a.value for a in artifact.action_order],
    }
    return json.dumps(manifest, indent=2, sort_keys=True)


def generate_recovery_evaluation_markdown(
    model_name: str,
    model_version: str,
    dataset_version: str,
    feature_schema_version: str,
    action_schema_version: str,
    baseline_metrics: dict[str, RecoveryOutcomeMetrics],
    candidate_metrics: dict[str, RecoveryOutcomeMetrics],
    selected_model_name: str,
    held_out_metrics: RecoveryOutcomeMetrics,
    shifted_metrics: RecoveryOutcomeMetrics | None = None,
    error_analysis: dict[str, Any] | None = None,
    selection_rationale: str | None = None,
) -> str:
    """Generate human-readable Markdown evaluation report for Model B."""
    po_m = held_out_metrics.potential_outcome_metrics
    lines = [
        "# APRO Phase 8 Recovery Outcome Prediction Evaluation Report",
        "",
        f"**Model Name:** `{model_name}`  ",
        f"**Model Version:** `{model_version}`  ",
        f"**Evaluated Dataset Version:** `{dataset_version}`  ",
        f"**Feature Schema Version:** `{feature_schema_version}`  ",
        f"**Action Schema Version:** `{action_schema_version}`  ",
        "",
        "---",
        "",
        "## 1. Executive Summary & Selection Decision",
        "",
    ]

    if selection_rationale:
        lines.extend(
            [
                f"> **Model Selection Decision:** {selection_rationale}",
                "",
            ]
        )

    lines.extend(
        [
            f"- **Held-Out Cases Evaluated:** {held_out_metrics.case_count:,} "
            f"({held_out_metrics.scenario_count:,} scenarios across 5 actions)",
            f"- **Overall Classification Accuracy:** "
            f"{held_out_metrics.accuracy * 100:.2f}%",
            f"- **Macro F1 Score across Actions:** "
            f"{held_out_metrics.macro_f1 * 100:.2f}%",
            f"- **Mean Absolute Error (MAE):** Rs {held_out_metrics.mae / 100:.2f}",
            f"- **Multi-class Log Loss:** {held_out_metrics.log_loss:.4f}",
            f"- **Expected Calibration Error (ECE):** "
            f"- **Mean Counterfactual Regret:** "
            f"Rs {po_m.counterfactual_regret / 100:.2f}",
            f"- **Oracle Gap:** Rs {po_m.oracle_gap / 100:.2f}",
            "",
            "---",
            "",
            "## 2. Validation Benchmark: Baselines vs Candidates",
            "",
            "| Model Name | Accuracy | Macro F1 | Log Loss | MAE (Rs) | ECE |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for b_name, b_m in baseline_metrics.items():
        lines.append(
            f"| {b_name} (Baseline) | {b_m.accuracy * 100:5.2f}% | "
            f"{b_m.macro_f1 * 100:5.2f}% | {b_m.log_loss:6.4f} | "
            f"{b_m.mae / 100:6.2f} | {b_m.expected_calibration_error:.4f} |"
        )

    for c_name, c_m in candidate_metrics.items():
        sel_tag = " **(Selected)**" if c_name == selected_model_name else ""
        lines.append(
            f"| {c_name}{sel_tag} | {c_m.accuracy * 100:5.2f}% | "
            f"{c_m.macro_f1 * 100:5.2f}% | {c_m.log_loss:6.4f} | "
            f"{c_m.mae / 100:6.2f} | {c_m.expected_calibration_error:.4f} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Per-Action Performance Breakdown (Held-Out Test Set)",
            "",
            "| Action | Cases | Accuracy | Precision | Recall | F1 | MAE (Rs) |"
            " Log Loss | ECE |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for act in RECOVERY_ACTION_ORDER:
        cm = held_out_metrics.per_action_classification[act]
        am = held_out_metrics.per_action_amount[act]
        lines.append(
            f"| `{act.value}` | {cm.case_count:,} | {cm.accuracy * 100:5.2f}% | "
            f"{cm.precision * 100:5.2f}% | {cm.recall * 100:5.2f}% | "
            f"{cm.f1 * 100:5.2f}% | {am.mae / 100:6.2f} | {cm.log_loss:6.4f} | "
            f"{cm.expected_calibration_error:.4f} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Evaluator-Side Potential-Outcome Analysis",
            "",
            f"- **Mean Best Achievable Value:** "
            f"Rs {po_m.mean_best_achievable_value / 100:.2f}",
            f"- **Mean Predicted Best Value:** "
            f"Rs {po_m.mean_predicted_best_value / 100:.2f}",
            f"- **Oracle Gap:** Rs {po_m.oracle_gap / 100:.2f}",
            f"- **Counterfactual Regret:** Rs {po_m.counterfactual_regret / 100:.2f}",
            "",
        ]
    )

    if shifted_metrics:
        s_po_m = shifted_metrics.potential_outcome_metrics
        acc_d = shifted_metrics.accuracy - held_out_metrics.accuracy
        f1_d = shifted_metrics.macro_f1 - held_out_metrics.macro_f1
        ll_d = shifted_metrics.log_loss - held_out_metrics.log_loss
        mae_d = (shifted_metrics.mae - held_out_metrics.mae) / 100
        gap_d = (s_po_m.oracle_gap - po_m.oracle_gap) / 100
        lines.extend(
            [
                "---",
                "",
                "## 5. Distribution Shift Resilience",
                "",
                "| Metric | In-Distribution Test | Shifted Benchmark | Delta |",
                "| :--- | :---: | :---: | :---: |",
                f"| Accuracy | {held_out_metrics.accuracy * 100:5.2f}% | "
                f"{shifted_metrics.accuracy * 100:5.2f}% | {acc_d:+.4f} |",
                f"| Macro F1 | {held_out_metrics.macro_f1 * 100:5.2f}% | "
                f"{shifted_metrics.macro_f1 * 100:5.2f}% | {f1_d:+.4f} |",
                f"| Log Loss | {held_out_metrics.log_loss:6.4f} | "
                f"{shifted_metrics.log_loss:6.4f} | {ll_d:+.4f} |",
                f"| MAE (Rs) | {held_out_metrics.mae / 100:6.2f} | "
                f"{shifted_metrics.mae / 100:6.2f} | {mae_d:+.2f} |",
                f"| Oracle Gap (Rs) | {po_m.oracle_gap / 100:6.2f} | "
                f"{s_po_m.oracle_gap / 100:6.2f} | {gap_d:+.2f} |",
                "",
            ]
        )

    if error_analysis:
        e_cnt = error_analysis.get("total_errors", 0)
        e_rate = error_analysis.get("error_rate", 0.0) * 100
        hc_cnt = error_analysis.get("high_confidence_wrong_count", 0)
        hc_rate = error_analysis.get("high_confidence_error_rate", 0.0) * 100
        la_cnt = error_analysis.get("large_amount_error_count", 0)
        lines.extend(
            [
                "---",
                "",
                "## 6. Error Analysis & Risk Inspection",
                "",
                f"- **Total Action Cases:** {error_analysis.get('total_cases', 0):,}",
                f"- **Classification Errors:** {e_cnt:,} ({e_rate:.2f}%)",
                f"- **High-Confidence Mistakes:** {hc_cnt:,} ({hc_rate:.2f}%)",
                f"- **Large Amount Deviations (>= Rs 1,000):** {la_cnt:,}",
                "",
                "### Errors by Recovery Action",
                "",
            ]
        )
        for act_name, count in error_analysis.get("action_error_breakdown", {}).items():
            lines.append(f"- `{act_name}`: {count} errors")

    lines.extend(
        [
            "",
            "---",
            "",
            "> [!NOTE]",
            "> **Phase Boundary Reminder:** Model B predicts conditional recovery "
            "outcomes for specific actions. It does not select or execute actions. "
            "Action selection belongs to Phase 9+.",
            "",
        ]
    )

    return "\n".join(lines)
