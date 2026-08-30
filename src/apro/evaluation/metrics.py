"""Economic, decision-quality, and safety metric computation for APRO Phase 6."""

from pydantic import BaseModel, ConfigDict, Field

from apro.evaluation.traces import CaseEvaluationTrace
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedOutcomeStatus,
)


class EconomicMetrics(BaseModel):
    """Monetary and intervention efficiency metrics computed from evaluation."""

    model_config = ConfigDict(frozen=True)

    revenue_at_risk: int = Field(
        ge=0, description="Total payment amount at risk in minor units"
    )
    revenue_recovered: int = Field(
        ge=0, description="Total amount recovered in minor units"
    )
    incremental_revenue_recovered: int = Field(
        description="Revenue recovered minus baseline recovered in minor units"
    )
    recovery_rate: float = Field(
        ge=0.0, le=1.0, description="Recovered cases / eligible cases"
    )
    intervention_count: int = Field(
        ge=0, description="Number of actions taken where action != STOP"
    )
    intervention_rate: float = Field(
        ge=0.0, le=1.0, description="Intervention cases / eligible cases"
    )
    recovered_revenue_per_intervention: float = Field(
        ge=0.0, description="Revenue recovered / intervention count"
    )
    unnecessary_intervention_count: int = Field(
        ge=0,
        description="Interventions on non-recoverable or where STOP yields same",
    )
    unnecessary_intervention_rate: float = Field(
        ge=0.0, le=1.0, description="Unnecessary interventions / eligible cases"
    )
    stop_count: int = Field(ge=0)
    stop_rate: float = Field(ge=0.0, le=1.0)
    escalation_count: int = Field(ge=0)
    escalation_rate: float = Field(ge=0.0, le=1.0)


class DecisionMetrics(BaseModel):
    """Counterfactual decision quality metrics evaluated against ground truth."""

    model_config = ConfigDict(frozen=True)

    optimal_action_count: int = Field(ge=0)
    optimal_action_rate: float = Field(
        ge=0.0, le=1.0, description="Optimal action cases / eligible cases"
    )
    total_regret: int = Field(
        ge=0, description="Sum of (best_achievable_value - recovered_value)"
    )
    average_regret: float = Field(ge=0.0, description="Total regret / eligible cases")
    expected_value_capture: float = Field(
        ge=0.0,
        le=1.0,
        description="Recovered revenue / total best achievable revenue",
    )
    action_selection_accuracy: float = Field(ge=0.0, le=1.0)


class SafetyReliabilityMetrics(BaseModel):
    """Safety and reliability signal schema for benchmark evaluation.

    Phase 6 Note:
    Subsystems not yet implemented in Phase 6 (e.g. Policy Engine, Execution)
    are explicitly marked None / unavailable rather than fabricating zero.
    """

    model_config = ConfigDict(frozen=True)

    policy_violation_count: int | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    duplicate_execution_count: int | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    captured_payment_intervention_count: int | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    retry_limit_violation_count: int | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    invalid_model_execution_count: int | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    unknown_state_unsafe_execution_count: int | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    webhook_processing_success_rate: float | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    event_deduplication_rate: float | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    decision_success_rate: float | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    execution_success_rate: float | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    unknown_execution_rate: float | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    api_error_rate: float | None = Field(
        default=None, description="Unavailable in Phase 6"
    )
    average_decision_latency_ms: float = Field(default=0.0, ge=0.0)


class EvaluationMetrics(BaseModel):
    """Consolidated metric report for evaluation."""

    model_config = ConfigDict(frozen=True)

    case_count: int = Field(ge=0)
    economic: EconomicMetrics
    decision: DecisionMetrics
    safety_reliability: SafetyReliabilityMetrics


def calculate_metrics(
    traces: list[CaseEvaluationTrace],
    baseline_revenue_recovered: int = 0,
) -> EvaluationMetrics:
    """Compute consolidated evaluation metrics from case evaluation traces."""
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

    # 1. Economic Metrics
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

    # 2. Decision Metrics
    optimal_cases = sum(1 for t in traces if t.is_optimal)
    optimal_rate = optimal_cases / n
    total_regret = sum(t.regret for t in traces)
    avg_regret = total_regret / n

    total_best_value = sum(t.best_achievable_value for t in traces)
    if total_best_value > 0:
        ev_capture = min(1.0, max(0.0, rev_recovered / total_best_value))
    else:
        ev_capture = 1.0 if rev_recovered == 0 else 0.0

    # 3. Latency
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
