"""Statistical multi-seed aggregation and subgroup evaluation for APRO Phase 6."""

import math
import statistics
from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field

from apro.evaluation.metrics import EvaluationMetrics, calculate_metrics
from apro.evaluation.traces import CaseEvaluationTrace


class MultiSeedStats(BaseModel):
    """Statistical summary across multiple independent benchmark seed runs."""

    model_config = ConfigDict(frozen=True)

    mean: float
    median: float
    std_dev: float
    min_val: float
    max_val: float
    ci_95_lower: float = Field(description="95% CI lower bound")
    ci_95_upper: float = Field(description="95% CI upper bound")


def compute_multi_seed_stats(values: list[float]) -> MultiSeedStats:
    """Compute summary statistics and 95% CI for metric observations."""
    n = len(values)
    if n == 0:
        return MultiSeedStats(
            mean=0.0,
            median=0.0,
            std_dev=0.0,
            min_val=0.0,
            max_val=0.0,
            ci_95_lower=0.0,
            ci_95_upper=0.0,
        )

    mean_val = statistics.mean(values)
    median_val = statistics.median(values)
    min_val = min(values)
    max_val = max(values)

    if n > 1:
        std_val = statistics.stdev(values)
        margin = 1.96 * (std_val / math.sqrt(n))
        ci_lower = round(mean_val - margin, 4)
        ci_upper = round(mean_val + margin, 4)
    else:
        std_val = 0.0
        ci_lower = round(mean_val, 4)
        ci_upper = round(mean_val, 4)

    return MultiSeedStats(
        mean=round(mean_val, 4),
        median=round(median_val, 4),
        std_dev=round(std_val, 4),
        min_val=round(min_val, 4),
        max_val=round(max_val, 4),
        ci_95_lower=ci_lower,
        ci_95_upper=ci_upper,
    )


def aggregate_multi_seed_metrics(
    seed_metric_map: dict[int, EvaluationMetrics],
) -> dict[str, MultiSeedStats]:
    """Aggregate per-seed metric observations into multi-seed statistical summaries."""
    if not seed_metric_map:
        return {}

    metric_arrays: dict[str, list[float]] = defaultdict(list)
    for _seed, m in seed_metric_map.items():
        metric_arrays["recovery_rate"].append(m.economic.recovery_rate)
        metric_arrays["revenue_recovered"].append(float(m.economic.revenue_recovered))
        metric_arrays["incremental_revenue_recovered"].append(
            float(m.economic.incremental_revenue_recovered)
        )
        metric_arrays["intervention_rate"].append(m.economic.intervention_rate)
        metric_arrays["unnecessary_intervention_rate"].append(
            m.economic.unnecessary_intervention_rate
        )
        metric_arrays["recovered_revenue_per_intervention"].append(
            m.economic.recovered_revenue_per_intervention
        )
        metric_arrays["optimal_action_rate"].append(m.decision.optimal_action_rate)
        metric_arrays["expected_value_capture"].append(
            m.decision.expected_value_capture
        )
        metric_arrays["average_regret"].append(m.decision.average_regret)
        metric_arrays["stop_rate"].append(m.economic.stop_rate)
        metric_arrays["escalation_rate"].append(m.economic.escalation_rate)

    return {
        metric_name: compute_multi_seed_stats(vals)
        for metric_name, vals in metric_arrays.items()
    }


def aggregate_by_segment(
    traces: list[CaseEvaluationTrace],
    dimension: str,
    baseline_recovered_by_segment: dict[str, int] | None = None,
) -> dict[str, EvaluationMetrics]:
    """Segment traces by dimensional attribute and compute metrics per segment."""
    grouped: dict[str, list[CaseEvaluationTrace]] = defaultdict(list)
    base_map = baseline_recovered_by_segment or {}

    for t in traces:
        if dimension == "scenario_family":
            key = t.scenario_family.value
        elif dimension == "recoverability":
            key = t.recoverability.value
        elif dimension == "customer_behavior":
            key = t.customer_behavior.value
        elif dimension == "payment_value_tier":
            key = t.payment_value_tier.value
        elif dimension == "scenario_difficulty":
            key = t.scenario_difficulty.value
        elif dimension == "chosen_action":
            key = t.chosen_action.value
        elif dimension == "seed":
            key = str(t.seed)
        else:
            key = "all"
        grouped[key].append(t)

    results: dict[str, EvaluationMetrics] = {}
    for segment_key, seg_traces in grouped.items():
        base_rev = base_map.get(segment_key, 0)
        results[segment_key] = calculate_metrics(
            seg_traces, baseline_revenue_recovered=base_rev
        )

    return results
