"""Pydantic data transfer objects and schemas for Phase 16 Live Dashboard API."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CommonResponseMetadata(BaseModel):
    """Common operational metadata returned by all dashboard API endpoints."""

    model_config = ConfigDict(frozen=True)

    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    source_revision: str = "b2fedab"
    data_version: str = "1.0.0"
    query_scope: str = "EVALUATION_PLANE"
    benchmark_run_id: str | None = None
    report_hash: str | None = None


class DashboardOverviewKPIs(BaseModel):
    """Aggregate high-level operational KPIs for the operations overview widget."""

    model_config = ConfigDict(frozen=True)

    eligible_cases: int
    recovered_cases: int
    recovery_rate: float
    gross_recovered_revenue: int
    net_recovered_revenue: int
    total_intervention_cost: int
    cost_per_recovered_rupee: float | None = None
    median_time_to_recovery_seconds: float | None = None
    mean_cycles_to_recovery: float | None = None
    safety_status: str
    latest_benchmark_run_id: str
    dataset_id: str
    dataset_version: str
    is_synthetic_demo: bool = False
    last_updated_at: str


class OverviewResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/overview."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    data: DashboardOverviewKPIs | None = None
    message: str | None = None


class FunnelStageData(BaseModel):
    """Single stage count and conversion metric in the recovery funnel."""

    model_config = ConfigDict(frozen=True)

    stage_name: str
    count: int | None = None
    percentage: float | None = None
    dropoff_count: int | None = None
    dropoff_percentage: float | None = None


class FunnelResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/funnel."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    data: list[FunnelStageData] = Field(default_factory=list)


class BaselineComparisonDTO(BaseModel):
    """Comparison metrics between APRO and a specific baseline policy."""

    model_config = ConfigDict(frozen=True)

    baseline_type: str
    baseline_name: str
    baseline_version: str
    apro_recovery_rate: float
    baseline_recovery_rate: float
    absolute_recovery_delta: float
    relative_recovery_delta: float | None = None
    apro_gross_recovered: int
    baseline_gross_recovered: int
    incremental_recovered_amount: int
    apro_net_recovered: int
    baseline_net_recovered: int
    incremental_net_revenue: int
    apro_intervention_cost: int
    baseline_intervention_cost: int
    delta_recovery_ci_95: list[float] | None = None
    delta_net_revenue_ci_95: list[float] | None = None
    p_value: float | None = None
    adjusted_p_value: float | None = None
    comparison_label: str
    is_statistically_significant: bool


class BenchmarksResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/benchmarks."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    data: list[BaselineComparisonDTO] = Field(default_factory=list)
    multiplicity_policy: str | None = "HOLM"


class CalibrationBinDTO(BaseModel):
    """Empirical calibration bin mapping predicted probabilities to actual recovery."""

    model_config = ConfigDict(frozen=True)

    bin_index: int
    bin_lower: float
    bin_upper: float
    sample_count: int
    mean_predicted_prob: float
    empirical_recovery_rate: float


class ClassificationMetricsDTO(BaseModel):
    """Standard statistical classification metrics for recovery prediction."""

    model_config = ConfigDict(frozen=True)

    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    roc_auc: float | None = None
    pr_auc: float | None = None
    log_loss: float | None = None


class DecisionQualityDTO(BaseModel):
    """Authoritative Phase 15 decision quality and counterfactual regret metrics."""

    model_config = ConfigDict(frozen=True)

    action_regret_avg: float | None = None
    oracle_gap_avg: float | None = None
    best_action_selection_rate: float | None = None


class PredictionQualityResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/prediction-quality."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    brier_score: float | None = None
    calibration_bins: list[CalibrationBinDTO] = Field(default_factory=list)
    classification_metrics: ClassificationMetricsDTO | None = None
    decision_quality: DecisionQualityDTO | None = None


class AdaptiveCycleDistributionDTO(BaseModel):
    """Case count and proportion for a specific adaptive cycle count."""

    model_config = ConfigDict(frozen=True)

    cycle_number: int
    case_count: int
    percentage: float


class AdaptiveRecoveryResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/adaptive."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    single_cycle_recovery_count: int = 0
    single_cycle_recovery_rate: float = 0.0
    multi_cycle_recovery_count: int = 0
    multi_cycle_recovery_rate: float = 0.0
    re_evaluated_cases_count: int = 0
    re_evaluation_recovery_rate: float = 0.0
    mean_cycles_to_recovery: float = 0.0
    median_cycles_to_recovery: float = 0.0
    same_action_avoidance_rate: float = 1.0
    bounded_termination_rate: float = 1.0
    hard_ceiling_violations: int | None = None
    cycle_distribution: list[AdaptiveCycleDistributionDTO] = Field(default_factory=list)


class SafetyInvariantCheckDTO(BaseModel):
    """Single safety invariant verification item and status."""

    model_config = ConfigDict(frozen=True)

    invariant_name: str
    description: str
    violation_count: int
    status: str


class SafetyResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/safety."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    overall_safety_status: str
    unsafe_dispatch_count: int = 0
    policy_bypass_count: int = 0
    stale_policy_reuse_count: int = 0
    duplicate_execution_count: int = 0
    duplicate_outcome_count: int = 0
    state_guard_rejections: int = 0
    terminal_case_reopen_attempts: int = 0
    provider_unknown_count: int = 0
    provider_unknown_rate: float = 0.0
    invariants: list[SafetyInvariantCheckDTO] = Field(default_factory=list)


class CohortBreakdownDTO(BaseModel):
    """Disaggregated segment breakdown metrics."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    cohort_key: str
    cohort_name: str
    case_count: int
    recovered_count: int
    recovery_rate: float
    gross_recovered_amount: int
    net_recovered_revenue: int
    small_cohort_flag: bool = False


class CohortsResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/cohorts."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    cohorts: list[CohortBreakdownDTO] = Field(default_factory=list)


class CaseSummaryDTO(BaseModel):
    """Compact case summary for table listing in the Case Explorer."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    payment_id: str
    amount: int
    currency: str = "INR"
    status: str
    failure_category: str | None = None
    selected_action: str | None = None
    cycle_count: int = 1
    is_recovered: bool = False
    recovered_amount: int = 0
    opened_at: str
    closed_at: str | None = None


class CaseListResponse(BaseModel):
    """Paginated response wrapper for GET /api/dashboard/cases."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    items: list[CaseSummaryDTO] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class CaseDetailResponse(BaseModel):
    """Full causal audit reconstruction response for case detail endpoint."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    case: dict[str, Any]


class AuditEventDTO(BaseModel):
    """Single chronological audit log event entry."""

    model_config = ConfigDict(frozen=True)

    audit_event_id: str
    case_id: str
    event_type: str
    actor: str
    timestamp: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class CaseTimelineResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/cases/{case_id}/timeline."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    case_id: str
    events: list[AuditEventDTO] = Field(default_factory=list)


class ReviewerQuestionsResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/cases/{case_id}/reviewer-questions."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    case_id: str
    completeness: str
    integrity_valid: bool
    integrity_issues: list[str] = Field(default_factory=list)
    questions: dict[str, Any] = Field(default_factory=dict)


class ReproducibilityResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/reproducibility/{benchmark_run_id}."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    benchmark_run_id: str
    dataset_id: str
    dataset_version: str
    snapshot_hash: str
    evaluation_config_version: str
    metric_schema_version: str
    code_revision: str
    bootstrap_seed: int
    bootstrap_iterations: int
    report_hash: str
    created_at: str
    limitations: list[str] = Field(default_factory=list)
    cost_model: dict[str, Any] = Field(default_factory=dict)


class BenchmarkRunSummaryDTO(BaseModel):
    """Summary record for a single immutable benchmark run."""

    model_config = ConfigDict(frozen=True)

    benchmark_run_id: str
    report_id: str
    dataset_id: str
    dataset_version: str
    report_hash: str
    recovery_rate: float
    gross_recovered_amount: int
    net_recovered_revenue: int
    is_synthetic_demo: bool = False
    created_at: str


class BenchmarkRunListResponse(BaseModel):
    """Response wrapper for GET /api/dashboard/runs."""

    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    metadata: CommonResponseMetadata
    runs: list[BenchmarkRunSummaryDTO] = Field(default_factory=list)
