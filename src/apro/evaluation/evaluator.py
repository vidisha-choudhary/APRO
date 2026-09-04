import uuid
from datetime import UTC, datetime

from apro.evaluation.baselines import evaluate_baselines_comparison
from apro.evaluation.calibration import evaluate_prediction_quality
from apro.evaluation.config import EvaluationConfig
from apro.evaluation.dataset import (
    BenchmarkDatasetSnapshot,
    EligibilityClassifier,
    TruthPlaneSeparation,
)
from apro.evaluation.enums import (
    MultipleComparisonPolicy,
)
from apro.evaluation.exceptions import (
    InsufficientSampleError,
)
from apro.evaluation.metrics import (
    compute_primary_kpis,
    compute_safety_kpis,
)
from apro.evaluation.models import (
    AdaptiveLoopSummary,
    BenchmarkCaseRecord,
    BenchmarkReport,
    DecisionQualitySummary,
    StatisticalSummary,
)
from apro.evaluation.persistence import EvaluationArtifactStore
from apro.evaluation.segmentation import compute_all_cohort_breakdowns
from apro.evaluation.statistics import (
    adjust_p_values_holm,
    bootstrap_case_metric,
    compute_proportion_ci,
)


class APROEvaluator:
    """Evaluates APRO performance under benchmark conditions in read-only mode."""

    def __init__(
        self,
        config: EvaluationConfig | None = None,
        artifact_store: EvaluationArtifactStore | None = None,
    ) -> None:
        self.config = config or EvaluationConfig()
        self.artifact_store = artifact_store or EvaluationArtifactStore()

    def evaluate_dataset(
        self,
        snapshot: BenchmarkDatasetSnapshot,
        benchmark_run_id: str | None = None,
        code_revision: str = "34fb73a",
        created_at: str | None = None,
    ) -> BenchmarkReport:
        """Run complete benchmark evaluation on an immutable dataset snapshot."""
        # 1. Anti-Cheating & Truth-Plane Separation Validation
        TruthPlaneSeparation.verify_isolation(list(snapshot.records))

        # 2. Case Accounting & Eligibility Filtering
        eligible_records, _eligibility_results, case_counts = (
            EligibilityClassifier.filter_and_account_cases(
                list(snapshot.records), self.config
            )
        )

        n_eligible = len(eligible_records)
        if n_eligible == 0:
            raise InsufficientSampleError(
                "No eligible cases found in benchmark snapshot for evaluation."
            )

        # 3. Primary KPIs Computation
        primary_kpis = compute_primary_kpis(eligible_records, self.config)

        # 4. Safety KPIs Computation
        safety_kpis = compute_safety_kpis(eligible_records, self.config)

        # 5. Baseline Comparisons (over identical eligible cohort)
        baseline_comparisons = evaluate_baselines_comparison(
            eligible_records, self.config, primary_kpis
        )

        # Apply multiple comparison correction to baseline p-values if enabled
        if self.config.multiple_comparison_policy == MultipleComparisonPolicy.HOLM:
            base_keys = list(baseline_comparisons.keys())
            raw_p_values = [baseline_comparisons[k].p_value or 1.0 for k in base_keys]
            adj_p_values = adjust_p_values_holm(raw_p_values)
            alpha = round(1.0 - self.config.confidence_level, 4)
            for idx, k in enumerate(base_keys):
                orig_res = baseline_comparisons[k]
                adj_p = adj_p_values[idx]
                is_sig = adj_p < alpha
                baseline_comparisons[k] = orig_res.model_copy(
                    update={
                        "adjusted_p_value": adj_p,
                        "is_statistically_significant": is_sig,
                    }
                )

        # 6. Statistical Estimation & Uncertainty
        rec_ci_lower, rec_ci_upper = compute_proportion_ci(
            primary_kpis.recovered_cases,
            primary_kpis.eligible_cases,
            confidence_level=self.config.confidence_level,
        )

        def _recovery_rate_fn(sample: list[object]) -> float:
            if not sample:
                return 0.0
            recs = sum(
                1
                for r in sample
                if isinstance(r, BenchmarkCaseRecord)
                and (r.is_recovered and r.recovered_amount > 0)
            )
            return recs / len(sample)

        _pt, boot_ci_l, boot_ci_u = bootstrap_case_metric(
            list(eligible_records),
            _recovery_rate_fn,
            confidence_level=self.config.confidence_level,
            iterations=self.config.bootstrap_iterations,
            seed=self.config.bootstrap_seed,
        )

        statistical_results: dict[str, StatisticalSummary] = {
            "recovery_rate": StatisticalSummary(
                metric_name="recovery_rate",
                point_estimate=primary_kpis.recovery_rate,
                mean=primary_kpis.recovery_rate,
                median=primary_kpis.recovery_rate,
                ci_lower=boot_ci_l,
                ci_upper=boot_ci_u,
                confidence_level=self.config.confidence_level,
                sample_size=n_eligible,
                method="case_level_bootstrap",
            ),
            "recovery_rate_wilson": StatisticalSummary(
                metric_name="recovery_rate_wilson",
                point_estimate=primary_kpis.recovery_rate,
                mean=primary_kpis.recovery_rate,
                median=primary_kpis.recovery_rate,
                ci_lower=rec_ci_lower,
                ci_upper=rec_ci_upper,
                confidence_level=self.config.confidence_level,
                sample_size=n_eligible,
                method="wilson_score_interval",
            ),
        }

        # 7. Phase 8 Prediction Quality & Calibration
        prediction_quality = evaluate_prediction_quality(eligible_records)

        # 8. Phase 9 Decision Quality Evaluation
        decision_quality = self._evaluate_decision_quality(eligible_records)

        # 9. Phase 13 Adaptive Loop Evaluation
        adaptive_loop_metrics = self._evaluate_adaptive_loop(eligible_records)

        # 10. Cohort Segmentations
        cohort_breakdowns = compute_all_cohort_breakdowns(eligible_records, self.config)

        # 11. Compile Structured Report
        run_id = benchmark_run_id or f"run_{uuid.uuid4().hex[:12]}"
        rep_id = f"rep_{run_id}"
        now_str = created_at or datetime.now(UTC).isoformat()

        repro_meta = {
            "benchmark_run_id": run_id,
            "dataset_snapshot_hash": snapshot.snapshot_hash,
            "evaluation_config_hash": self.config.compute_config_hash(),
            "bootstrap_seed": self.config.bootstrap_seed,
            "bootstrap_iterations": self.config.bootstrap_iterations,
            "software_revision": code_revision,
            "metric_schema_version": self.config.metric_schema_version,
            "evaluation_config_version": self.config.evaluation_config_version,
        }

        report = BenchmarkReport(
            report_id=rep_id,
            benchmark_run_id=run_id,
            dataset_id=snapshot.dataset_id,
            dataset_version=snapshot.dataset_version,
            snapshot_hash=snapshot.snapshot_hash,
            evaluation_config_version=self.config.evaluation_config_version,
            metric_schema_version=self.config.metric_schema_version,
            code_revision=code_revision,
            created_at=now_str,
            evaluation_config=self.config,
            case_counts=case_counts,
            primary_kpis=primary_kpis,
            safety_metrics=safety_kpis,
            baseline_comparisons=baseline_comparisons,
            statistical_results=statistical_results,
            prediction_quality=prediction_quality,
            decision_quality=decision_quality,
            adaptive_loop_metrics=adaptive_loop_metrics,
            cohort_breakdowns=cohort_breakdowns,
            limitations=[
                "Observational comparisons do not establish causal impact.",
                "Simulated actions are evaluated under offline assumptions.",
                "Counterfactual labels reflect evaluation ground truth.",
            ],
            reproducibility_metadata=repro_meta,
        )

        # Persist report in evaluation store
        self.artifact_store.save_report(report)

        return report

    def _evaluate_decision_quality(
        self, records: list[BenchmarkCaseRecord]
    ) -> DecisionQualitySummary:
        """Measure Phase 9 decision quality without altering runtime decisions."""
        action_dist: dict[str, int] = {}
        candidate_counts: list[int] = []
        erv_list: list[int] = []
        cost_list: list[int] = []
        regrets: list[int] = []
        oracle_gaps: list[int] = []
        best_action_matches = 0
        total_eval_truth_cases = 0

        for r in records:
            act = r.final_action_type or (
                r.executions[-1].execution_type if r.executions else "STOP"
            )
            action_dist[act] = action_dist.get(act, 0) + 1

            if r.decisions:
                d = r.decisions[0]
                erv_list.append(d.expected_recovery_value)
                cost_list.append(
                    self.config.cost_model.get_action_cost(d.recommended_action)
                )
                candidate_counts.append(len(r.recovery_actions) or 1)

            if r.offline_truth:
                total_eval_truth_cases += 1
                best_val = r.offline_truth.ground_truth_recovered_amount
                best_act = r.offline_truth.ground_truth_best_action
                rec_val = r.recovered_amount if r.is_recovered else 0

                regret = max(0, best_val - rec_val)
                regrets.append(regret)
                oracle_gaps.append(regret)

                if best_act and act.upper() == best_act.upper():
                    best_action_matches += 1

        avg_cand = (
            sum(candidate_counts) / len(candidate_counts) if candidate_counts else 1.0
        )
        avg_erv = sum(erv_list) / len(erv_list) if erv_list else 0.0
        avg_cost = sum(cost_list) / len(cost_list) if cost_list else 0.0
        avg_regret = (sum(regrets) / len(regrets)) if regrets else None
        avg_gap = (sum(oracle_gaps) / len(oracle_gaps)) if oracle_gaps else None
        best_rate = (
            (best_action_matches / total_eval_truth_cases)
            if total_eval_truth_cases > 0
            else None
        )

        return DecisionQualitySummary(
            selected_action_distribution=action_dist,
            candidate_action_count_avg=round(avg_cand, 2),
            selected_action_erv_avg=round(avg_erv, 2),
            selected_action_cost_avg=round(avg_cost, 2),
            action_regret_avg=round(avg_regret, 2) if avg_regret is not None else None,
            oracle_gap_avg=round(avg_gap, 2) if avg_gap is not None else None,
            best_action_selection_rate=(
                round(best_rate, 4) if best_rate is not None else None
            ),
        )

    def _evaluate_adaptive_loop(
        self, records: list[BenchmarkCaseRecord]
    ) -> AdaptiveLoopSummary:
        """Measure Phase 13 adaptive recovery loop from canonical persisted history."""
        n = len(records)
        if n == 0:
            return AdaptiveLoopSummary(total_cases=0)

        single_rec = 0
        multi_rec = 0
        reeval_cases = 0
        reeval_rec = 0
        cycles_to_rec: list[int] = []
        first_failure_cases = 0
        recovered_after_first_fail = 0
        avoided_same_action_count = 0
        bounded_termination_count = 0

        for r in records:
            c_count = max(1, r.cycle_count)
            is_rec = r.is_recovered and r.recovered_amount > 0

            if is_rec:
                cycles_to_rec.append(c_count)
                if c_count == 1:
                    single_rec += 1
                else:
                    multi_rec += 1

            if r.re_evaluation_count > 0 or c_count > 1:
                reeval_cases += 1
                if is_rec:
                    reeval_rec += 1

            if len(r.executions) > 1:
                first_failure_cases += 1
                if is_rec:
                    recovered_after_first_fail += 1

                acts = [e.execution_type for e in r.executions]
                if len(acts) >= 2 and acts[0] != acts[1]:
                    avoided_same_action_count += 1

            if c_count <= 5 and r.case_status in (
                "CLOSED_RECOVERED",
                "CLOSED_STOPPED",
                "CLOSED_ESCALATED",
                "STOPPED",
                "ESCALATED",
            ):
                bounded_termination_count += 1

        mean_cyc = (sum(cycles_to_rec) / len(cycles_to_rec)) if cycles_to_rec else None
        cycles_to_rec.sort()
        median_cyc = (
            float(cycles_to_rec[len(cycles_to_rec) // 2]) if cycles_to_rec else None
        )

        single_rate = round(single_rec / n, 4)
        multi_rate = round(multi_rec / n, 4)
        reeval_rate = round(reeval_rec / reeval_cases, 4) if reeval_cases > 0 else 0.0
        inc_after_fail = (
            round(recovered_after_first_fail / first_failure_cases, 4)
            if first_failure_cases > 0
            else 0.0
        )
        avoid_rate = (
            round(avoided_same_action_count / first_failure_cases, 4)
            if first_failure_cases > 0
            else 1.0
        )
        bounded_rate = round(bounded_termination_count / n, 4)

        return AdaptiveLoopSummary(
            total_cases=n,
            single_cycle_recovery_count=single_rec,
            single_cycle_recovery_rate=single_rate,
            multi_cycle_recovery_count=multi_rec,
            multi_cycle_recovery_rate=multi_rate,
            re_evaluation_count=reeval_cases,
            recovery_after_re_evaluation_rate=reeval_rate,
            mean_cycles_to_recovery=(
                round(mean_cyc, 2) if mean_cyc is not None else None
            ),
            median_cycles_to_recovery=median_cyc,
            incremental_recovery_after_first_failure=inc_after_fail,
            same_action_avoidance_rate=avoid_rate,
            bounded_termination_rate=bounded_rate,
        )
