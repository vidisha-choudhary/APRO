"""Data models and report schemas for APRO Phase 15 evaluation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.audit.models import CaseAuditTrace
from apro.domain.models import (
    AuditEvent,
    Decision,
    Diagnosis,
    Execution,
    Outcome,
    Payment,
    PaymentEvent,
    PolicyDecision,
    RecoveryAction,
    RecoveryCase,
)
from apro.evaluation.config import EvaluationConfig
from apro.evaluation.enums import (
    BaselineType,
    EvaluationCaseStatus,
    MetricComparisonLabel,
)


class OfflineEvaluationTruth(BaseModel):
    """Offline-only benchmark ground truth and counterfactual labels.

    MUST NOT be used as runtime model or decision inputs.
    """

    model_config = ConfigDict(frozen=True)

    ground_truth_recovered: bool
    ground_truth_recovered_amount: int = Field(ge=0)
    ground_truth_best_action: str | None = None
    ground_truth_failure_class: str | None = None
    ground_truth_time_to_recovery_seconds: float | None = None
    counterfactual_outcomes: dict[str, dict[str, Any]] = Field(default_factory=dict)


class BenchmarkCaseRecord(BaseModel):
    """Evaluation view of a single recovery case."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    payment_id: str
    payment_amount: int = Field(ge=0, description="Amount in paise")
    currency: str = "INR"
    payment_method: str = "CARD"
    case_status: str = "CLOSED_RECOVERED"
    failure_code: str | None = None
    failure_category: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    duration_seconds: float | None = None

    # Lifecycle entity references
    case: RecoveryCase | None = None
    payment: Payment | None = None
    payment_events: list[PaymentEvent] = Field(default_factory=list)
    diagnosis: Diagnosis | None = None
    decisions: list[Decision] = Field(default_factory=list)
    policy_decisions: list[PolicyDecision] = Field(default_factory=list)
    recovery_actions: list[RecoveryAction] = Field(default_factory=list)
    executions: list[Execution] = Field(default_factory=list)
    outcomes: list[Outcome] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)
    audit_trace: CaseAuditTrace | None = None

    # Offline evaluation truth (strictly separated from runtime decisions)
    offline_truth: OfflineEvaluationTruth | None = None

    # Precomputed / evaluated properties
    is_recovered: bool = False
    recovered_amount: int = 0
    intervention_count: int = 0
    cycle_count: int = 1
    re_evaluation_count: int = 0
    final_action_type: str | None = None
    terminal_disposition: str = "UNKNOWN"


class CaseEligibilityResult(BaseModel):
    """Case eligibility classification result."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    status: EvaluationCaseStatus
    exclusion_reason: str | None = None
    is_eligible: bool


class PrimaryKPISet(BaseModel):
    """Primary economic, financial, and operational recovery KPIs."""

    model_config = ConfigDict(frozen=True)

    case_count: int = Field(ge=0)
    eligible_cases: int = Field(ge=0)
    recovered_cases: int = Field(ge=0)
    recovery_rate: float = Field(ge=0.0, le=1.0)
    eligible_at_risk_amount: int = Field(ge=0, description="Revenue at risk in paise")
    gross_recovered_amount: int = Field(
        ge=0, description="Total gross recovered in paise"
    )
    recovered_revenue_rate: float = Field(ge=0.0, le=1.0)
    total_intervention_cost: int = Field(ge=0, description="Total action cost in paise")
    net_recovered_revenue: int = Field(
        description="Gross recovered minus intervention cost"
    )
    cost_per_recovered_rupee: float | None = Field(
        default=None,
        description="Intervention cost / gross recovered. None if gross recovered is 0",
    )
    net_recovery_efficiency: float = Field(description="Net recovered / at risk amount")

    # Time to recovery
    mean_time_to_recovery_seconds: float | None = None
    median_time_to_recovery_seconds: float | None = None
    p25_time_to_recovery_seconds: float | None = None
    p75_time_to_recovery_seconds: float | None = None
    p90_time_to_recovery_seconds: float | None = None

    # Attempts & Cycles
    attempts_per_case_mean: float = 0.0
    attempts_per_case_median: float = 0.0
    attempts_per_case_p90: float = 0.0
    cycle_count_total: int = 0
    re_evaluation_count_total: int = 0
    same_action_repetition_count: int = 0

    # Disposition distribution
    terminal_disposition_mix: dict[str, int] = Field(default_factory=dict)


class SafetyKPISet(BaseModel):
    """Safety and operational invariant verification KPIs."""

    model_config = ConfigDict(frozen=True)

    policy_block_count: int = 0
    policy_block_rate: float = 0.0
    state_guard_rejection_count: int = 0
    state_guard_rejection_rate: float = 0.0
    stale_policy_rejection_count: int = 0
    stale_policy_rejection_rate: float = 0.0
    provider_transport_unknown_count: int = 0
    provider_transport_unknown_rate: float = 0.0
    duplicate_execution_attempt_count: int = 0
    duplicate_execution_attempt_rate: float = 0.0
    duplicate_outcome_count: int = 0
    duplicate_outcome_rate: float = 0.0
    terminal_case_reopen_attempt_count: int = 0
    terminal_case_reopen_attempt_rate: float = 0.0
    unsafe_dispatch_count: int = 0
    unsafe_dispatch_rate: float = 0.0
    policy_bypass_count: int = 0
    credential_leakage_count: int = 0


class StatisticalSummary(BaseModel):
    """Statistical estimation and uncertainty summary for a single metric."""

    model_config = ConfigDict(frozen=True)

    metric_name: str
    point_estimate: float
    mean: float
    median: float
    std_err: float | None = None
    ci_lower: float
    ci_upper: float
    confidence_level: float = 0.95
    sample_size: int
    method: str = "case_bootstrap"


class BaselineComparisonResult(BaseModel):
    """Comparative evaluation result between APRO and a baseline strategy."""

    model_config = ConfigDict(frozen=True)

    baseline_type: BaselineType
    baseline_name: str
    baseline_version: str = "1.0.0"
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
    delta_recovery_ci_95: tuple[float, float] = (0.0, 0.0)
    delta_net_revenue_ci_95: tuple[float, float] = (0.0, 0.0)
    p_value: float | None = None
    adjusted_p_value: float | None = None
    effect_size: float | None = None
    comparison_label: MetricComparisonLabel = (
        MetricComparisonLabel.BENCHMARK_ASSOCIATION
    )
    is_statistically_significant: bool = False


class CalibrationBin(BaseModel):
    """A single prediction probability calibration bin."""

    model_config = ConfigDict(frozen=True)

    bin_index: int
    bin_lower: float
    bin_upper: float
    predicted_mean_probability: float
    empirical_success_rate: float
    sample_count: int


class PredictionQualitySummary(BaseModel):
    """Phase 8 outcome prediction calibration and accuracy metrics."""

    model_config = ConfigDict(frozen=True)

    brier_score: float
    sample_size: int
    positive_class: str = "RECOVERED"
    action_scope: str = "ALL"
    roc_auc: float | None = None
    pr_auc: float | None = None
    log_loss: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    calibration_curve: list[CalibrationBin] = Field(default_factory=list)


class DecisionQualitySummary(BaseModel):
    """Phase 9 decision engine quality and counterfactual regret metrics."""

    model_config = ConfigDict(frozen=True)

    selected_action_distribution: dict[str, int] = Field(default_factory=dict)
    candidate_action_count_avg: float = 0.0
    selected_action_erv_avg: float = 0.0
    selected_action_cost_avg: float = 0.0
    action_regret_avg: float | None = None
    oracle_gap_avg: float | None = None
    best_action_selection_rate: float | None = None


class AdaptiveLoopSummary(BaseModel):
    """Phase 13 adaptive recovery loop evaluation from canonical history."""

    model_config = ConfigDict(frozen=True)

    total_cases: int
    single_cycle_recovery_count: int = 0
    single_cycle_recovery_rate: float = 0.0
    multi_cycle_recovery_count: int = 0
    multi_cycle_recovery_rate: float = 0.0
    re_evaluation_count: int = 0
    recovery_after_re_evaluation_rate: float = 0.0
    mean_cycles_to_recovery: float | None = None
    median_cycles_to_recovery: float | None = None
    incremental_recovery_after_first_failure: float = 0.0
    same_action_avoidance_rate: float = 0.0
    bounded_termination_rate: float = 1.0


class CohortBreakdown(BaseModel):
    """Metric evaluation sliced by cohort dimension."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    cohort_key: str
    case_count: int
    is_small_cohort: bool = False
    recovery_rate: float = 0.0
    gross_recovered: int = 0
    net_recovered: int = 0
    mean_time_to_recovery: float | None = None


class BenchmarkReport(BaseModel):
    """Authoritative structured benchmark evaluation report."""

    model_config = ConfigDict(frozen=True)

    report_id: str
    benchmark_run_id: str
    dataset_id: str
    dataset_version: str
    snapshot_hash: str
    evaluation_config_version: str
    metric_schema_version: str
    code_revision: str
    created_at: str
    evaluation_config: EvaluationConfig
    case_counts: dict[str, int]
    primary_kpis: PrimaryKPISet
    safety_metrics: SafetyKPISet
    baseline_comparisons: dict[str, BaselineComparisonResult] = Field(
        default_factory=dict
    )
    statistical_results: dict[str, StatisticalSummary] = Field(default_factory=dict)
    prediction_quality: PredictionQualitySummary | None = None
    decision_quality: DecisionQualitySummary | None = None
    adaptive_loop_metrics: AdaptiveLoopSummary | None = None
    cohort_breakdowns: dict[str, list[CohortBreakdown]] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    reproducibility_metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def report_hash(self) -> str:
        """Deterministic SHA-256 hash of the report content."""
        from apro.evaluation.report import compute_report_hash

        return compute_report_hash(self)
