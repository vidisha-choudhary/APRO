"""Markdown report and JSON metrics generator for APRO Phase 9 Decision Engine."""

import json
from pathlib import Path
from typing import Any

from apro.decision.artifacts import DecisionEngineArtifact
from apro.decision.evaluation import DecisionEvaluationMetrics
from apro.decision.traces import RecoveryDecisionTrace


def generate_markdown_report(
    metrics: DecisionEvaluationMetrics,
    baseline_metrics: dict[str, DecisionEvaluationMetrics],
    segment_metrics: dict[str, dict[str, Any]],
    shift_comparison: dict[str, Any],
    error_analysis: dict[str, Any],
    artifact: DecisionEngineArtifact,
) -> str:
    """Generate the comprehensive Phase 9 decision evaluation Markdown report."""
    mean_u_rs = metrics.mean_utility / 100
    med_u_rs = metrics.median_utility / 100
    mean_reg_rs = metrics.mean_decision_regret / 100
    mean_gap_rs = metrics.oracle_gap / 100
    tot_rec_rs = metrics.total_recovered_amount / 100

    md = [
        "# APRO Phase 9 — Economic Decision Engine Evaluation Report",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Evaluated Cases:** {metrics.case_count:,}",
        (
            f"- **Decision Accuracy vs Oracle:** "
            f"{metrics.decision_accuracy_vs_oracle:.2%}"
        ),
        f"- **Mean Economic Utility:** Rs {mean_u_rs:.2f}",
        f"- **Median Economic Utility:** Rs {med_u_rs:.2f}",
        f"- **Mean Decision Regret:** Rs {mean_reg_rs:.2f}",
        f"- **Mean Oracle Gap:** Rs {mean_gap_rs:.2f}",
        f"- **Gross Recovery Rate:** {metrics.recovery_rate:.2%}",
        f"- **Total Recovered Amount:** Rs {tot_rec_rs:,.2f}",
        f"- **Active Intervention Rate:** {metrics.intervention_rate:.2%}",
        (
            f"- **Unnecessary Intervention Rate:** "
            f"{metrics.unnecessary_intervention_rate:.2%}"
        ),
        (
            f"- **Policy Constraint Violations:** "
            f"{metrics.constraint_violation_count} "
            f"({metrics.ineligible_selection_rate:.2%})"
        ),
        "",
        "---",
        "",
        "## 2. Baseline Comparison",
        "",
        (
            "| Decision Strategy | Type | Accuracy vs Oracle | "
            "Mean Utility (Rs) | Mean Regret (Rs) | Recovery Rate | "
            "Intervention Rate |"
        ),
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for name, b_m in baseline_metrics.items():
        is_baseline = (
            "Baseline" in name or "No Intervention" in name or "Highest" in name
        )
        b_type = "Baseline" if is_baseline else "Selected Engine"
        b_u = b_m.mean_utility / 100
        b_reg = b_m.mean_decision_regret / 100
        md.append(
            f"| {name} | {b_type} | {b_m.decision_accuracy_vs_oracle:.2%} | "
            f"Rs {b_u:.2f} | Rs {b_reg:.2f} | "
            f"{b_m.recovery_rate:.2%} | {b_m.intervention_rate:.2%} |"
        )

    md.extend(
        [
            "",
            "---",
            "",
            "## 3. Selected Action Distribution",
            "",
            "| Recovery Action | Selected Cases | Distribution Share |",
            "| :--- | :---: | :---: |",
        ]
    )

    for act, count in sorted(metrics.selected_action_distribution.items()):
        share = count / max(1, metrics.case_count)
        md.append(f"| `{act}` | {count:,} | {share:.2%} |")

    md.extend(
        [
            "",
            "---",
            "",
            "## 4. Distribution Shift Resilience",
            "",
            "| Metric | In-Distribution Test | Shifted Benchmark | Delta |",
            "| :--- | :---: | :---: | :---: |",
        ]
    )

    in_dist = shift_comparison.get("in_distribution", {})
    sh_dist = shift_comparison.get("shifted_distribution", {})
    deltas = shift_comparison.get("deltas", {})

    acc_in = in_dist.get("decision_accuracy_vs_oracle", 0.0)
    acc_sh = sh_dist.get("decision_accuracy_vs_oracle", 0.0)
    acc_d = deltas.get("decision_accuracy_delta", 0.0)
    md.append(
        f"| **Decision Accuracy vs Oracle** | {acc_in:.2%} | "
        f"{acc_sh:.2%} | {acc_d:+.2%} |"
    )

    u_in = in_dist.get("mean_utility", 0.0) / 100
    u_sh = sh_dist.get("mean_utility", 0.0) / 100
    u_d = deltas.get("mean_utility_delta", 0.0) / 100
    md.append(f"| **Mean Utility** | Rs {u_in:.2f} | Rs {u_sh:.2f} | Rs {u_d:+.2f} |")

    reg_in = in_dist.get("mean_decision_regret", 0.0) / 100
    reg_sh = sh_dist.get("mean_decision_regret", 0.0) / 100
    reg_d = deltas.get("mean_regret_delta", 0.0) / 100
    md.append(
        f"| **Mean Decision Regret** | Rs {reg_in:.2f} | "
        f"Rs {reg_sh:.2f} | Rs {reg_d:+.2f} |"
    )

    rec_in = in_dist.get("recovery_rate", 0.0)
    rec_sh = sh_dist.get("recovery_rate", 0.0)
    rec_d = deltas.get("recovery_rate_delta", 0.0)
    md.append(f"| **Recovery Rate** | {rec_in:.2%} | {rec_sh:.2%} | {rec_d:+.2%} |")

    md.extend(
        [
            "",
            "---",
            "",
            "## 5. Segment Performance Breakdown",
            "",
        ]
    )

    for dim, grps in segment_metrics.items():
        md.append(f"### Segment Dimension: `{dim}`")
        md.append("")
        md.append(
            "| Segment Value | Cases | Accuracy vs Oracle | "
            "Mean Utility (Rs) | Mean Regret (Rs) | Recovery Rate |"
        )
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for val, m in grps.items():
            s_u = m["mean_utility"] / 100
            s_reg = m["mean_decision_regret"] / 100
            md.append(
                f"| `{val}` | {m['case_count']:,} | "
                f"{m['decision_accuracy_vs_oracle']:.2%} | "
                f"Rs {s_u:.2f} | Rs {s_reg:.2f} | "
                f"{m['recovery_rate']:.2%} |"
            )
        md.append("")

    tot_c = error_analysis.get("total_cases", 0)
    tot_or_dis = error_analysis.get("total_oracle_disagreements", 0)
    or_dis_rate = error_analysis.get("oracle_disagreement_rate", 0.0)
    hi_conf_w = error_analysis.get("high_confidence_wrong_count", 0)
    hi_conf_rate = error_analysis.get("high_confidence_wrong_rate", 0.0)
    neg_u_cnt = error_analysis.get("negative_utility_count", 0)
    near_tie_cnt = error_analysis.get("near_tie_decision_count", 0)
    pol_filt_cnt = error_analysis.get("policy_filtered_best_prediction_count", 0)
    lg_reg = error_analysis.get("large_regret_count", 0)
    un_int = error_analysis.get("unnecessary_intervention_count", 0)
    inel_cnt = error_analysis.get("ineligible_selection_count", 0)
    viol_cnt = error_analysis.get("constraint_violation_count", 0)

    md.extend(
        [
            "---",
            "",
            "## 6. Error & Constraint Analysis",
            "",
            f"- **Total Evaluated Cases:** {tot_c:,}",
            f"- **Oracle Disagreements:** {tot_or_dis:,} ({or_dis_rate:.2%})",
            (
                f"- **High-Confidence Wrong Decisions:** {hi_conf_w:,} "
                f"({hi_conf_rate:.2%})"
            ),
            f"- **Negative-Utility Selections:** {neg_u_cnt:,}",
            f"- **Near-Tie Decisions (margin <= Rs 5.00):** {near_tie_cnt:,}",
            (f"- **Policy-Filtered Best Prediction Actions:** {pol_filt_cnt:,}"),
            f"- **Large Regret Decisions (>= Rs 500):** {lg_reg:,}",
            f"- **Unnecessary Active Interventions:** {un_int:,}",
            f"- **Ineligible Action Selections:** {inel_cnt:,}",
            f"- **Policy Constraint Violations:** {viol_cnt:,}",
            "",
            "---",
            "",
            "## 7. Artifact Provenance & Deterministic Identity",
            "",
            f"- **Deterministic Identity:** `{artifact.deterministic_identity}`",
            f"- **Decision Model Version:** `{artifact.decision_model_version}`",
            (
                f"- **Economic Config Version:** "
                f"`{artifact.economic_config.config_version}`"
            ),
            f"- **Policy Version:** `{artifact.policy_config.policy_version}`",
            f"- **Action Schema Version:** `{artifact.action_schema_version}`",
            f"- **Created At:** `{artifact.created_at}`",
        ]
    )

    return "\n".join(md)


def save_decision_reports(
    output_dir: Path | str,
    metrics: DecisionEvaluationMetrics,
    baseline_metrics: dict[str, DecisionEvaluationMetrics],
    segment_metrics: dict[str, dict[str, Any]],
    shift_comparison: dict[str, Any],
    error_analysis: dict[str, Any],
    artifact: DecisionEngineArtifact,
    traces: list[RecoveryDecisionTrace],
) -> dict[str, Path]:
    """Persist Markdown, JSON metrics, JSONL traces, and manifest files."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / "economic_decision_evaluation.md"
    json_path = out_dir / "economic_decision_evaluation.json"
    traces_path = out_dir / "economic_decision_trace.jsonl"
    manifest_path = out_dir / "economic_decision_manifest.json"

    # 1. Write Markdown Report
    md_content = generate_markdown_report(
        metrics=metrics,
        baseline_metrics=baseline_metrics,
        segment_metrics=segment_metrics,
        shift_comparison=shift_comparison,
        error_analysis=error_analysis,
        artifact=artifact,
    )
    md_path.write_text(md_content, encoding="utf-8")

    # 2. Write JSON Evaluation Metrics
    json_data = {
        "evaluation_metrics": metrics.model_dump(),
        "baseline_comparison": {k: v.model_dump() for k, v in baseline_metrics.items()},
        "segment_metrics": segment_metrics,
        "shift_comparison": shift_comparison,
        "error_analysis": error_analysis,
        "artifact_identity": artifact.deterministic_identity,
    }
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    # 3. Write Traces JSONL
    with traces_path.open("w", encoding="utf-8") as f:
        for t in traces:
            f.write(t.model_dump_json() + "\n")

    # 4. Write Manifest JSON
    manifest_data = {
        "manifest_version": "decision-manifest-v1",
        "artifact_deterministic_identity": artifact.deterministic_identity,
        "decision_model_version": artifact.decision_model_version,
        "total_cases_evaluated": metrics.case_count,
        "files": {
            "markdown_report": md_path.name,
            "json_metrics": json_path.name,
            "traces_jsonl": traces_path.name,
        },
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    return {
        "markdown_report": md_path,
        "json_metrics": json_path,
        "traces_jsonl": traces_path,
        "manifest_json": manifest_path,
    }
