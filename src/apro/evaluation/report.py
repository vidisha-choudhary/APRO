"""Structured benchmark report generation in Markdown and JSON formats."""

import hashlib
import json

from apro.evaluation.models import BenchmarkReport


def compute_report_hash(report: BenchmarkReport) -> str:
    """Compute deterministic SHA-256 hash of the structured benchmark report."""
    dumped = report.model_dump()
    canonical_json = json.dumps(dumped, sort_keys=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def generate_json_report(report: BenchmarkReport) -> str:
    """Generate machine-readable JSON representation of the BenchmarkReport."""
    return json.dumps(report.model_dump(), indent=2)


def generate_markdown_report(report: BenchmarkReport) -> str:
    """Generate human-readable Markdown report from BenchmarkReport."""
    lines: list[str] = []
    kpis = report.primary_kpis
    safety = report.safety_metrics

    # Header
    lines.append("# APRO Phase 15 — Authoritative Benchmark Evaluation Report\n")
    lines.append(f"**Report ID:** `{report.report_id}`  ")
    lines.append(f"**Benchmark Run ID:** `{report.benchmark_run_id}`  ")
    lines.append(f"**Dataset ID:** `{report.dataset_id}` (v{report.dataset_version})  ")
    lines.append(f"**Dataset Snapshot Hash:** `{report.snapshot_hash}`  ")
    lines.append(
        f"**Evaluation Config Version:** `{report.evaluation_config_version}`  "
    )
    lines.append(f"**Metric Schema Version:** `{report.metric_schema_version}`  ")
    lines.append(f"**Code Revision:** `{report.code_revision}`  ")
    lines.append(f"**Generated At:** `{report.created_at}`\n")
    lines.append("---\n")

    # 1. Executive Summary
    lines.append("## 1. Executive Summary\n")
    lines.append(f"- **Eligible Cases Evaluated:** **{kpis.eligible_cases:,}**")
    lines.append(
        f"- **APRO Recovery Rate:** **{kpis.recovery_rate * 100:.2f}%** "
        f"({kpis.recovered_cases:,} / {kpis.eligible_cases:,})"
    )
    lines.append(f"- **Revenue at Risk:** ₹{kpis.eligible_at_risk_amount / 100:,.2f}")
    lines.append(
        f"- **Gross Revenue Recovered:** "
        f"**₹{kpis.gross_recovered_amount / 100:,.2f}** "
        f"({kpis.recovered_revenue_rate * 100:.2f}%)"
    )
    lines.append(
        f"- **Total Intervention Cost:** ₹{kpis.total_intervention_cost / 100:,.2f}"
    )
    lines.append(
        f"- **Net Recovered Revenue:** **₹{kpis.net_recovered_revenue / 100:,.2f}**"
    )
    cost_str = (
        f"₹{kpis.cost_per_recovered_rupee:.4f}"
        if kpis.cost_per_recovered_rupee is not None
        else "UNDEFINED (₹0 gross recovered)"
    )
    lines.append(f"- **Cost per Recovered Rupee:** `{cost_str}`")
    lines.append(
        f"- **Net Recovery Efficiency:** {kpis.net_recovery_efficiency * 100:.2f}%"
    )
    is_safe = safety.unsafe_dispatch_count == 0 and safety.policy_bypass_count == 0
    lines.append(
        f"- **Safety Invariant Status:** "
        f"**{'PASSED (0 Violations)' if is_safe else 'FAILED'}**\n"
    )

    # 2. Primary KPI Table
    lines.append("## 2. Primary KPI Table\n")
    lines.append(
        "| Metric | Value | Unit | Numerator | Denominator | 95% Confidence Interval |"
    )
    lines.append("|---|---|---|---|---|---|")
    rec_stat = report.statistical_results.get("recovery_rate")
    rec_ci_str = (
        f"[{rec_stat.ci_lower * 100:.2f}%, {rec_stat.ci_upper * 100:.2f}%]"
        if rec_stat
        else "N/A"
    )
    lines.append(
        f"| **Recovery Rate** | **{kpis.recovery_rate * 100:.2f}%** | Proportion | "
        f"{kpis.recovered_cases:,} cases | {kpis.eligible_cases:,} cases | "
        f"{rec_ci_str} |"
    )
    lines.append(
        f"| **Gross Recovered Revenue** | "
        f"₹{kpis.gross_recovered_amount / 100:,.2f} | INR | "
        f"{kpis.gross_recovered_amount:,} paise | "
        f"{kpis.eligible_at_risk_amount:,} paise | N/A |"
    )
    lines.append(
        f"| **Recovered Revenue Rate** | "
        f"{kpis.recovered_revenue_rate * 100:.2f}% | Proportion | "
        f"₹{kpis.gross_recovered_amount / 100:,.2f} | "
        f"₹{kpis.eligible_at_risk_amount / 100:,.2f} | N/A |"
    )
    lines.append(
        f"| **Total Intervention Cost** | "
        f"₹{kpis.total_intervention_cost / 100:,.2f} | INR | "
        f"{kpis.total_intervention_cost:,} paise | - | N/A |"
    )
    net_diff = kpis.gross_recovered_amount - kpis.total_intervention_cost
    lines.append(
        f"| **Net Recovered Revenue** | "
        f"₹{kpis.net_recovered_revenue / 100:,.2f} | INR | "
        f"₹{net_diff / 100:,.2f} | - | N/A |"
    )
    lines.append(
        f"| **Cost per Recovered Rupee** | {cost_str} | Ratio | "
        f"₹{kpis.total_intervention_cost / 100:,.2f} | "
        f"₹{kpis.gross_recovered_amount / 100:,.2f} | - |"
    )
    med_t = kpis.median_time_to_recovery_seconds or 0.0
    p25_t = kpis.p25_time_to_recovery_seconds or 0.0
    p75_t = kpis.p75_time_to_recovery_seconds or 0.0
    lines.append(
        f"| **Median Time to Recovery** | {med_t:.2f}s | Seconds | - | - | "
        f"[p25: {p25_t:.2f}s, p75: {p75_t:.2f}s] |"
    )
    att_m = kpis.attempts_per_case_mean
    att_med = kpis.attempts_per_case_median
    att_p90 = kpis.attempts_per_case_p90
    lines.append(
        f"| **Mean Attempts per Case** | {att_m:.2f} | Count | - | "
        f"{kpis.eligible_cases:,} cases | "
        f"[median: {att_med:.2f}, p90: {att_p90:.2f}] |\n"
    )

    # 3. Baseline Comparison Table
    lines.append("## 3. Baseline Comparison Table\n")
    lines.append(
        "| Baseline Strategy | Baseline Rate | APRO Rate | Absolute Delta | "
        "Relative Delta | Incremental Net Revenue | 95% CI (Delta Recovery) | "
        "Statistical Significance |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for b_name, b_res in report.baseline_comparisons.items():
        rel_str = (
            f"{b_res.relative_recovery_delta * 100:+.2f}%"
            if b_res.relative_recovery_delta is not None
            else "N/A"
        )
        ci_str = (
            f"[{b_res.delta_recovery_ci_95[0] * 100:+.2f}%, "
            f"{b_res.delta_recovery_ci_95[1] * 100:+.2f}%]"
        )
        sig_str = (
            "p < 0.05" if b_res.is_statistically_significant else "Not Significant"
        )
        lines.append(
            f"| **{b_name}** | {b_res.baseline_recovery_rate * 100:.2f}% | "
            f"{b_res.apro_recovery_rate * 100:.2f}% | "
            f"**{b_res.absolute_recovery_delta * 100:+.2f}%** | {rel_str} | "
            f"₹{b_res.incremental_net_revenue / 100:+,.2f} | {ci_str} | `{sig_str}` |"
        )
    lines.append("")

    # 4. Safety Table
    lines.append("## 4. Safety & Invariant Verification Table\n")
    lines.append(
        "| Safety Invariant | Observed Count | Observed Rate | Status | Threshold |"
    )
    lines.append("|---|---|---|---|---|")
    u_stat = "PASS" if safety.unsafe_dispatch_count == 0 else "FAIL"
    lines.append(
        f"| **Unsafe Dispatches** | **{safety.unsafe_dispatch_count}** | "
        f"{safety.unsafe_dispatch_rate * 100:.2f}% | {u_stat} | 0 (Hard Invariant) |"
    )
    p_stat = "PASS" if safety.policy_bypass_count == 0 else "FAIL"
    lines.append(
        f"| **Policy Bypasses** | **{safety.policy_bypass_count}** | 0.00% | "
        f"{p_stat} | 0 (Hard Invariant) |"
    )
    d_stat = "PASS" if safety.duplicate_execution_attempt_count == 0 else "FAIL"
    lines.append(
        f"| **Duplicate Executions** | "
        f"**{safety.duplicate_execution_attempt_count}** | "
        f"{safety.duplicate_execution_attempt_rate * 100:.2f}% | "
        f"{d_stat} | 0 (Idempotency Safe) |"
    )
    o_stat = "PASS" if safety.duplicate_outcome_count == 0 else "FAIL"
    lines.append(
        f"| **Duplicate Outcomes** | **{safety.duplicate_outcome_count}** | "
        f"{safety.duplicate_outcome_rate * 100:.2f}% | "
        f"{o_stat} | 0 (Audit Safe) |"
    )
    lines.append(
        f"| **StateGuard Rejections** | "
        f"**{safety.state_guard_rejection_count}** | "
        f"{safety.state_guard_rejection_rate * 100:.2f}% | OBSERVED | Policy Safe |"
    )
    lines.append(
        f"| **Stale Policy Rejections** | "
        f"**{safety.stale_policy_rejection_count}** | "
        f"{safety.stale_policy_rejection_rate * 100:.2f}% | OBSERVED | State Safe |"
    )
    c_stat = "PASS" if safety.credential_leakage_count == 0 else "FAIL"
    lines.append(
        f"| **Credential Leakage** | **{safety.credential_leakage_count}** | "
        f"0.00% | {c_stat} | 0 (Redacted) |\n"
    )

    # 5. Prediction Quality
    if report.prediction_quality is not None:
        pq = report.prediction_quality
        lines.append("## 5. Phase 8 Prediction Quality & Calibration\n")
        lines.append(f"- **Evaluated Predictions Sample Size:** {pq.sample_size:,}")
        lines.append(f"- **Brier Score:** **{pq.brier_score:.6f}** (lower is better)")
        if pq.roc_auc is not None:
            lines.append(f"- **ROC-AUC:** {pq.roc_auc:.4f}")
        if pq.f1_score is not None:
            lines.append(f"- **F1 Score:** {pq.f1_score:.4f}")
        if pq.log_loss is not None:
            lines.append(f"- **Log Loss:** {pq.log_loss:.4f}")

        if pq.calibration_curve:
            lines.append("\n### Calibration Curve Bins")
            lines.append(
                "| Bin Range | Samples | Predicted Mean Prob | Empirical Success Rate |"
            )
            lines.append("|---|---|---|---|")
            for bin_item in pq.calibration_curve:
                if bin_item.sample_count > 0:
                    lines.append(
                        f"| [{bin_item.bin_lower:.2f}, {bin_item.bin_upper:.2f}) | "
                        f"{bin_item.sample_count:,} | "
                        f"{bin_item.predicted_mean_probability:.4f} | "
                        f"{bin_item.empirical_success_rate:.4f} |"
                    )
            lines.append("")

    # 6. Decision Quality
    if report.decision_quality is not None:
        dq = report.decision_quality
        lines.append("## 6. Phase 9 Decision Engine Quality\n")
        lines.append(
            f"- **Average Candidate Actions per Decision:** "
            f"{dq.candidate_action_count_avg:.2f}"
        )
        lines.append(
            f"- **Average Selected Action ERV:** "
            f"₹{dq.selected_action_erv_avg / 100:,.2f}"
        )
        lines.append(
            f"- **Average Selected Action Cost:** "
            f"₹{dq.selected_action_cost_avg / 100:,.2f}"
        )
        if dq.best_action_selection_rate is not None:
            lines.append(
                f"- **Optimal Action Selection Rate (Counterfactual):** "
                f"{dq.best_action_selection_rate * 100:.2f}%"
            )
        if dq.action_regret_avg is not None:
            lines.append(
                f"- **Average Counterfactual Action Regret:** "
                f"₹{dq.action_regret_avg / 100:,.2f}"
            )
        lines.append("\n**Selected Action Distribution:**")
        for act, count in dq.selected_action_distribution.items():
            lines.append(f"- `{act}`: {count:,} cases")
        lines.append("")

    # 7. Adaptive Recovery Analysis
    if report.adaptive_loop_metrics is not None:
        ad = report.adaptive_loop_metrics
        lines.append("## 7. Phase 13 Adaptive Recovery Loop Evaluation\n")
        lines.append(
            f"- **Single-Cycle Recovery Rate:** "
            f"{ad.single_cycle_recovery_rate * 100:.2f}% "
            f"({ad.single_cycle_recovery_count:,} cases)"
        )
        lines.append(
            f"- **Multi-Cycle Adaptive Recovery Rate:** "
            f"**{ad.multi_cycle_recovery_rate * 100:.2f}%** "
            f"({ad.multi_cycle_recovery_count:,} cases)"
        )
        lines.append(
            f"- **Recovery After Re-Evaluation Rate:** "
            f"{ad.recovery_after_re_evaluation_rate * 100:.2f}%"
        )
        lines.append(
            f"- **Incremental Recovery After First Failure:** "
            f"{ad.incremental_recovery_after_first_failure * 100:.2f}%"
        )
        lines.append(
            f"- **Same-Action Avoidance Rate:** "
            f"{ad.same_action_avoidance_rate * 100:.2f}%"
        )
        lines.append(
            f"- **Bounded Loop Termination Rate:** "
            f"{ad.bounded_termination_rate * 100:.2f}%\n"
        )

    # 8. Cohort Analysis
    if report.cohort_breakdowns:
        lines.append("## 8. Cohort & Segment Breakdown\n")
        for dim, breakdowns in report.cohort_breakdowns.items():
            lines.append(f"### Breakdown by `{dim}`")
            lines.append(
                "| Segment | Cases | Recovery Rate | Gross Recovered | "
                "Net Recovered | Small Cohort Flag |"
            )
            lines.append("|---|---|---|---|---|---|")
            for b in breakdowns:
                small_flag = "⚠️ `< 5 cases`" if b.is_small_cohort else "Normal"
                lines.append(
                    f"| **{b.cohort_key}** | {b.case_count:,} | "
                    f"{b.recovery_rate * 100:.2f}% | "
                    f"₹{b.gross_recovered / 100:,.2f} | "
                    f"₹{b.net_recovered / 100:,.2f} | {small_flag} |"
                )
            lines.append("")

    # 9. Limitations
    lines.append("## 9. Evaluation Limitations & Scope\n")
    if report.limitations:
        for lim in report.limitations:
            lines.append(f"- {lim}")
    else:
        lines.append("- Observational comparisons do not establish causal impact.")
        lines.append(
            "- Provider dispatch is simulated/stubbed in offline benchmark mode."
        )
        lines.append("- Counterfactual labels reflect evaluation ground truth.")
    lines.append("")

    # 10. Reproducibility Metadata
    lines.append("## 10. Reproducibility Metadata\n")
    lines.append(
        f"```json\n{json.dumps(report.reproducibility_metadata, indent=2)}\n```\n"
    )

    return "\n".join(lines)
