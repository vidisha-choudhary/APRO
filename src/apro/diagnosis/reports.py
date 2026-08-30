"""Reporting and artifact formatting utilities for Phase 7 Failure Diagnosis."""

import json
from typing import Any

from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DiagnosisCategory,
)
from apro.diagnosis.metrics import DiagnosisMetrics
from apro.diagnosis.models import DiagnosisModelArtifact
from apro.diagnosis.traces import DiagnosisPredictionTrace


def generate_diagnosis_evaluation_json(evaluation_data: dict[str, Any]) -> str:
    """Generate authoritative machine-readable evaluation summary JSON."""
    return json.dumps(evaluation_data, indent=2)


def generate_confusion_matrix_json(
    matrix: list[list[int]],
    class_order: list[DiagnosisCategory] | None = None,
) -> str:
    """Generate structured confusion matrix JSON artifact."""
    classes = [c.value for c in (class_order or list(DIAGNOSIS_TAXONOMY_ORDER))]
    data = {
        "taxonomy_order": classes,
        "matrix": matrix,
        "rows": "Actual Failure Category",
        "columns": "Predicted Failure Category",
    }
    return json.dumps(data, indent=2)


def generate_prediction_traces_jsonl(
    traces: list[DiagnosisPredictionTrace],
) -> str:
    """Generate JSON Lines formatted prediction trace log."""
    lines = [json.dumps(t.model_dump()) for t in traces]
    return "\n".join(lines)


def generate_model_manifest_json(artifact: DiagnosisModelArtifact) -> str:
    """Generate model manifest JSON artifact."""
    return json.dumps(artifact.model_dump(), indent=2)


def generate_diagnosis_evaluation_markdown(
    model_name: str,
    model_version: str,
    dataset_version: str,
    feature_schema_version: str,
    taxonomy_version: str,
    baseline_metrics: dict[str, DiagnosisMetrics],
    candidate_metrics: dict[str, DiagnosisMetrics],
    selected_model_name: str,
    held_out_metrics: DiagnosisMetrics,
    shifted_metrics: DiagnosisMetrics | None = None,
    error_analysis: dict[str, Any] | None = None,
    selection_rationale: str | None = None,
) -> str:
    """Generate human-readable presentation Markdown evaluation report."""
    lines: list[str] = []

    lines.append(
        f"# APRO Phase 7 Failure Diagnosis Evaluation Report — `{model_name}`\n"
    )
    lines.append("## 1. Provenance & Metadata\n")
    lines.append(f"- **Model Name:** `{model_name}`")
    lines.append(f"- **Model Version:** `{model_version}`")
    lines.append(f"- **Dataset Version:** `{dataset_version}`")
    lines.append(f"- **Feature Schema Version:** `{feature_schema_version}`")
    lines.append(f"- **Taxonomy Version:** `{taxonomy_version}`\n")

    lines.append("## 2. Baseline & Candidate Model Selection (Validation Set)\n")
    if selection_rationale:
        lines.append(f"- **Selection Decision:** {selection_rationale}\n")
    headers = [
        "Model / Baseline",
        "Accuracy",
        "Balanced Acc.",
        "Macro F1",
        "Weighted F1",
        "Log Loss",
        "Brier Score",
        "ECE",
    ]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    # Baselines
    for b_name, m in baseline_metrics.items():
        row = [
            f"**Baseline: {b_name}**",
            f"{m.accuracy * 100:.2f}%",
            f"{m.balanced_accuracy * 100:.2f}%",
            f"{m.macro_f1 * 100:.2f}%",
            f"{m.weighted_f1 * 100:.2f}%",
            f"{m.log_loss:.4f}",
            f"{m.brier_score:.4f}",
            f"{m.expected_calibration_error:.4f}",
        ]
        lines.append("| " + " | ".join(row) + " |")

    # Candidates
    for c_name, m in candidate_metrics.items():
        is_sel = " (Selected)" if c_name == selected_model_name else ""
        row = [
            f"**Candidate: {c_name}{is_sel}**",
            f"{m.accuracy * 100:.2f}%",
            f"{m.balanced_accuracy * 100:.2f}%",
            f"{m.macro_f1 * 100:.2f}%",
            f"{m.weighted_f1 * 100:.2f}%",
            f"{m.log_loss:.4f}",
            f"{m.brier_score:.4f}",
            f"{m.expected_calibration_error:.4f}",
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## 3. Final Held-Out Test Evaluation\n")
    lines.append(f"- **Evaluated Test Cases:** **{held_out_metrics.case_count:,}**")
    lines.append(f"- **Overall Accuracy:** `{held_out_metrics.accuracy * 100:.2f}%`")
    lines.append(
        f"- **Balanced Accuracy:** `{held_out_metrics.balanced_accuracy * 100:.2f}%`"
    )
    lines.append(
        f"- **Macro Precision:** `{held_out_metrics.macro_precision * 100:.2f}%`"
    )
    lines.append(f"- **Macro Recall:** `{held_out_metrics.macro_recall * 100:.2f}%`")
    lines.append(f"- **Macro F1 Score:** `{held_out_metrics.macro_f1 * 100:.2f}%`")
    lines.append(
        f"- **Top-2 Accuracy:** `{held_out_metrics.top_2_accuracy * 100:.2f}%`"
    )
    lines.append(f"- **Multi-class Log Loss:** `{held_out_metrics.log_loss:.4f}`")
    lines.append(f"- **Brier Score:** `{held_out_metrics.brier_score:.4f}`")
    lines.append(
        "- **Expected Calibration Error (ECE):** "
        f"`{held_out_metrics.expected_calibration_error:.4f}`"
    )
    lines.append(
        "- **Average Decision Latency:** "
        f"`{held_out_metrics.average_decision_latency_ms:.4f} ms / decision`\n"
    )

    lines.append("### Per-Class Performance Breakdown\n")
    class_headers = ["Category", "Precision", "Recall", "F1 Score", "Support"]
    lines.append("| " + " | ".join(class_headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(class_headers)) + " |")

    for cat in DIAGNOSIS_TAXONOMY_ORDER:
        pm = held_out_metrics.per_class.get(cat)
        if pm:
            row = [
                f"`{cat.value}`",
                f"{pm.precision * 100:.2f}%",
                f"{pm.recall * 100:.2f}%",
                f"{pm.f1 * 100:.2f}%",
                f"{pm.support:,}",
            ]
            lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## 4. Confusion Matrix (Held-Out Test Set)\n")
    classes = [c.value for c in DIAGNOSIS_TAXONOMY_ORDER]
    col_headers = " | ".join(f"`{c[:6]}`" for c in classes)
    lines.append(f"| Actual \\ Predicted | {col_headers} |")
    lines.append("|---|" + "|".join(["---"] * len(classes)) + "|")
    for i, cm_row in enumerate(held_out_metrics.confusion_matrix):
        lines.append(
            f"| **`{classes[i]}`** | " + " | ".join(str(val) for val in cm_row) + " |"
        )
    lines.append("")

    if shifted_metrics:
        f1_delta = shifted_metrics.macro_f1 - held_out_metrics.macro_f1
        acc_delta = shifted_metrics.accuracy - held_out_metrics.accuracy
        loss_delta = shifted_metrics.log_loss - held_out_metrics.log_loss
        ece_delta = (
            shifted_metrics.expected_calibration_error
            - held_out_metrics.expected_calibration_error
        )
        lines.append("## 5. Distribution Shift Evaluation (Shifted Benchmark)\n")
        lines.append(
            "- **In-Distribution Macro F1:** "
            f"`{held_out_metrics.macro_f1 * 100:.2f}%` → "
            f"**Shifted Benchmark Macro F1:** "
            f"`{shifted_metrics.macro_f1 * 100:.2f}%` "
            f"(Δ {f1_delta:+.4f})"
        )
        lines.append(
            "- **In-Distribution Accuracy:** "
            f"`{held_out_metrics.accuracy * 100:.2f}%` → "
            f"**Shifted Benchmark Accuracy:** "
            f"`{shifted_metrics.accuracy * 100:.2f}%` "
            f"(Δ {acc_delta:+.4f})"
        )
        lines.append(
            "- **In-Distribution Log Loss:** "
            f"`{held_out_metrics.log_loss:.4f}` → "
            f"**Shifted Benchmark Log Loss:** "
            f"`{shifted_metrics.log_loss:.4f}` "
            f"(Δ {loss_delta:+.4f})"
        )
        lines.append(
            "- **In-Distribution ECE:** "
            f"`{held_out_metrics.expected_calibration_error:.4f}` → "
            f"**Shifted Benchmark ECE:** "
            f"`{shifted_metrics.expected_calibration_error:.4f}` "
            f"(Δ {ece_delta:+.4f})\n"
        )

    if error_analysis:
        err_rate = error_analysis.get("error_rate", 0.0) * 100
        hw_cnt = error_analysis.get("high_confidence_wrong_count", 0)
        low_cnt = error_analysis.get("low_confidence_count", 0)
        lines.append("## 6. Error Analysis Summary\n")
        lines.append(f"- **Total Error Rate:** `{err_rate:.2f}%`")
        lines.append(f"- **High-Confidence Wrong Predictions:** `{hw_cnt}`")
        lines.append(f"- **Low-Confidence Predictions:** `{low_cnt}`")
        top_pairs = error_analysis.get("top_confusion_pairs", [])
        if top_pairs:
            lines.append("- **Top Confusion Pairs:**")
            for item in top_pairs:
                lines.append(f"  - `{item['pair']}`: {item['count']} cases")
        lines.append("")

    return "\n".join(lines)
