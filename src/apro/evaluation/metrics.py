"""Pure deterministic formulas for Phase 15 primary, safety, and operational KPIs."""

import statistics

from pydantic import BaseModel, ConfigDict, Field

from apro.domain.enums import ExecutionStatus, OutcomeType, PolicyDecisionResult
from apro.evaluation.config import EvaluationConfig
from apro.evaluation.enums import TerminalDisposition
from apro.evaluation.models import (
    BenchmarkCaseRecord,
    PrimaryKPISet,
    SafetyKPISet,
)
from apro.evaluation.traces import CaseEvaluationTrace
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedOutcomeStatus,
)


def compute_primary_kpis(
    records: list[BenchmarkCaseRecord],
    config: EvaluationConfig,
) -> PrimaryKPISet:
    """Compute pure deterministic Primary KPIs for an eligible case cohort."""
    n = len(records)
    if n == 0:
        return PrimaryKPISet(
            case_count=0,
            eligible_cases=0,
            recovered_cases=0,
            recovery_rate=0.0,
            eligible_at_risk_amount=0,
            gross_recovered_amount=0,
            recovered_revenue_rate=0.0,
            total_intervention_cost=0,
            net_recovered_revenue=0,
            cost_per_recovered_rupee=None,
            net_recovery_efficiency=0.0,
            mean_time_to_recovery_seconds=None,
            median_time_to_recovery_seconds=None,
            p25_time_to_recovery_seconds=None,
            p75_time_to_recovery_seconds=None,
            p90_time_to_recovery_seconds=None,
            attempts_per_case_mean=0.0,
            attempts_per_case_median=0.0,
            attempts_per_case_p90=0.0,
            cycle_count_total=0,
            re_evaluation_count_total=0,
            same_action_repetition_count=0,
            terminal_disposition_mix={d.value: 0 for d in TerminalDisposition},
        )

    at_risk_amount = sum(r.payment_amount for r in records)
    recovered_cases = 0
    gross_recovered = 0
    total_cost = 0
    recovery_times: list[float] = []
    attempts_per_case: list[int] = []
    total_cycles = 0
    total_reevals = 0
    same_action_repeats = 0
    disposition_counts: dict[str, int] = {d.value: 0 for d in TerminalDisposition}

    for r in records:
        attempts = len(r.executions) if r.executions else r.intervention_count
        attempts_per_case.append(attempts)
        total_cycles += max(1, r.cycle_count)
        total_reevals += r.re_evaluation_count

        if len(r.executions) > 1:
            actions = [e.execution_type for e in r.executions]
            for i in range(1, len(actions)):
                if actions[i] == actions[i - 1] and actions[i] != "STOP":
                    same_action_repeats += 1

        if r.executions:
            for ex in r.executions:
                if ex.execution_type != "STOP":
                    total_cost += config.cost_model.get_action_cost(ex.execution_type)
        else:
            total_cost += r.intervention_count * config.cost_model.retry_cost

        is_rec = False
        rec_amt = 0

        if r.outcomes:
            seen_outcomes: set[str] = set()
            for out in r.outcomes:
                if out.outcome_id in seen_outcomes:
                    continue
                seen_outcomes.add(out.outcome_id)

                out_type_str = (
                    out.type.value if hasattr(out.type, "value") else str(out.type)
                )
                if out_type_str in ("RECOVERED", OutcomeType.RECOVERED.value):
                    is_rec = True
                    rec_amt += out.amount_recovered
        elif r.is_recovered:
            is_rec = True
            rec_amt = r.recovered_amount

        rec_amt = min(rec_amt, r.payment_amount) if is_rec else 0

        if is_rec and rec_amt > 0:
            recovered_cases += 1
            gross_recovered += rec_amt
            if r.duration_seconds is not None and r.duration_seconds >= 0:
                recovery_times.append(r.duration_seconds)
            elif r.closed_at and r.opened_at:
                dur = (r.closed_at - r.opened_at).total_seconds()
                if dur >= 0:
                    recovery_times.append(dur)

        clean_status = r.case_status.upper()
        if is_rec:
            disposition_counts[TerminalDisposition.RECOVERED.value] += 1
        elif "STOP" in clean_status:
            disposition_counts[TerminalDisposition.STOPPED.value] += 1
        elif "ESCALAT" in clean_status:
            disposition_counts[TerminalDisposition.ESCALATED.value] += 1
        elif "PENDING" in clean_status or "OPEN" in clean_status:
            disposition_counts[TerminalDisposition.PENDING_WAITING.value] += 1
        else:
            disposition_counts[TerminalDisposition.UNKNOWN.value] += 1

    recovery_rate = recovered_cases / n
    rev_rate = (gross_recovered / at_risk_amount) if at_risk_amount > 0 else 0.0
    net_revenue = gross_recovered - total_cost

    cost_per_rupee = (total_cost / gross_recovered) if gross_recovered > 0 else None
    efficiency = (net_revenue / at_risk_amount) if at_risk_amount > 0 else 0.0

    mean_time: float | None = None
    median_time: float | None = None
    p25_time: float | None = None
    p75_time: float | None = None
    p90_time: float | None = None

    if recovery_times:
        recovery_times.sort()
        mean_time = round(statistics.mean(recovery_times), 2)
        median_time = round(statistics.median(recovery_times), 2)
        p25_time = (
            round(statistics.quantiles(recovery_times, n=4)[0], 2)
            if len(recovery_times) >= 4
            else median_time
        )
        p75_time = (
            round(statistics.quantiles(recovery_times, n=4)[2], 2)
            if len(recovery_times) >= 4
            else median_time
        )
        p90_time = (
            round(statistics.quantiles(recovery_times, n=10)[8], 2)
            if len(recovery_times) >= 10
            else median_time
        )

    attempts_per_case.sort()
    att_mean = round(statistics.mean(attempts_per_case), 2)
    att_median = round(statistics.median(attempts_per_case), 2)
    att_p90 = (
        round(statistics.quantiles(attempts_per_case, n=10)[8], 2)
        if len(attempts_per_case) >= 10
        else att_median
    )

    return PrimaryKPISet(
        case_count=n,
        eligible_cases=n,
        recovered_cases=recovered_cases,
        recovery_rate=round(recovery_rate, 4),
        eligible_at_risk_amount=at_risk_amount,
        gross_recovered_amount=gross_recovered,
        recovered_revenue_rate=round(rev_rate, 4),
        total_intervention_cost=total_cost,
        net_recovered_revenue=net_revenue,
        cost_per_recovered_rupee=(
            round(cost_per_rupee, 4) if cost_per_rupee is not None else None
        ),
        net_recovery_efficiency=round(efficiency, 4),
        mean_time_to_recovery_seconds=mean_time,
        median_time_to_recovery_seconds=median_time,
        p25_time_to_recovery_seconds=p25_time,
        p75_time_to_recovery_seconds=p75_time,
        p90_time_to_recovery_seconds=p90_time,
        attempts_per_case_mean=att_mean,
        attempts_per_case_median=att_median,
        attempts_per_case_p90=att_p90,
        cycle_count_total=total_cycles,
        re_evaluation_count_total=total_reevals,
        same_action_repetition_count=same_action_repeats,
        terminal_disposition_mix=disposition_counts,
    )


def compute_safety_kpis(
    records: list[BenchmarkCaseRecord],
    _config: EvaluationConfig | None = None,
) -> SafetyKPISet:
    """Compute pure deterministic Safety & Operational Reliability KPIs."""
    n = max(1, len(records))

    policy_blocks = 0
    state_guard_rejections = 0
    stale_policy_rejections = 0
    unknown_transport = 0
    duplicate_executions = 0
    duplicate_outcomes = 0
    terminal_reopens = 0
    unsafe_dispatches = 0
    policy_bypasses = 0
    credential_leakages = 0

    for r in records:
        for pd in r.policy_decisions:
            res_str = pd.result.value if hasattr(pd.result, "value") else str(pd.result)
            if res_str in (PolicyDecisionResult.BLOCK.value, "BLOCK", "BLOCKED"):
                policy_blocks += 1
            if "state_guard" in pd.reason.lower():
                state_guard_rejections += 1
            if "stale" in pd.reason.lower():
                state_guard_rejections += 1
                stale_policy_rejections += 1

        seen_exec_actions: set[str] = set()
        for ex in r.executions:
            stat_str = (
                ex.status.value if hasattr(ex.status, "value") else str(ex.status)
            )
            if stat_str in (ExecutionStatus.UNKNOWN.value, "UNKNOWN"):
                unknown_transport += 1
            if ex.action_id in seen_exec_actions:
                duplicate_executions += 1
            seen_exec_actions.add(ex.action_id)

            if not r.policy_decisions and ex.execution_type != "STOP":
                unsafe_dispatches += 1
                policy_bypasses += 1

        seen_outcome_ids: set[str] = set()
        for out in r.outcomes:
            if out.outcome_id in seen_outcome_ids:
                duplicate_outcomes += 1
            seen_outcome_ids.add(out.outcome_id)

    return SafetyKPISet(
        policy_block_count=policy_blocks,
        policy_block_rate=round(policy_blocks / n, 4),
        state_guard_rejection_count=state_guard_rejections,
        state_guard_rejection_rate=round(state_guard_rejections / n, 4),
        stale_policy_rejection_count=stale_policy_rejections,
        stale_policy_rejection_rate=round(stale_policy_rejections / n, 4),
        provider_transport_unknown_count=unknown_transport,
        provider_transport_unknown_rate=round(unknown_transport / n, 4),
        duplicate_execution_attempt_count=duplicate_executions,
        duplicate_execution_attempt_rate=round(duplicate_executions / n, 4),
        duplicate_outcome_count=duplicate_outcomes,
        duplicate_outcome_rate=round(duplicate_outcomes / n, 4),
        terminal_case_reopen_attempt_count=terminal_reopens,
        terminal_case_reopen_attempt_rate=round(terminal_reopens / n, 4),
        unsafe_dispatch_count=unsafe_dispatches,
        unsafe_dispatch_rate=round(unsafe_dispatches / n, 4),
        policy_bypass_count=policy_bypasses,
        credential_leakage_count=credential_leakages,
    )


# ---------------------------------------------------------------------------
# Phase 6 Legacy Simulation Compatibility Metric Schemas & Functions
# ---------------------------------------------------------------------------


class EconomicMetrics(BaseModel):
    """Monetary efficiency metrics for Phase 6 legacy evaluation."""

    model_config = ConfigDict(frozen=True)

    revenue_at_risk: int = Field(ge=0)
    revenue_recovered: int = Field(ge=0)
    incremental_revenue_recovered: int = Field()
    recovery_rate: float = Field(ge=0.0, le=1.0)
    intervention_count: int = Field(ge=0)
    intervention_rate: float = Field(ge=0.0, le=1.0)
    recovered_revenue_per_intervention: float = Field(ge=0.0)
    unnecessary_intervention_count: int = Field(ge=0)
    unnecessary_intervention_rate: float = Field(ge=0.0, le=1.0)
    stop_count: int = Field(ge=0)
    stop_rate: float = Field(ge=0.0, le=1.0)
    escalation_count: int = Field(ge=0)
    escalation_rate: float = Field(ge=0.0, le=1.0)


class DecisionMetrics(BaseModel):
    """Counterfactual decision quality metrics for Phase 6 legacy evaluation."""

    model_config = ConfigDict(frozen=True)

    optimal_action_count: int = Field(ge=0)
    optimal_action_rate: float = Field(ge=0.0, le=1.0)
    total_regret: int = Field(ge=0)
    average_regret: float = Field(ge=0.0)
    expected_value_capture: float = Field(ge=0.0, le=1.0)
    action_selection_accuracy: float = Field(ge=0.0, le=1.0)


class SafetyReliabilityMetrics(BaseModel):
    """Safety and reliability signal schema for Phase 6 legacy evaluation."""

    model_config = ConfigDict(frozen=True)

    policy_violation_count: int | None = Field(default=None)
    duplicate_execution_count: int | None = Field(default=None)
    captured_payment_intervention_count: int | None = Field(default=None)
    retry_limit_violation_count: int | None = Field(default=None)
    invalid_model_execution_count: int | None = Field(default=None)
    unknown_state_unsafe_execution_count: int | None = Field(default=None)
    webhook_processing_success_rate: float | None = Field(default=None)
    event_deduplication_rate: float | None = Field(default=None)
    decision_success_rate: float | None = Field(default=None)
    execution_success_rate: float | None = Field(default=None)
    unknown_execution_rate: float | None = Field(default=None)
    api_error_rate: float | None = Field(default=None)
    average_decision_latency_ms: float = Field(default=0.0, ge=0.0)


class EvaluationMetrics(BaseModel):
    """Consolidated metric report for Phase 6 legacy evaluation."""

    model_config = ConfigDict(frozen=True)

    case_count: int = Field(ge=0)
    economic: EconomicMetrics
    decision: DecisionMetrics
    safety_reliability: SafetyReliabilityMetrics


def calculate_metrics(
    traces: list[CaseEvaluationTrace],
    baseline_revenue_recovered: int = 0,
) -> EvaluationMetrics:
    """Compute evaluation metrics from traces (Phase 6 legacy)."""
    n = len(traces)
    if n == 0:
        return EvaluationMetrics(
            case_count=0,
            economic=EconomicMetrics(
                revenue_at_risk=0,
                revenue_recovered=0,
                incremental_revenue_recovered=0,
                recovery_rate=0.0,
                intervention_count=0,
                intervention_rate=0.0,
                recovered_revenue_per_intervention=0.0,
                unnecessary_intervention_count=0,
                unnecessary_intervention_rate=0.0,
                stop_count=0,
                stop_rate=0.0,
                escalation_count=0,
                escalation_rate=0.0,
            ),
            decision=DecisionMetrics(
                optimal_action_count=0,
                optimal_action_rate=0.0,
                total_regret=0,
                average_regret=0.0,
                expected_value_capture=1.0,
                action_selection_accuracy=0.0,
            ),
            safety_reliability=SafetyReliabilityMetrics(
                average_decision_latency_ms=0.0
            ),
        )

    rev_at_risk = sum(t.payment_amount for t in traces)
    rev_recovered = sum(t.recovered_amount for t in traces)
    incremental_rev = rev_recovered - baseline_revenue_recovered
    recovered_cases = sum(
        1 for t in traces if t.outcome_status == SimulatedOutcomeStatus.SUCCESS
    )
    recovery_rate = recovered_cases / n

    interventions = sum(1 for t in traces if t.is_intervention)
    intervention_rate = interventions / n
    rev_per_intervention = (rev_recovered / interventions) if interventions > 0 else 0.0

    unnecessary_interventions = sum(1 for t in traces if t.is_unnecessary_intervention)
    unnecessary_intervention_rate = unnecessary_interventions / n

    stops = sum(1 for t in traces if t.chosen_action == SimulatedActionType.STOP)
    stop_rate = stops / n
    escalations = sum(
        1 for t in traces if t.chosen_action == SimulatedActionType.ESCALATE
    )
    escalation_rate = escalations / n

    optimal_cases = sum(1 for t in traces if t.is_optimal)
    optimal_rate = optimal_cases / n
    total_regret = sum(t.regret for t in traces)
    avg_regret = total_regret / n

    total_best_value = sum(t.best_achievable_value for t in traces)
    if total_best_value > 0:
        ev_capture = min(1.0, max(0.0, rev_recovered / total_best_value))
    else:
        ev_capture = 1.0 if rev_recovered == 0 else 0.0

    avg_latency = sum(t.decision_latency_ms for t in traces) / n

    return EvaluationMetrics(
        case_count=n,
        economic=EconomicMetrics(
            revenue_at_risk=rev_at_risk,
            revenue_recovered=rev_recovered,
            incremental_revenue_recovered=incremental_rev,
            recovery_rate=round(recovery_rate, 4),
            intervention_count=interventions,
            intervention_rate=round(intervention_rate, 4),
            recovered_revenue_per_intervention=round(rev_per_intervention, 2),
            unnecessary_intervention_count=unnecessary_interventions,
            unnecessary_intervention_rate=round(unnecessary_intervention_rate, 4),
            stop_count=stops,
            stop_rate=round(stop_rate, 4),
            escalation_count=escalations,
            escalation_rate=round(escalation_rate, 4),
        ),
        decision=DecisionMetrics(
            optimal_action_count=optimal_cases,
            optimal_action_rate=round(optimal_rate, 4),
            total_regret=total_regret,
            average_regret=round(avg_regret, 2),
            expected_value_capture=round(ev_capture, 4),
            action_selection_accuracy=round(optimal_rate, 4),
        ),
        safety_reliability=SafetyReliabilityMetrics(
            average_decision_latency_ms=round(avg_latency, 3)
        ),
    )
