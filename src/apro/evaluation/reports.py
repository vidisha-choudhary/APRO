"""Report generators for APRO Phase 6."""

import json
from typing import Any

from apro.evaluation.benchmark import BenchmarkRunResult


def generate_benchmark_summary_json(result: BenchmarkRunResult) -> str:
    """Generate authoritative machine-readable JSON summary artifact."""
    return json.dumps(result.model_dump(), indent=2)


def generate_benchmark_summary_markdown(result: BenchmarkRunResult) -> str:
    """Generate presentation-oriented human-readable Markdown summary artifact."""
    manifest = result.manifest
    lines: list[str] = []

    lines.append(f"# APRO Benchmark Summary Report — `{manifest.benchmark_version}`\n")
    lines.append("## 1. Provenance & Execution Manifest\n")
    lines.append(f"- **Benchmark Version:** `{manifest.benchmark_version}`")
    lines.append(f"- **Dataset Version:** `{manifest.dataset_version}`")
    lines.append(f"- **Scenario Version:** `{manifest.scenario_version}`")
    lines.append(f"- **Configuration Version:** `{manifest.configuration_version}`")
    lines.append(f"- **Feature Schema Version:** `{manifest.feature_schema_version}`")
    lines.append(f"- **Metric Version:** `{manifest.metric_version}`")
    lines.append(f"- **Seeds Evaluated:** `{manifest.seed_list}`")
    lines.append(f"- **Total Recovery Cases:** **{manifest.case_count:,}**")
    if manifest.distribution_shift_name:
        lines.append(f"- **Distribution Shift:** `{manifest.distribution_shift_name}`")
    lines.append(f"- **Created At:** `{manifest.created_at}`\n")

    lines.append("## 2. Comparative Strategy Performance\n")
    headers = [
        "Strategy",
        "Version",
        "Revenue at Risk",
        "Recovered",
        "Incremental",
        "Recovery Rate",
        "Interv. Rate",
        "Unnec. Interv.",
        "EV Capture",
        "Avg Regret",
    ]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for strat_name, metrics in result.strategy_metrics.items():
        v = manifest.strategy_versions.get(strat_name, "v1.0")
        rar = f"₹{metrics.economic.revenue_at_risk / 100:,.2f}"
        rec = f"₹{metrics.economic.revenue_recovered / 100:,.2f}"
        inc = f"₹{metrics.economic.incremental_revenue_recovered / 100:,.2f}"
        rr = f"{metrics.economic.recovery_rate * 100:.2f}%"
        ir = f"{metrics.economic.intervention_rate * 100:.2f}%"
        uir = f"{metrics.economic.unnecessary_intervention_rate * 100:.2f}%"
        evc = f"{metrics.decision.expected_value_capture * 100:.2f}%"
        reg = f"₹{metrics.decision.average_regret / 100:,.2f}"

        row = [
            f"**{strat_name}**",
            f"`{v}`",
            rar,
            rec,
            inc,
            rr,
            ir,
            uir,
            evc,
            reg,
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## 3. Multi-Seed Statistical Summary (Across Seeds)\n")
    stat_headers = [
        "Strategy",
        "Metric",
        "Mean",
        "Median",
        "Std Dev",
        "Min",
        "Max",
        "95% Confidence Interval",
    ]
    lines.append("| " + " | ".join(stat_headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(stat_headers)) + " |")

    for strat_name, stats_map in result.strategy_multi_seed_stats.items():
        if "recovery_rate" in stats_map:
            rr_s = stats_map["recovery_rate"]
            lines.append(
                f"| **{strat_name}** | **Recovery Rate** | "
                f"{rr_s.mean * 100:.2f}% | {rr_s.median * 100:.2f}% | "
                f"{rr_s.std_dev * 100:.2f}% | {rr_s.min_val * 100:.2f}% | "
                f"{rr_s.max_val * 100:.2f}% | "
                f"[{rr_s.ci_95_lower * 100:.2f}%, {rr_s.ci_95_upper * 100:.2f}%] |"
            )
        if "incremental_revenue_recovered" in stats_map:
            inc_s = stats_map["incremental_revenue_recovered"]
            lines.append(
                f"| **{strat_name}** | **Incremental Revenue** | "
                f"₹{inc_s.mean / 100:,.2f} | ₹{inc_s.median / 100:,.2f} | "
                f"₹{inc_s.std_dev / 100:,.2f} | ₹{inc_s.min_val / 100:,.2f} | "
                f"₹{inc_s.max_val / 100:,.2f} | "
                f"[₹{inc_s.ci_95_lower / 100:,.2f}, ₹{inc_s.ci_95_upper / 100:,.2f}] |"
            )
    lines.append("")

    lines.append("## 4. Scenario Dimension Coverage\n")
    lines.append("| Dimension | Category | Count | Proportion |")
    lines.append("|---|---|---|---|")
    total_cases = max(1, manifest.case_count)
    for dim_name, cat_counts in result.coverage.items():
        if dim_name in (
            "scenario_family",
            "recoverability",
            "customer_behavior",
            "scenario_difficulty",
        ):
            for cat, cnt in cat_counts.items():
                prop = f"{cnt / total_cases * 100:.1f}%"
                lines.append(f"| `{dim_name}` | **{cat}** | {cnt:,} | {prop} |")
    lines.append("")

    lines.append("## 5. Safety & Reliability Signals (Phase 6 Baseline Schema)\n")
    first_m = next(iter(result.strategy_metrics.values()), None)
    sr = first_m.safety_reliability if first_m else None

    def _fmt(name: str, val: Any) -> str:
        if val is None:
            return f"- **{name}:** `N/A (unavailable in Phase 6)`"
        if isinstance(val, float):
            return f"- **{name}:** `{val:.4f}`"
        return f"- **{name}:** `{val}`"

    if sr is not None:
        lines.append(_fmt("Policy Violation Count", sr.policy_violation_count))
        lines.append(_fmt("Duplicate Execution Count", sr.duplicate_execution_count))
        lines.append(
            _fmt(
                "Captured Payment Intervention Count",
                sr.captured_payment_intervention_count,
            )
        )
        lines.append(
            _fmt("Retry Limit Violation Count", sr.retry_limit_violation_count)
        )
        lines.append(
            _fmt("Invalid Model Execution Count", sr.invalid_model_execution_count)
        )
        lines.append(
            _fmt(
                "Unknown State Unsafe Execution Count",
                sr.unknown_state_unsafe_execution_count,
            )
        )
        lines.append(
            _fmt(
                "Webhook Processing Success Rate",
                sr.webhook_processing_success_rate,
            )
        )
        lines.append(_fmt("Event Deduplication Rate", sr.event_deduplication_rate))
        lines.append(_fmt("Decision Success Rate", sr.decision_success_rate))
        lines.append(_fmt("Execution Success Rate", sr.execution_success_rate))
        lines.append(_fmt("Unknown Execution Rate", sr.unknown_execution_rate))
        lines.append(_fmt("API Error Rate", sr.api_error_rate))
        lat = f"{sr.average_decision_latency_ms:.4f} ms / decision"
        lines.append(f"- **Average Decision Latency:** `{lat}`\n")
    else:
        lines.append("- **Safety Signals:** `N/A`\n")

    return "\n".join(lines)
