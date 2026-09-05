export interface CommonResponseMetadata {
  timestamp: string;
  service: string;
  phase: string;
  source_revision?: string;
  data_version: string;
  query_scope?: string;
  benchmark_run_id?: string | null;
  report_hash?: string | null;
}

export interface DashboardOverviewKPIs {
  eligible_cases: number;
  recovered_cases: number;
  recovery_rate: number;
  gross_recovered_revenue: number;
  net_recovered_revenue: number;
  total_intervention_cost: number;
  cost_per_recovered_rupee?: number | null;
  median_time_to_recovery_seconds?: number | null;
  mean_cycles_to_recovery?: number | null;
  safety_status: string;
  latest_benchmark_run_id: string;
  dataset_id: string;
  dataset_version: string;
  is_synthetic_demo: boolean;
  last_updated_at: string;
}

export interface OverviewResponse {
  status: "ok" | "empty" | "error";
  metadata: CommonResponseMetadata;
  data: DashboardOverviewKPIs | null;
  message?: string | null;
}

export interface FunnelStageData {
  stage_name: string;
  count?: number | null;
  percentage?: number | null;
  dropoff_count?: number | null;
  dropoff_percentage?: number | null;
}

export interface FunnelResponse {
  status: "ok" | "empty" | "error";
  metadata: CommonResponseMetadata;
  data: FunnelStageData[];
}

export interface BaselineComparisonDTO {
  baseline_type: string;
  baseline_name: string;
  baseline_version: string;
  apro_recovery_rate: number;
  baseline_recovery_rate: number;
  absolute_recovery_delta: number;
  relative_recovery_delta?: number | null;
  apro_gross_recovered: number;
  baseline_gross_recovered: number;
  incremental_recovered_amount: number;
  apro_net_recovered: number;
  baseline_net_recovered: number;
  incremental_net_revenue: number;
  apro_intervention_cost: number;
  baseline_intervention_cost: number;
  delta_recovery_ci_95?: number[] | null;
  delta_net_revenue_ci_95?: number[] | null;
  p_value?: number | null;
  adjusted_p_value?: number | null;
  comparison_label: string;
  is_statistically_significant: boolean;
}

export interface BenchmarksResponse {
  status: "ok" | "empty" | "error";
  metadata: CommonResponseMetadata;
  data: BaselineComparisonDTO[];
  multiplicity_policy?: string | null;
}

export interface CalibrationBinDTO {
  bin_index: number;
  bin_lower: number;
  bin_upper: number;
  sample_count: number;
  mean_predicted_prob: number;
  empirical_recovery_rate: number;
}

export interface ClassificationMetricsDTO {
  accuracy?: number | null;
  precision?: number | null;
  recall?: number | null;
  f1_score?: number | null;
  roc_auc?: number | null;
  pr_auc?: number | null;
  log_loss?: number | null;
}

export interface DecisionQualityDTO {
  action_regret_avg?: number | null;
  oracle_gap_avg?: number | null;
  best_action_selection_rate?: number | null;
}

export interface PredictionQualityResponse {
  status: "ok" | "empty" | "error";
  metadata: CommonResponseMetadata;
  brier_score?: number | null;
  calibration_bins: CalibrationBinDTO[];
  classification_metrics?: ClassificationMetricsDTO | null;
  decision_quality?: DecisionQualityDTO | null;
}

export interface AdaptiveCycleDistributionDTO {
  cycle_number: number;
  case_count: number;
  percentage: number;
}

export interface AdaptiveRecoveryResponse {
  status: "ok" | "empty" | "error";
  metadata: CommonResponseMetadata;
  single_cycle_recovery_count: number;
  single_cycle_recovery_rate: number;
  multi_cycle_recovery_count: number;
  multi_cycle_recovery_rate: number;
  re_evaluated_cases_count: number;
  re_evaluation_recovery_rate: number;
  mean_cycles_to_recovery: number;
  median_cycles_to_recovery: number;
  same_action_avoidance_rate: number;
  bounded_termination_rate: number;
  hard_ceiling_violations?: number | null;
  cycle_distribution: AdaptiveCycleDistributionDTO[];
}

export interface SafetyInvariantCheckDTO {
  invariant_name: string;
  description: string;
  violation_count: number;
  status: string;
}

export interface SafetyResponse {
  status: "ok" | "empty" | "error";
  metadata: CommonResponseMetadata;
  overall_safety_status: string;
  unsafe_dispatch_count: number;
  policy_bypass_count: number;
  stale_policy_reuse_count: number;
  duplicate_execution_count: number;
  duplicate_outcome_count: number;
  state_guard_rejections: number;
  terminal_case_reopen_attempts: number;
  provider_unknown_count: number;
  provider_unknown_rate: number;
  invariants: SafetyInvariantCheckDTO[];
}

export interface CohortBreakdownDTO {
  dimension: string;
  cohort_key: string;
  cohort_name: string;
  case_count: number;
  recovered_count: number;
  recovery_rate: number;
  gross_recovered_amount: number;
  net_recovered_revenue: number;
  small_cohort_flag: boolean;
}

export interface CohortsResponse {
  status: "ok" | "empty" | "error";
  metadata: CommonResponseMetadata;
  cohorts: CohortBreakdownDTO[];
}

export interface CaseSummaryDTO {
  case_id: string;
  payment_id: string;
  amount: number;
  currency: string;
  status: string;
  failure_category?: string | null;
  selected_action?: string | null;
  cycle_count: number;
  is_recovered: boolean;
  recovered_amount: number;
  opened_at: string;
  closed_at?: string | null;
}

export interface CaseListResponse {
  status: "ok" | "empty" | "error";
  metadata: CommonResponseMetadata;
  items: CaseSummaryDTO[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CaseDetailResponse {
  status: "ok" | "error";
  metadata: CommonResponseMetadata;
  case: Record<string, any>;
}

export interface AuditEventDTO {
  audit_event_id: string;
  case_id: string;
  event_type: string;
  actor: string;
  timestamp: string;
  payload: Record<string, any>;
  correlation_id: string;
}

export interface CaseTimelineResponse {
  status: "ok" | "error";
  metadata: CommonResponseMetadata;
  case_id: string;
  events: AuditEventDTO[];
}

export interface ReviewerQuestionsResponse {
  status: "ok" | "error";
  metadata: CommonResponseMetadata;
  case_id: string;
  completeness: string;
  integrity_valid: boolean;
  integrity_issues: string[];
  questions: Record<string, any>;
}

export interface ReproducibilityResponse {
  status: "ok" | "error";
  metadata: CommonResponseMetadata;
  benchmark_run_id: string;
  dataset_id: string;
  dataset_version: string;
  snapshot_hash: string;
  report_hash: string;
  evaluation_config_version: string;
  metric_schema_version: string;
  code_revision: string;
  bootstrap_seed: number;
  bootstrap_iterations: number;
  is_synthetic_demo: boolean;
  created_at: string;
  reproducibility_manifest: Record<string, any>;
}

export interface BenchmarkRunSummaryDTO {
  report_id: string;
  benchmark_run_id: string;
  dataset_id: string;
  dataset_version: string;
  report_hash: string;
  created_at: string;
  recovery_rate: number;
  gross_recovered_amount: number;
  net_recovered_revenue: number;
  total_intervention_cost: number;
  is_synthetic_demo: boolean;
}

export interface BenchmarkRunListResponse {
  status: "ok" | "error";
  metadata: CommonResponseMetadata;
  runs: BenchmarkRunSummaryDTO[];
}
