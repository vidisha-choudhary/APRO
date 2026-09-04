"""Deterministic cohort segmentation and subgroup evaluation for Phase 15."""

from collections import defaultdict

from apro.evaluation.config import EvaluationConfig
from apro.evaluation.models import (
    BenchmarkCaseRecord,
    CohortBreakdown,
)


def get_amount_bucket(amount_paise: int) -> str:
    """Classify payment amount into standard financial tiers."""
    if amount_paise <= 100000:  # <= ₹1,000
        return "LOW_VALUE (<= ₹1,000)"
    if amount_paise <= 500000:  # <= ₹5,000
        return "MEDIUM_VALUE (₹1,000 - ₹5,000)"
    return "HIGH_VALUE (> ₹5,000)"


def segment_cases(
    records: list[BenchmarkCaseRecord],
    dimension: str,
    config: EvaluationConfig,
) -> list[CohortBreakdown]:
    """Segment benchmark records by a single dimension and compute cohort metrics."""
    grouped: dict[str, list[BenchmarkCaseRecord]] = defaultdict(list)

    for r in records:
        if dimension == "payment_method":
            key = str(r.payment_method).upper()
        elif dimension == "amount_bucket":
            key = get_amount_bucket(r.payment_amount)
        elif dimension == "failure_category":
            key = str(r.failure_category or "UNKNOWN").upper()
        elif dimension == "selected_action":
            act = r.final_action_type or (
                r.executions[-1].execution_type if r.executions else "STOP"
            )
            key = str(act).upper()
        elif dimension == "final_disposition":
            key = str(r.terminal_disposition).upper()
        elif dimension == "initial_attempt_count":
            key = f"attempts_{len(r.executions)}"
        elif dimension == "execution_mode":
            mode = r.executions[0].execution_mode if r.executions else "SIMULATION"
            key = str(mode).upper()
        else:
            key = "ALL"

        grouped[key].append(r)

    breakdowns: list[CohortBreakdown] = []
    min_size = config.minimum_cohort_size

    for key, cohort_records in sorted(grouped.items(), key=lambda item: item[0]):
        n_c = len(cohort_records)
        is_small = n_c < min_size
        rec_count = sum(
            1 for cr in cohort_records if (cr.is_recovered and cr.recovered_amount > 0)
        )
        rec_rate = round(rec_count / n_c, 4) if n_c > 0 else 0.0
        gross_rev = sum(cr.recovered_amount for cr in cohort_records if cr.is_recovered)

        # Cohort intervention cost
        cost = 0
        for cr in cohort_records:
            if cr.executions:
                for ex in cr.executions:
                    if ex.execution_type != "STOP":
                        cost += config.cost_model.get_action_cost(ex.execution_type)
            else:
                cost += cr.intervention_count * config.cost_model.retry_cost
        net_rev = gross_rev - cost

        # Mean time to recovery in cohort
        durs = [
            cr.duration_seconds
            for cr in cohort_records
            if cr.is_recovered
            and cr.duration_seconds is not None
            and cr.duration_seconds >= 0
        ]
        mean_dur = round(sum(durs) / len(durs), 2) if durs else None

        breakdowns.append(
            CohortBreakdown(
                dimension=dimension,
                cohort_key=key,
                case_count=n_c,
                is_small_cohort=is_small,
                recovery_rate=rec_rate,
                gross_recovered=gross_rev,
                net_recovered=net_rev,
                mean_time_to_recovery=mean_dur,
            )
        )

    return breakdowns


def compute_all_cohort_breakdowns(
    records: list[BenchmarkCaseRecord],
    config: EvaluationConfig,
) -> dict[str, list[CohortBreakdown]]:
    """Compute all required Phase 15 cohort breakdowns."""
    dimensions = [
        "failure_category",
        "selected_action",
        "payment_method",
        "amount_bucket",
    ]

    results: dict[str, list[CohortBreakdown]] = {}
    for dim in dimensions:
        results[dim] = segment_cases(records, dim, config)

    return results
