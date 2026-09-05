"""Dashboard service providing read-only queries from PostgreSQL truth."""

from typing import Any

from apro.audit.exceptions import AuditNotFoundError
from apro.audit.reconstruction import CaseReconstructionService
from apro.dashboard.schemas import (
    AdaptiveRecoveryResponse,
    AuditEventDTO,
    BaselineComparisonDTO,
    BenchmarkRunListResponse,
    BenchmarkRunSummaryDTO,
    BenchmarksResponse,
    CalibrationBinDTO,
    CaseDetailResponse,
    CaseListResponse,
    CaseSummaryDTO,
    CaseTimelineResponse,
    ClassificationMetricsDTO,
    CohortBreakdownDTO,
    CohortsResponse,
    CommonResponseMetadata,
    DashboardOverviewKPIs,
    DecisionQualityDTO,
    FunnelResponse,
    FunnelStageData,
    OverviewResponse,
    PredictionQualityResponse,
    ReproducibilityResponse,
    ReviewerQuestionsResponse,
    SafetyInvariantCheckDTO,
    SafetyResponse,
)
from apro.evaluation.exceptions import EvaluationPersistenceError
from apro.evaluation.models import BenchmarkReport
from apro.evaluation.persistence import (
    EvaluationArtifactStore,
    PostgreSQLEvaluationArtifactStore,
)
from apro.persistence.unit_of_work import UnitOfWork


class DashboardService:
    """Read-only aggregation service for Phase 16 Live Dashboard API."""

    def __init__(
        self,
        eval_store: PostgreSQLEvaluationArtifactStore
        | EvaluationArtifactStore
        | None = None,
        uow_factory: Any | None = None,
        allow_in_memory_for_testing: bool = False,
    ) -> None:
        self._allow_in_memory = allow_in_memory_for_testing
        self._uow_factory = uow_factory

        if eval_store is not None:
            if (
                isinstance(eval_store, EvaluationArtifactStore)
                and not allow_in_memory_for_testing
            ):
                raise EvaluationPersistenceError(
                    "Production dashboard service strictly requires "
                    "PostgreSQLEvaluationArtifactStore. "
                    "In-memory store fallback is prohibited in production mode."
                )
            self._eval_store = eval_store
        else:
            if not allow_in_memory_for_testing:
                try:
                    self._eval_store = PostgreSQLEvaluationArtifactStore()
                except Exception as e:
                    raise EvaluationPersistenceError(
                        f"Failed to initialize PostgreSQLEvaluationArtifactStore: {e}"
                    ) from e
            else:
                self._eval_store = EvaluationArtifactStore()

    async def _get_uow(self) -> UnitOfWork:
        if self._uow_factory is not None:
            return self._uow_factory()  # type: ignore[no-any-return]
        if (
            hasattr(self._eval_store, "_session_factory")
            and self._eval_store._session_factory is not None
        ):
            return UnitOfWork(self._eval_store._session_factory)
        import os

        from apro.config import settings
        from apro.persistence.database import get_async_engine, get_session_factory

        db_url = settings.DATABASE_URL or os.environ.get("POSTGRES_TEST_URL")
        engine = get_async_engine(db_url)
        session_factory = get_session_factory(engine)
        return UnitOfWork(session_factory)

    async def resolve_benchmark_report(
        self, benchmark_run_id: str | None = None
    ) -> BenchmarkReport | None:
        """Resolve a benchmark report by ID or fetch the latest immutable run."""
        if benchmark_run_id:
            if hasattr(self._eval_store, "get_report_by_run_id"):
                if isinstance(self._eval_store, PostgreSQLEvaluationArtifactStore):
                    report = await self._eval_store.get_report_by_run_id(
                        benchmark_run_id
                    )
                else:
                    report = self._eval_store.get_report_by_run_id(benchmark_run_id)
            else:
                report = None

            if report is None:
                raise KeyError(
                    f"Benchmark run '{benchmark_run_id}' not found in storage."
                )
            return report

        # No specific run supplied: fetch latest immutable run
        if hasattr(self._eval_store, "get_latest_report"):
            if isinstance(self._eval_store, PostgreSQLEvaluationArtifactStore):
                return await self._eval_store.get_latest_report()
            return self._eval_store.get_latest_report()

        return None

    def _make_metadata(
        self, report: BenchmarkReport | None = None
    ) -> CommonResponseMetadata:
        if report is not None:
            return CommonResponseMetadata(
                benchmark_run_id=report.benchmark_run_id,
                report_hash=report.report_hash,
                data_version=report.metric_schema_version,
            )
        return CommonResponseMetadata()

    async def get_overview(
        self, benchmark_run_id: str | None = None
    ) -> OverviewResponse:
        """GET /api/dashboard/overview."""
        report = await self.resolve_benchmark_report(benchmark_run_id)
        if report is None:
            return OverviewResponse(
                status="empty",
                metadata=self._make_metadata(),
                data=None,
                message=(
                    "No benchmark run available. Run or load a benchmark "
                    "evaluation to populate."
                ),
            )

        kpis = report.primary_kpis
        safety = report.safety_metrics

        # Determine overall safety status
        safety_status = "PASS"
        if (
            safety.unsafe_dispatch_count > 0
            or safety.policy_bypass_count > 0
            or safety.stale_policy_rejection_count > 0
        ):
            safety_status = "FAIL"
        elif (
            safety.provider_transport_unknown_count > 0
            or safety.duplicate_outcome_count > 0
        ):
            safety_status = "WARNING"

        overview_data = DashboardOverviewKPIs(
            eligible_cases=kpis.eligible_cases,
            recovered_cases=kpis.recovered_cases,
            recovery_rate=kpis.recovery_rate,
            gross_recovered_revenue=kpis.gross_recovered_amount,
            net_recovered_revenue=kpis.net_recovered_revenue,
            total_intervention_cost=kpis.total_intervention_cost,
            cost_per_recovered_rupee=kpis.cost_per_recovered_rupee,
            median_time_to_recovery_seconds=kpis.median_time_to_recovery_seconds,
            mean_cycles_to_recovery=report.adaptive_loop_metrics.mean_cycles_to_recovery
            if report.adaptive_loop_metrics
            else None,
            safety_status=safety_status,
            latest_benchmark_run_id=report.benchmark_run_id,
            dataset_id=report.dataset_id,
            dataset_version=report.dataset_version,
            is_synthetic_demo="demo" in report.dataset_id.lower(),
            last_updated_at=report.created_at,
        )

        return OverviewResponse(
            status="ok",
            metadata=self._make_metadata(report),
            data=overview_data,
        )

    async def get_funnel(self, benchmark_run_id: str | None = None) -> FunnelResponse:
        """GET /api/dashboard/funnel."""
        report = await self.resolve_benchmark_report(benchmark_run_id)
        if report is None:
            return FunnelResponse(
                status="empty",
                metadata=self._make_metadata(),
                data=[],
            )

        kpis = report.primary_kpis
        total = max(1, kpis.eligible_cases)

        stages = [
            FunnelStageData(
                stage_name="Eligible",
                count=kpis.eligible_cases,
                percentage=100.0,
                dropoff_count=0,
                dropoff_percentage=0.0,
            ),
        ]

        # Attempted stage (only if authoritative in case_counts)
        if report.case_counts and "attempted" in report.case_counts:
            attempted_cnt = report.case_counts["attempted"]
            attempted_pct = round((attempted_cnt / total) * 100.0, 2)
            dropoff_cnt = max(0, kpis.eligible_cases - attempted_cnt)
            dropoff_pct = round((dropoff_cnt / total) * 100.0, 2)
            stages.append(
                FunnelStageData(
                    stage_name="Attempted",
                    count=attempted_cnt,
                    percentage=attempted_pct,
                    dropoff_count=dropoff_cnt,
                    dropoff_percentage=dropoff_pct,
                )
            )
        else:
            stages.append(
                FunnelStageData(
                    stage_name="Attempted",
                    count=None,
                    percentage=None,
                    dropoff_count=None,
                    dropoff_percentage=None,
                )
            )

        # Pending stage (only if authoritative in case_counts)
        if report.case_counts and "pending" in report.case_counts:
            pending_cnt = report.case_counts["pending"]
            pending_pct = round((pending_cnt / total) * 100.0, 2)
            stages.append(
                FunnelStageData(
                    stage_name="Pending",
                    count=pending_cnt,
                    percentage=pending_pct,
                    dropoff_count=0,
                    dropoff_percentage=0.0,
                )
            )
        else:
            stages.append(
                FunnelStageData(
                    stage_name="Pending",
                    count=None,
                    percentage=None,
                    dropoff_count=None,
                    dropoff_percentage=None,
                )
            )

        # Recovered stage (authoritative)
        rec_cnt = kpis.recovered_cases
        rec_pct = round((rec_cnt / total) * 100.0, 2)
        stages.append(
            FunnelStageData(
                stage_name="Recovered",
                count=rec_cnt,
                percentage=rec_pct,
                dropoff_count=None,
                dropoff_percentage=None,
            )
        )

        # Stopped stage (only if in terminal_disposition_mix or case_counts)
        if kpis.terminal_disposition_mix and "STOPPED" in kpis.terminal_disposition_mix:
            stopped_cnt = kpis.terminal_disposition_mix["STOPPED"]
            stopped_pct = round((stopped_cnt / total) * 100.0, 2)
            stages.append(
                FunnelStageData(
                    stage_name="Stopped",
                    count=stopped_cnt,
                    percentage=stopped_pct,
                    dropoff_count=0,
                    dropoff_percentage=0.0,
                )
            )
        elif report.case_counts and "stopped" in report.case_counts:
            stopped_cnt = report.case_counts["stopped"]
            stopped_pct = round((stopped_cnt / total) * 100.0, 2)
            stages.append(
                FunnelStageData(
                    stage_name="Stopped",
                    count=stopped_cnt,
                    percentage=stopped_pct,
                    dropoff_count=0,
                    dropoff_percentage=0.0,
                )
            )
        else:
            stages.append(
                FunnelStageData(
                    stage_name="Stopped",
                    count=None,
                    percentage=None,
                    dropoff_count=None,
                    dropoff_percentage=None,
                )
            )

        # Escalated stage (only if in terminal_disposition_mix or case_counts)
        if (
            kpis.terminal_disposition_mix
            and "ESCALATED" in kpis.terminal_disposition_mix
        ):
            esc_cnt = kpis.terminal_disposition_mix["ESCALATED"]
            esc_pct = round((esc_cnt / total) * 100.0, 2)
            stages.append(
                FunnelStageData(
                    stage_name="Escalated",
                    count=esc_cnt,
                    percentage=esc_pct,
                    dropoff_count=0,
                    dropoff_percentage=0.0,
                )
            )
        elif report.case_counts and "escalated" in report.case_counts:
            esc_cnt = report.case_counts["escalated"]
            esc_pct = round((esc_cnt / total) * 100.0, 2)
            stages.append(
                FunnelStageData(
                    stage_name="Escalated",
                    count=esc_cnt,
                    percentage=esc_pct,
                    dropoff_count=0,
                    dropoff_percentage=0.0,
                )
            )
        else:
            stages.append(
                FunnelStageData(
                    stage_name="Escalated",
                    count=None,
                    percentage=None,
                    dropoff_count=None,
                    dropoff_percentage=None,
                )
            )

        return FunnelResponse(
            status="ok",
            metadata=self._make_metadata(report),
            data=stages,
        )

    async def get_benchmarks(
        self, benchmark_run_id: str | None = None
    ) -> BenchmarksResponse:
        """GET /api/dashboard/benchmarks."""
        report = await self.resolve_benchmark_report(benchmark_run_id)
        if report is None:
            return BenchmarksResponse(
                status="empty",
                metadata=self._make_metadata(),
                data=[],
            )

        comparisons: list[BaselineComparisonDTO] = []
        for name, comp in report.baseline_comparisons.items():
            b_type = (
                comp.baseline_type.value
                if hasattr(comp.baseline_type, "value")
                else str(comp.baseline_type)
            )
            label = (
                comp.comparison_label.value
                if hasattr(comp.comparison_label, "value")
                else str(comp.comparison_label)
            )

            dto = BaselineComparisonDTO(
                baseline_type=b_type,
                baseline_name=name,
                baseline_version=comp.baseline_version,
                apro_recovery_rate=comp.apro_recovery_rate,
                baseline_recovery_rate=comp.baseline_recovery_rate,
                absolute_recovery_delta=comp.absolute_recovery_delta,
                relative_recovery_delta=comp.relative_recovery_delta,
                apro_gross_recovered=comp.apro_gross_recovered,
                baseline_gross_recovered=comp.baseline_gross_recovered,
                incremental_recovered_amount=comp.incremental_recovered_amount,
                apro_net_recovered=comp.apro_net_recovered,
                baseline_net_recovered=comp.baseline_net_recovered,
                incremental_net_revenue=comp.incremental_net_revenue,
                apro_intervention_cost=comp.apro_intervention_cost,
                baseline_intervention_cost=comp.baseline_intervention_cost,
                delta_recovery_ci_95=list(comp.delta_recovery_ci_95)
                if comp.delta_recovery_ci_95
                else None,
                delta_net_revenue_ci_95=list(comp.delta_net_revenue_ci_95)
                if comp.delta_net_revenue_ci_95
                else None,
                p_value=comp.p_value,
                adjusted_p_value=comp.adjusted_p_value,
                comparison_label=label,
                is_statistically_significant=comp.is_statistically_significant,
            )
            comparisons.append(dto)

        return BenchmarksResponse(
            status="ok",
            metadata=self._make_metadata(report),
            data=comparisons,
        )

    async def get_prediction_quality(
        self, benchmark_run_id: str | None = None
    ) -> PredictionQualityResponse:
        """GET /api/dashboard/prediction-quality."""
        report = await self.resolve_benchmark_report(benchmark_run_id)
        if report is None:
            return PredictionQualityResponse(
                status="empty",
                metadata=self._make_metadata(),
            )

        pred = report.prediction_quality
        dec = report.decision_quality

        bins: list[CalibrationBinDTO] = []
        cls_metrics: ClassificationMetricsDTO | None = None
        if pred is not None:
            bins = [
                CalibrationBinDTO(
                    bin_index=b.bin_index,
                    bin_lower=b.bin_lower,
                    bin_upper=b.bin_upper,
                    sample_count=b.sample_count,
                    mean_predicted_prob=b.predicted_mean_probability,
                    empirical_recovery_rate=b.empirical_success_rate,
                )
                for b in pred.calibration_curve
            ]

            cls_metrics = ClassificationMetricsDTO(
                accuracy=None,
                precision=pred.precision,
                recall=pred.recall,
                f1_score=pred.f1_score,
                roc_auc=pred.roc_auc,
                pr_auc=pred.pr_auc,
                log_loss=pred.log_loss,
            )

        dec_metrics: DecisionQualityDTO | None = None
        if dec is not None:
            dec_metrics = DecisionQualityDTO(
                action_regret_avg=dec.action_regret_avg,
                oracle_gap_avg=dec.oracle_gap_avg,
                best_action_selection_rate=dec.best_action_selection_rate,
            )

        return PredictionQualityResponse(
            status="ok",
            metadata=self._make_metadata(report),
            brier_score=pred.brier_score if pred else None,
            calibration_bins=bins,
            classification_metrics=cls_metrics,
            decision_quality=dec_metrics,
        )

    async def get_adaptive(
        self, benchmark_run_id: str | None = None
    ) -> AdaptiveRecoveryResponse:
        """GET /api/dashboard/adaptive."""
        report = await self.resolve_benchmark_report(benchmark_run_id)
        if report is None:
            return AdaptiveRecoveryResponse(
                status="empty",
                metadata=self._make_metadata(),
            )

        adapt = report.adaptive_loop_metrics
        if adapt is None:
            return AdaptiveRecoveryResponse(
                status="ok",
                metadata=self._make_metadata(report),
            )

        return AdaptiveRecoveryResponse(
            status="ok",
            metadata=self._make_metadata(report),
            single_cycle_recovery_count=adapt.single_cycle_recovery_count,
            single_cycle_recovery_rate=adapt.single_cycle_recovery_rate,
            multi_cycle_recovery_count=adapt.multi_cycle_recovery_count,
            multi_cycle_recovery_rate=adapt.multi_cycle_recovery_rate,
            re_evaluated_cases_count=adapt.re_evaluation_count,
            re_evaluation_recovery_rate=adapt.recovery_after_re_evaluation_rate,
            mean_cycles_to_recovery=adapt.mean_cycles_to_recovery or 0.0,
            median_cycles_to_recovery=adapt.median_cycles_to_recovery or 0.0,
            same_action_avoidance_rate=adapt.same_action_avoidance_rate,
            bounded_termination_rate=adapt.bounded_termination_rate,
            hard_ceiling_violations=None,
            cycle_distribution=[],
        )

    async def get_safety(self, benchmark_run_id: str | None = None) -> SafetyResponse:
        """GET /api/dashboard/safety."""
        report = await self.resolve_benchmark_report(benchmark_run_id)
        if report is None:
            return SafetyResponse(
                status="empty",
                metadata=self._make_metadata(),
                overall_safety_status="NO_DATA",
            )

        safety = report.safety_metrics
        invariants: list[SafetyInvariantCheckDTO] = [
            SafetyInvariantCheckDTO(
                invariant_name="Unsafe Dispatches",
                description=(
                    "Zero dispatches executed without valid policy authorization"
                ),
                violation_count=safety.unsafe_dispatch_count,
                status="PASS" if safety.unsafe_dispatch_count == 0 else "FAIL",
            ),
            SafetyInvariantCheckDTO(
                invariant_name="Policy Bypasses",
                description="Zero bypasses of Phase 10 safety constraints",
                violation_count=safety.policy_bypass_count,
                status="PASS" if safety.policy_bypass_count == 0 else "FAIL",
            ),
            SafetyInvariantCheckDTO(
                invariant_name="Stale Policy Reuse",
                description=(
                    "Zero reuse of stale policy decisions for changed recovery actions"
                ),
                violation_count=safety.stale_policy_rejection_count,
                status="PASS" if safety.stale_policy_rejection_count == 0 else "FAIL",
            ),
            SafetyInvariantCheckDTO(
                invariant_name="Duplicate Executions",
                description="Zero redundant duplicate executions dispatched per cycle",
                violation_count=safety.duplicate_execution_attempt_count,
                status="PASS"
                if safety.duplicate_execution_attempt_count == 0
                else "FAIL",
            ),
            SafetyInvariantCheckDTO(
                invariant_name="State Guards",
                description="Zero invalid state transitions",
                violation_count=safety.state_guard_rejection_count,
                status="PASS" if safety.state_guard_rejection_count == 0 else "FAIL",
            ),
            SafetyInvariantCheckDTO(
                invariant_name="Terminal Integrity",
                description="Zero reopenings of finalized terminal cases",
                violation_count=safety.terminal_case_reopen_attempt_count,
                status="PASS"
                if safety.terminal_case_reopen_attempt_count == 0
                else "FAIL",
            ),
            SafetyInvariantCheckDTO(
                invariant_name="Transport Safety",
                description="Zero unknown provider transports",
                violation_count=safety.provider_transport_unknown_count,
                status="PASS"
                if safety.provider_transport_unknown_count == 0
                else "FAIL",
            ),
        ]

        overall_status = "PASS"
        if any(inv.status == "FAIL" for inv in invariants):
            overall_status = "FAIL"
        elif safety.provider_transport_unknown_count > 0:
            overall_status = "WARNING"

        return SafetyResponse(
            status="ok",
            metadata=self._make_metadata(report),
            overall_safety_status=overall_status,
            unsafe_dispatch_count=safety.unsafe_dispatch_count,
            policy_bypass_count=safety.policy_bypass_count,
            stale_policy_reuse_count=safety.stale_policy_rejection_count,
            duplicate_execution_count=safety.duplicate_execution_attempt_count,
            duplicate_outcome_count=safety.duplicate_outcome_count,
            state_guard_rejections=safety.state_guard_rejection_count,
            terminal_case_reopen_attempts=safety.terminal_case_reopen_attempt_count,
            provider_unknown_count=safety.provider_transport_unknown_count,
            provider_unknown_rate=safety.provider_transport_unknown_rate,
            invariants=invariants,
        )

    async def get_cohorts(self, benchmark_run_id: str | None = None) -> CohortsResponse:
        """GET /api/dashboard/cohorts."""
        report = await self.resolve_benchmark_report(benchmark_run_id)
        if report is None:
            return CohortsResponse(
                status="empty",
                metadata=self._make_metadata(),
                cohorts=[],
            )

        dtos: list[CohortBreakdownDTO] = []
        for _dim, items in report.cohort_breakdowns.items():
            for c in items:
                dtos.append(
                    CohortBreakdownDTO(
                        dimension=c.dimension,
                        cohort_key=c.cohort_key,
                        cohort_name=c.cohort_key,
                        case_count=c.case_count,
                        recovered_count=int(round(c.case_count * c.recovery_rate)),
                        recovery_rate=c.recovery_rate,
                        gross_recovered_amount=c.gross_recovered,
                        net_recovered_revenue=c.net_recovered,
                        small_cohort_flag=c.is_small_cohort,
                    )
                )

        return CohortsResponse(
            status="ok",
            metadata=self._make_metadata(report),
            cohorts=dtos,
        )

    async def get_reproducibility(
        self, benchmark_run_id: str
    ) -> ReproducibilityResponse:
        """GET /api/dashboard/reproducibility/{benchmark_run_id}."""
        report = await self.resolve_benchmark_report(benchmark_run_id)
        if report is None:
            raise KeyError(f"Benchmark run '{benchmark_run_id}' not found.")

        seed = int(report.reproducibility_metadata.get("bootstrap_seed", 42))
        iters = int(report.reproducibility_metadata.get("bootstrap_iterations", 1000))

        cost_model = report.evaluation_config.cost_model
        cost_dict = {
            "retry_cost": cost_model.retry_cost,
            "payment_link_cost": cost_model.payment_link_cost,
            "outreach_cost": cost_model.outreach_cost,
            "escalation_cost": cost_model.escalation_cost,
            "stop_cost": cost_model.stop_cost,
        }

        return ReproducibilityResponse(
            status="ok",
            metadata=self._make_metadata(report),
            benchmark_run_id=report.benchmark_run_id,
            dataset_id=report.dataset_id,
            dataset_version=report.dataset_version,
            snapshot_hash=report.snapshot_hash,
            evaluation_config_version=report.evaluation_config_version,
            metric_schema_version=report.metric_schema_version,
            code_revision=report.code_revision,
            bootstrap_seed=seed,
            bootstrap_iterations=iters,
            report_hash=report.report_hash,
            created_at=report.created_at,
            limitations=report.limitations,
            cost_model=cost_dict,
        )

    async def list_cases(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        search: str | None = None,
    ) -> CaseListResponse:
        """GET /api/dashboard/cases with pagination and search."""
        try:
            uow = await self._get_uow()
            async with uow:
                # Query canonical cases from database
                all_cases = await uow.recovery_cases.find_all(limit=1000)

                items: list[CaseSummaryDTO] = []
                for c in all_cases:
                    if status and c.status.value != status:
                        continue
                    if search and search not in c.case_id:
                        continue

                    # Lookup payment amount
                    amt = 0
                    curr = "INR"
                    pay = await uow.payments.get_by_id(c.payment_id)
                    if pay:
                        amt = pay.amount
                        curr = pay.currency

                    # Lookup outcome
                    outcomes = await uow.outcomes.find_by_case_id(c.case_id)
                    is_rec = any(o.type.value == "RECOVERED" for o in outcomes)
                    rec_amt = sum(
                        o.amount_recovered
                        for o in outcomes
                        if o.type.value == "RECOVERED"
                    )

                    # Lookup decision
                    decisions = await uow.decisions.find_by_case_id(c.case_id)
                    action = (
                        decisions[-1].recommended_action.value if decisions else None
                    )

                    items.append(
                        CaseSummaryDTO(
                            case_id=c.case_id,
                            payment_id=c.payment_id,
                            amount=amt,
                            currency=curr,
                            status=c.status.value,
                            selected_action=action,
                            cycle_count=len(decisions) or 1,
                            is_recovered=is_rec,
                            recovered_amount=rec_amt,
                            opened_at=c.opened_at.isoformat()
                            if hasattr(c.opened_at, "isoformat")
                            else str(c.opened_at),
                            closed_at=c.closed_at.isoformat()
                            if hasattr(c.closed_at, "isoformat") and c.closed_at
                            else None,
                        )
                    )

                total = len(items)
                start_idx = (page - 1) * page_size
                page_items = items[start_idx : start_idx + page_size]
                total_pages = max(1, (total + page_size - 1) // page_size)

                return CaseListResponse(
                    status="ok",
                    metadata=self._make_metadata(),
                    items=page_items,
                    total_count=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                )
        except Exception as err:
            raise EvaluationPersistenceError(
                f"Failed to query cases from database: {err}"
            ) from err

    async def get_case_detail(self, case_id: str) -> CaseDetailResponse:
        """GET /api/dashboard/cases/{case_id} via Phase 14 reconstruction."""
        try:
            uow = await self._get_uow()
            async with uow:
                trace = await CaseReconstructionService.reconstruct_case(
                    case_id=case_id, uow=uow
                )
                return CaseDetailResponse(
                    status="ok",
                    metadata=self._make_metadata(),
                    case=trace.model_dump(mode="json"),
                )
        except AuditNotFoundError as err:
            raise KeyError(f"Case '{case_id}' not found.") from err
        except KeyError:
            raise
        except Exception as err:
            raise EvaluationPersistenceError(
                f"Failed to reconstruct case '{case_id}': {err}"
            ) from err

    async def get_case_timeline(self, case_id: str) -> CaseTimelineResponse:
        """GET /api/dashboard/cases/{case_id}/timeline."""
        try:
            uow = await self._get_uow()
            async with uow:
                trace = await CaseReconstructionService.reconstruct_case(
                    case_id=case_id, uow=uow
                )
                events = [
                    AuditEventDTO(
                        audit_event_id=e.audit_event_id,
                        case_id=e.case_id,
                        event_type=e.event_type.value
                        if hasattr(e.event_type, "value")
                        else str(e.event_type),
                        actor=e.actor.value
                        if hasattr(e.actor, "value")
                        else str(e.actor),
                        timestamp=e.timestamp.isoformat()
                        if hasattr(e.timestamp, "isoformat")
                        else str(e.timestamp),
                        payload=e.payload,
                        correlation_id=e.correlation_id,
                    )
                    for e in trace.events
                ]
                return CaseTimelineResponse(
                    status="ok",
                    metadata=self._make_metadata(),
                    case_id=case_id,
                    events=events,
                )
        except AuditNotFoundError as err:
            raise KeyError(f"Case '{case_id}' not found.") from err
        except KeyError:
            raise
        except Exception as err:
            raise EvaluationPersistenceError(
                f"Failed to reconstruct case timeline '{case_id}': {err}"
            ) from err

    async def get_reviewer_questions(self, case_id: str) -> ReviewerQuestionsResponse:
        """GET /api/dashboard/cases/{case_id}/reviewer-questions."""
        try:
            uow = await self._get_uow()
            async with uow:
                trace = await CaseReconstructionService.reconstruct_case(
                    case_id=case_id, uow=uow
                )
                compl = (
                    trace.completeness.value
                    if hasattr(trace.completeness, "value")
                    else str(trace.completeness)
                )
                return ReviewerQuestionsResponse(
                    status="ok",
                    metadata=self._make_metadata(),
                    case_id=case_id,
                    completeness=compl,
                    integrity_valid=trace.integrity_valid,
                    integrity_issues=trace.integrity_issues,
                    questions=trace.reviewer_answers,
                )
        except AuditNotFoundError as err:
            raise KeyError(f"Case '{case_id}' not found.") from err
        except KeyError:
            raise
        except Exception as err:
            raise EvaluationPersistenceError(
                f"Failed to reconstruct reviewer questions for case '{case_id}': {err}"
            ) from err

    async def list_benchmark_runs(self) -> BenchmarkRunListResponse:
        """GET /api/dashboard/runs."""
        if hasattr(self._eval_store, "list_reports"):
            if isinstance(self._eval_store, PostgreSQLEvaluationArtifactStore):
                raw_runs = await self._eval_store.list_reports()
            else:
                raw_runs = self._eval_store.list_reports()
        else:
            raw_runs = []

        summaries = [
            BenchmarkRunSummaryDTO(
                benchmark_run_id=r["benchmark_run_id"],
                report_id=r["report_id"],
                dataset_id=r["dataset_id"],
                dataset_version=r["dataset_version"],
                report_hash=r["report_hash"],
                recovery_rate=r["recovery_rate"],
                gross_recovered_amount=r.get("gross_recovered_amount", 0),
                net_recovered_revenue=r["net_recovered_revenue"],
                is_synthetic_demo=r.get("is_synthetic_demo", False),
                created_at=r["created_at"],
            )
            for r in raw_runs
        ]

        return BenchmarkRunListResponse(
            status="ok",
            metadata=self._make_metadata(),
            runs=summaries,
        )
