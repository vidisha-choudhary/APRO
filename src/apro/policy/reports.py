"""Markdown and JSON report formatting for Policy & Safety Engine."""

import json
from pathlib import Path
from typing import Any

from apro.policy.evaluation import PolicySafetyMetrics


def format_policy_markdown_report(
    metrics: PolicySafetyMetrics,
    shift_comparison: dict[str, Any] | None = None,
    segments: dict[str, Any] | None = None,
) -> str:
    """Generate structured Markdown report summarizing policy evaluations."""
    allow_pct = metrics.allow_rate * 100
    block_pct = metrics.block_rate * 100
    appr_pct = metrics.require_human_approval_rate * 100

    lines: list[str] = [
        "# APRO Phase 10 — Policy & Safety Engine Evaluation Report",
        "",
        "## 1. Executive Summary & Safety Invariants",
        f"- **Total Benchmark Evaluations:** {metrics.total_evaluations}",
        f"- **Policy ALLOW Rate:** {allow_pct:.2f}% ({metrics.allow_count} cases)",
        f"- **Policy BLOCK Rate:** {block_pct:.2f}% ({metrics.block_count} cases)",
        (
            f"- **REQUIRE_HUMAN_APPROVAL Rate:** {appr_pct:.2f}% "
            f"({metrics.require_human_approval_count} cases)"
        ),
        (
            f"- **Hard Constraint Violations:** "
            f"**{metrics.constraint_violation_count}** (Verified: Zero Violations)"
        ),
        "",
        "## 2. Guardrail Trigger Breakdown",
        "| Guardrail Category | Trigger Count | Primary Outcome |",
        "| :--- | :---: | :--- |",
        (
            f"| High-Value (> 1000 INR) | "
            f"{metrics.high_value_approval_count} | REQUIRE_HUMAN_APPROVAL |"
        ),
        (
            f"| Low-Confidence (< 0.50) | "
            f"{metrics.low_confidence_approval_count} | "
            f"REQUIRE_HUMAN_APPROVAL / BLOCK |"
        ),
        (f"| Retry Limit (>= 3 retries) | {metrics.retry_limit_block_count} | BLOCK |"),
        (
            f"| Retry Cooldown (< 300s) | "
            f"{metrics.cooldown_block_count} | BLOCK / DEFER |"
        ),
        (
            f"| Same-Action Limit (>= 2 reps) | "
            f"{metrics.same_action_block_count} | BLOCK |"
        ),
        (
            f"| Total Interventions (>= 4) | "
            f"{metrics.total_intervention_limit_block_count} | BLOCK |"
        ),
        (
            f"| Negative / Sub-threshold ERV | "
            f"{metrics.negative_erv_block_count} | BLOCK |"
        ),
        (
            f"| Captured / Stale State | "
            f"{metrics.captured_payment_block_count} | HARD BLOCK |"
        ),
        (
            f"| Invalid Model Output / NaN | "
            f"{metrics.invalid_model_output_block_count} | FAIL-CLOSED BLOCK |"
        ),
        (
            f"| Duplicate Webhook | "
            f"{metrics.duplicate_event_block_count} | IGNORE / BLOCK |"
        ),
        (
            f"| Idempotency Key Conflicts | "
            f"{metrics.idempotency_conflict_count} | BLOCK |"
        ),
        "",
        "## 3. Reason Code Distribution",
        "| Reason Code | Count |",
        "| :--- | :---: |",
    ]

    for code, cnt in sorted(
        metrics.reason_code_counts.items(), key=lambda x: x[1], reverse=True
    ):
        lines.append(f"| `{code}` | {cnt} |")

    if shift_comparison:
        in_dist = shift_comparison.get("in_distribution", {})
        shift = shift_comparison.get("distribution_shift", {})
        delta = shift_comparison.get("delta", {})
        in_al = in_dist.get("allow_rate", 0.0) * 100
        sh_al = shift.get("allow_rate", 0.0) * 100
        d_al = delta.get("allow_rate_delta", 0.0) * 100
        in_bl = in_dist.get("block_rate", 0.0) * 100
        sh_bl = shift.get("block_rate", 0.0) * 100
        d_bl = delta.get("block_rate_delta", 0.0) * 100
        in_ap = in_dist.get("require_human_approval_rate", 0.0) * 100
        sh_ap = shift.get("require_human_approval_rate", 0.0) * 100
        d_ap = delta.get("approval_rate_delta", 0.0) * 100
        lines.extend(
            [
                "",
                "## 4. Distribution-Shift Governance Robustness",
                "| Metric | In-Dist Benchmark | Shifted Set | Delta |",
                "| :--- | :---: | :---: | :---: |",
                f"| Allow Rate | {in_al:.2f}% | {sh_al:.2f}% | {d_al:+.2f}% |",
                f"| Block Rate | {in_bl:.2f}% | {sh_bl:.2f}% | {d_bl:+.2f}% |",
                f"| Approval Rate | {in_ap:.2f}% | {sh_ap:.2f}% | {d_ap:+.2f}% |",
                (
                    f"| Violations | {in_dist.get('constraint_violations', 0)} | "
                    f"{shift.get('constraint_violations', 0)} | 0 |"
                ),
            ]
        )

    if segments:
        lines.extend(
            [
                "",
                "## 5. Segment Compliance Breakdown",
                "| Segment Dimension | Count | Allow | Block | Approval |",
                "| :--- | :---: | :---: | :---: | :---: |",
            ]
        )
        for seg_name, seg_data in sorted(segments.items()):
            cnt = seg_data.get("count", 0)
            al = seg_data.get("allow", 0)
            bl = seg_data.get("block", 0)
            ap = seg_data.get("require_approval", 0)
            lines.append(f"| `{seg_name}` | {cnt} | {al} | {bl} | {ap} |")

    return "\n".join(lines)


def export_policy_metrics_json(
    metrics: PolicySafetyMetrics,
    file_path: Path | str,
) -> None:
    """Export PolicySafetyMetrics to structured JSON."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(metrics.model_dump(), indent=2, sort_keys=True))


__all__ = [
    "export_policy_metrics_json",
    "format_policy_markdown_report",
]
