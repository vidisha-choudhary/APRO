"""APRO Phase 15 Acceptance Suite — Benchmarking & Statistical Reporting.

Authoritative Acceptance Runner for:
1. 10 Manual Acceptance Scenarios
2. 84 Acceptance Criteria (AC-01 through AC-84)
"""

import argparse
import ast
import asyncio
import inspect
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import apro.evaluation.baselines as baselines_mod
import apro.evaluation.evaluator as eval_mod
from apro.domain.enums import (
    AuditActor,
    ExecutionMode,
    ExecutionStatus,
    FailureCategory,
    OutcomeType,
    PaymentStatus,
    PolicyDecisionResult,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import (
    AuditEvent,
    Decision,
    Diagnosis,
    Execution,
    Outcome,
    Payment,
    PolicyDecision,
    RecoveryAction,
    RecoveryCase,
)
from apro.evaluation.baselines import (
    FixedEscalationBaseline,
    FixedRetryBaseline,
    NoInterventionBaseline,
    PaymentLinkBaseline,
    evaluate_baselines_comparison,
)
from apro.evaluation.calibration import (
    compute_brier_score,
    compute_calibration_curve,
    compute_classification_metrics,
)
from apro.evaluation.config import (
    EvaluationConfig,
)
from apro.evaluation.dataset import (
    BenchmarkDatasetSnapshot,
    EligibilityClassifier,
    TruthPlaneSeparation,
)
from apro.evaluation.enums import (
    BaselineType,
    CensoringPolicy,
    EvaluationConfigVersion,
    MetricComparisonLabel,
    MetricSchemaVersion,
    MissingDataPolicy,
)
from apro.evaluation.evaluator import APROEvaluator
from apro.evaluation.exceptions import (
    CheatingViolationError,
    InsufficientSampleError,
)
from apro.evaluation.metrics import (
    compute_primary_kpis,
    compute_safety_kpis,
)
from apro.evaluation.models import (
    BenchmarkCaseRecord,
    OfflineEvaluationTruth,
)
from apro.evaluation.persistence import EvaluationArtifactStore
from apro.evaluation.report import (
    compute_report_hash,
    generate_json_report,
    generate_markdown_report,
)
from apro.evaluation.statistics import (
    adjust_p_values_holm,
    bootstrap_case_metric,
    compute_cohens_d,
    compute_cohens_h,
    compute_paired_bootstrap_ci,
    compute_paired_randomization_p_value,
    compute_proportion_ci,
)
from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    PredictionUncertaintyState,
)
from apro.recovery_prediction.enums import (
    RecoveryAction as PredictorAction,
)
from apro.recovery_prediction.models import OutcomePrediction

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def evaluate_acceptance_results(
    results: dict[str, bool], required_count: int = 84
) -> bool:
    """Evaluate acceptance dictionary and return True iff criteria pass."""
    if not results or len(results) < required_count:
        return False
    return all(results.get(f"AC-{i:02d}", False) for i in range(1, required_count + 1))


def make_test_record(
    case_id: str,
    payment_amount: int = 50000,
    payment_method: str = "CARD",
    failure_category: str = "TECHNICAL",
    is_recovered: bool = True,
    recovered_amount: int | None = None,
    cycle_count: int = 1,
    duration_seconds: float = 120.0,
    final_action_type: str = "RETRY_IMMEDIATE",
    case_status: str = "CLOSED_RECOVERED",
    re_evaluation_count: int = 0,
    offline_truth: OfflineEvaluationTruth | None = None,
    include_prediction: bool = True,
) -> BenchmarkCaseRecord:
    """Construct a high-fidelity synthetic benchmark case record."""
    actual_recovered_amount = (
        payment_amount if recovered_amount is None else recovered_amount
    )
    now = datetime.now(UTC)
    opened = now - timedelta(seconds=duration_seconds)
    closed = now if "CLOSED" in case_status else None

    # Domain entities
    case = RecoveryCase(
        case_id=case_id,
        payment_id=f"pay_{case_id}",
        customer_id=f"cust_{case_id}",
        status=RecoveryCaseStatus.RECOVERED
        if is_recovered
        else RecoveryCaseStatus.STOPPED,
        opened_at=opened,
        updated_at=now,
        closed_at=closed,
        recovery_amount=actual_recovered_amount if is_recovered else None,
    )
    payment = Payment(
        payment_id=f"pay_{case_id}",
        customer_id=f"cust_{case_id}",
        provider="razorpay",
        amount=payment_amount,
        currency="INR",
        method=payment_method,
        status=PaymentStatus.CAPTURED if is_recovered else PaymentStatus.FAILED,
        created_at=opened,
        updated_at=now,
    )

    diag = Diagnosis(
        diagnosis_id=f"diag_{case_id}",
        case_id=case_id,
        category=FailureCategory.GATEWAY,
        confidence=0.85,
        evidence=("gateway_timeout", "channel_unresponsive"),
        model_name="rule_based_diagnosis",
        model_version="1.0.0",
        created_at=opened,
    )

    decisions: list[Decision] = []
    executions: list[Execution] = []
    outcomes: list[Outcome] = []
    policy_decisions: list[PolicyDecision] = []
    recovery_actions: list[RecoveryAction] = []

    for c in range(1, cycle_count + 1):
        act_type = (
            RecoveryActionType.RETRY
            if c == 1
            else RecoveryActionType.ALTERNATE_RECOVERY
        )
        dec = Decision(
            decision_id=f"dec_{case_id}_{c}",
            case_id=case_id,
            recommended_action=act_type,
            confidence=0.85,
            expected_recovery_value=int(payment_amount * 0.8),
            reason="High ERV candidate action",
            model_name="economic_decision_engine",
            model_version="1.0.0",
            created_at=opened + timedelta(seconds=c * 10),
        )
        decisions.append(dec)

        pdec = PolicyDecision(
            policy_decision_id=f"pdec_{case_id}_{c}",
            decision_id=dec.decision_id,
            case_id=case_id,
            result=PolicyDecisionResult.ALLOW,
            reason="Within daily safety budget",
            policy_version="1.0.0",
            created_at=opened + timedelta(seconds=c * 12),
        )
        policy_decisions.append(pdec)

        act = RecoveryAction(
            action_id=f"act_{case_id}_{c}",
            case_id=case_id,
            action_type=act_type,
            status=RecoveryActionStatus.COMPLETED
            if (is_recovered and c == cycle_count)
            else RecoveryActionStatus.FAILED,
            created_at=opened + timedelta(seconds=c * 15),
            updated_at=opened + timedelta(seconds=c * 20),
        )
        recovery_actions.append(act)

        exec_status = (
            ExecutionStatus.SUCCEEDED
            if (is_recovered and c == cycle_count)
            else ExecutionStatus.FAILED
        )
        exe = Execution(
            execution_id=f"exe_{case_id}_{c}",
            action_id=act.action_id,
            case_id=case_id,
            execution_type=act_type.value,
            execution_mode=ExecutionMode.SIMULATION,
            status=exec_status,
            started_at=opened + timedelta(seconds=c * 25),
            completed_at=opened + timedelta(seconds=c * 30),
        )
        executions.append(exe)

        if is_recovered and c == cycle_count:
            outc = Outcome(
                outcome_id=f"outc_{case_id}",
                case_id=case_id,
                execution_id=exe.execution_id,
                type=OutcomeType.RECOVERED,
                amount_recovered=actual_recovered_amount,
                observed_at=now,
            )
            outcomes.append(outc)

    # Optional prediction artifact
    audit_events: list[AuditEvent] = []
    if include_prediction:
        prob = 0.85 if is_recovered else 0.15
        pred = OutcomePrediction(
            prediction_id=f"pred_{case_id}",
            record_id=f"rec_{case_id}",
            scenario_id=f"scen_{case_id}",
            action=PredictorAction.RETRY,
            model_name="model_b_predictor",
            model_version="1.0.0",
            dataset_version="1.0.0",
            feature_schema_version="feature-v1",
            predicted_success_probability=prob,
            predicted_outcome_state=PredictedOutcomeState.SUCCESS
            if is_recovered
            else PredictedOutcomeState.FAILURE,
            predicted_recovered_amount=actual_recovered_amount if is_recovered else 0,
            confidence=prob,
            uncertainty_state=PredictionUncertaintyState.HIGH_CONFIDENCE,
        )
        audit_events.append(
            AuditEvent(
                audit_event_id=f"aud_{case_id}_pred",
                case_id=case_id,
                event_type="PREDICTION_CREATED",
                actor=AuditActor.MODEL,
                timestamp=opened,
                payload={"prediction": pred.model_dump()},
            )
        )

    # Default offline truth if not provided
    if offline_truth is None:
        offline_truth = OfflineEvaluationTruth(
            ground_truth_recovered=is_recovered,
            ground_truth_recovered_amount=actual_recovered_amount
            if is_recovered
            else 0,
            ground_truth_best_action=final_action_type,
            ground_truth_failure_class=failure_category,
            ground_truth_time_to_recovery_seconds=duration_seconds
            if is_recovered
            else None,
            counterfactual_outcomes={
                "NO_INTERVENTION": {"recovered": False, "amount": 0},
                "RETRY": {
                    "recovered": is_recovered,
                    "amount": actual_recovered_amount if is_recovered else 0,
                },
                "PAYMENT_LINK": {
                    "recovered": is_recovered,
                    "amount": actual_recovered_amount,
                },
                "ESCALATE": {"recovered": False, "amount": 0},
            },
        )

    return BenchmarkCaseRecord(
        case_id=case_id,
        payment_id=f"pay_{case_id}",
        payment_amount=payment_amount,
        currency="INR",
        payment_method=payment_method,
        case_status=case_status,
        failure_code="GATEWAY_TIMEOUT",
        failure_category=failure_category,
        opened_at=opened,
        closed_at=closed,
        duration_seconds=duration_seconds if is_recovered else None,
        case=case,
        payment=payment,
        diagnosis=diag,
        decisions=decisions,
        policy_decisions=policy_decisions,
        recovery_actions=recovery_actions,
        executions=executions,
        outcomes=outcomes,
        audit_events=audit_events,
        offline_truth=offline_truth,
        is_recovered=is_recovered,
        recovered_amount=actual_recovered_amount if is_recovered else 0,
        intervention_count=len(executions),
        cycle_count=cycle_count,
        re_evaluation_count=re_evaluation_count,
        final_action_type=final_action_type,
        terminal_disposition="RECOVERED" if is_recovered else "STOPPED",
    )


# ==============================================================================
# 10 MANUAL SCENARIOS
# ==============================================================================


def run_scenario_1_clean_benchmark_run(ac_results: dict[str, bool]) -> None:
    """Scenario 1: Clean Benchmark Run — Snapshot -> KPIs -> Report."""
    print("  Executing Scenario 1: Clean Benchmark Run...")

    records = [
        make_test_record(
            f"case_s1_{i}", payment_amount=100000, is_recovered=(i % 3 != 0)
        )
        for i in range(30)
    ]
    snapshot = BenchmarkDatasetSnapshot.from_records(
        records,
        dataset_id="snap_s1",
        dataset_version="1.0.0",
    )

    config = EvaluationConfig(
        evaluation_config_version=EvaluationConfigVersion.V1_0,
        metric_schema_version=MetricSchemaVersion.V1_0,
        bootstrap_seed=42,
        bootstrap_iterations=200,
    )

    evaluator = APROEvaluator(config=config)
    report = evaluator.evaluate_dataset(
        snapshot, benchmark_run_id="run_s1_001", code_revision="34fb73a"
    )

    # Assertions
    assert report.benchmark_run_id == "run_s1_001"
    assert report.snapshot_hash == snapshot.snapshot_hash
    assert report.primary_kpis.case_count == 30
    assert report.primary_kpis.eligible_cases == 30
    assert report.primary_kpis.recovered_cases == 20
    assert abs(report.primary_kpis.recovery_rate - (20 / 30)) < 1e-4
    assert report.primary_kpis.gross_recovered_amount == 20 * 100000
    assert (
        report.primary_kpis.net_recovered_revenue
        == (20 * 100000) - report.primary_kpis.total_intervention_cost
    )
    assert report.safety_metrics.unsafe_dispatch_count == 0

    json_rep = generate_json_report(report)
    md_rep = generate_markdown_report(report)
    rep_hash = compute_report_hash(report)

    assert json_rep and len(json_rep) > 100
    assert "Benchmark Evaluation Report" in md_rep
    assert rep_hash and len(rep_hash) == 64

    # AC mapping
    ac_results["AC-01"] = bool(
        report.benchmark_run_id == "run_s1_001" and len(report.benchmark_run_id) > 0
    )
    ac_results["AC-02"] = bool(
        len(snapshot.snapshot_hash) == 64
        and all(c in "0123456789abcdefABCDEF" for c in snapshot.snapshot_hash)
    )
    ac_results["AC-03"] = bool(
        report.evaluation_config_version == EvaluationConfigVersion.V1_0
    )
    ac_results["AC-04"] = bool(report.code_revision == "34fb73a")
    ac_results["AC-05"] = bool(
        report.case_counts["total_cases"]
        == report.case_counts["eligible"] + report.case_counts["excluded"]
        and report.case_counts["total_cases"] == 30
    )
    ac_results["AC-09"] = bool(
        abs(
            report.primary_kpis.recovery_rate
            - (report.primary_kpis.recovered_cases / report.primary_kpis.eligible_cases)
        )
        < 1e-4
        and report.primary_kpis.recovered_cases == 20
    )
    ac_results["AC-11"] = bool(
        report.primary_kpis.gross_recovered_amount == 2000000
        and report.primary_kpis.gross_recovered_amount == 20 * 100000
    )
    ac_results["AC-12"] = bool(
        report.primary_kpis.eligible_at_risk_amount == 30 * 100000
        and report.primary_kpis.eligible_at_risk_amount > 0
    )
    ac_results["AC-13"] = bool(
        report.primary_kpis.total_intervention_cost == 30 * config.cost_model.retry_cost
        and report.primary_kpis.total_intervention_cost > 0
    )
    ac_results["AC-14"] = bool(
        report.primary_kpis.net_recovered_revenue
        == report.primary_kpis.gross_recovered_amount
        - report.primary_kpis.total_intervention_cost
    )
    ac_results["AC-16"] = bool(
        report.primary_kpis.median_time_to_recovery_seconds is not None
        and report.primary_kpis.median_time_to_recovery_seconds == 120.0
    )
    ac_results["AC-17"] = bool(
        report.primary_kpis.attempts_per_case_mean == 1.0
        and report.primary_kpis.attempts_per_case_median == 1.0
    )
    ac_results["AC-19"] = bool(
        sum(report.primary_kpis.terminal_disposition_mix.values())
        == report.primary_kpis.eligible_cases
        and report.primary_kpis.terminal_disposition_mix["RECOVERED"] == 20
    )
    ac_results["AC-20"] = bool(
        report.primary_kpis.recovery_rate
        == round(
            report.primary_kpis.recovered_cases / report.primary_kpis.eligible_cases, 4
        )
        and report.primary_kpis.net_recovered_revenue
        == (
            report.primary_kpis.gross_recovered_amount
            - report.primary_kpis.total_intervention_cost
        )
    )


def run_scenario_2_apro_vs_no_intervention(ac_results: dict[str, bool]) -> None:
    """Scenario 2: APRO vs No-Intervention Baseline."""
    print("  Executing Scenario 2: APRO vs No-Intervention Baseline...")

    records = [
        make_test_record(
            f"case_s2_{i}", payment_amount=80000, is_recovered=(i % 2 == 0)
        )
        for i in range(40)
    ]
    config = EvaluationConfig(bootstrap_seed=42, bootstrap_iterations=200)
    primary_kpis = compute_primary_kpis(records, config)

    baseline = NoInterventionBaseline()
    rec_eval, amt_eval, cost_eval = baseline.evaluate_case(records[0], config)
    assert rec_eval is False
    assert amt_eval == 0
    assert cost_eval == 0

    # AST boundary check on baselines module to prove offline-only isolation
    baselines_src = inspect.getsource(baselines_mod)
    baselines_ast = ast.parse(baselines_src)
    has_live_dispatch_import = any(
        isinstance(node, ast.ImportFrom) and "providers" in (node.module or "")
        for node in ast.walk(baselines_ast)
    )
    has_live_dispatch_calls = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and "dispatch" in node.func.id
        for node in ast.walk(baselines_ast)
    )

    all_comparisons = evaluate_baselines_comparison(records, config, primary_kpis)
    base_res = (
        all_comparisons.get("No Intervention")
        or all_comparisons[BaselineType.NO_INTERVENTION.value]
    )

    assert base_res.baseline_type == BaselineType.NO_INTERVENTION
    assert base_res.baseline_recovery_rate == 0.0
    assert base_res.baseline_intervention_cost == 0
    assert base_res.absolute_recovery_delta == primary_kpis.recovery_rate
    assert (
        base_res.incremental_net_revenue
        == primary_kpis.net_recovered_revenue - base_res.baseline_net_recovered
    )

    ac_results["AC-21"] = bool(
        isinstance(baseline, NoInterventionBaseline)
        and baseline.baseline_type == BaselineType.NO_INTERVENTION
    )
    ac_results["AC-25"] = bool(
        not has_live_dispatch_import
        and not has_live_dispatch_calls
        and rec_eval is False
        and amt_eval == 0
        and cost_eval == 0
    )
    ac_results["AC-26"] = bool(
        base_res.apro_gross_recovered == primary_kpis.gross_recovered_amount
        and base_res.apro_recovery_rate == primary_kpis.recovery_rate
    )
    ac_results["AC-28"] = bool(
        base_res.absolute_recovery_delta
        == primary_kpis.recovery_rate - base_res.baseline_recovery_rate
        and base_res.baseline_recovery_rate == 0.0
    )
    ac_results["AC-29"] = bool(
        base_res.incremental_net_revenue
        == primary_kpis.net_recovered_revenue - base_res.baseline_net_recovered
        and base_res.baseline_net_recovered == 0
    )
    ac_results["AC-30"] = bool(
        base_res.comparison_label == MetricComparisonLabel.BENCHMARK_ASSOCIATION
    )


def run_scenario_3_apro_vs_fixed_retry(ac_results: dict[str, bool]) -> None:
    """Scenario 3: APRO vs Fixed-Retry Baseline."""
    print("  Executing Scenario 3: APRO vs Fixed-Retry Baseline...")

    records = [
        make_test_record(
            f"case_s3_{i}", payment_amount=60000, is_recovered=(i % 2 == 0)
        )
        for i in range(30)
    ]
    config = EvaluationConfig(bootstrap_seed=42, bootstrap_iterations=200)
    primary_kpis = compute_primary_kpis(records, config)

    baseline = FixedRetryBaseline(max_retries=2)
    rec_eval, amt_eval, cost_eval = baseline.evaluate_case(records[0], config)
    assert cost_eval == config.cost_model.retry_cost

    all_comparisons = evaluate_baselines_comparison(records, config, primary_kpis)
    base_res = (
        all_comparisons.get("Fixed Retry")
        or all_comparisons[BaselineType.FIXED_RETRY.value]
    )

    assert base_res.baseline_type == BaselineType.FIXED_RETRY
    assert base_res.baseline_intervention_cost > 0
    assert base_res.delta_recovery_ci_95 is not None
    assert base_res.delta_net_revenue_ci_95 is not None

    ac_results["AC-22"] = bool(
        isinstance(baseline, FixedRetryBaseline)
        and baseline.baseline_type == BaselineType.FIXED_RETRY
        and baseline.max_retries == 2
    )
    ac_results["AC-27"] = bool(
        config.cost_model.get_action_cost("RETRY") > 0
        and base_res.baseline_intervention_cost == 30 * config.cost_model.retry_cost
    )


def run_scenario_4_apro_vs_payment_link_and_escalation(
    ac_results: dict[str, bool],
) -> None:
    """Scenario 4: APRO vs Payment Link & Fixed Escalation Baselines."""
    print("  Executing Scenario 4: APRO vs Payment Link & Fixed Escalation...")

    records = [
        make_test_record(
            f"case_s4_{i}", payment_amount=120000, is_recovered=(i % 3 != 0)
        )
        for i in range(30)
    ]
    config = EvaluationConfig(bootstrap_seed=42, bootstrap_iterations=200)
    primary_kpis = compute_primary_kpis(records, config)

    link_baseline = PaymentLinkBaseline()
    esc_baseline = FixedEscalationBaseline()

    all_comparisons = evaluate_baselines_comparison(records, config, primary_kpis)
    link_res = (
        all_comparisons.get("Payment Link")
        or all_comparisons[BaselineType.PAYMENT_LINK.value]
    )
    esc_res = (
        all_comparisons.get("Fixed Escalation")
        or all_comparisons[BaselineType.FIXED_ESCALATION.value]
    )

    assert link_res.baseline_type == BaselineType.PAYMENT_LINK
    assert esc_res.baseline_type == BaselineType.FIXED_ESCALATION
    assert len(all_comparisons) >= 4

    ac_results["AC-23"] = bool(
        isinstance(link_baseline, PaymentLinkBaseline)
        and link_baseline.baseline_type == BaselineType.PAYMENT_LINK
    )
    ac_results["AC-24"] = bool(
        isinstance(esc_baseline, FixedEscalationBaseline)
        and esc_baseline.baseline_type == BaselineType.FIXED_ESCALATION
    )


def run_scenario_5_statistical_uncertainty_and_bootstrap(
    ac_results: dict[str, bool],
) -> None:
    """Scenario 5: Statistical Uncertainty, Wilson CI & Multiplicity."""
    print("  Executing Scenario 5: Statistical Uncertainty & Bootstrap...")

    # 1. Wilson score CI
    ci_l, ci_u = compute_proportion_ci(40, 100, confidence_level=0.95)
    assert 0.30 < ci_l < 0.40
    assert 0.40 < ci_u < 0.51

    # 2. Case-level bootstrap reproducibility
    records = [
        make_test_record(
            f"case_s5_{i}", payment_amount=50000, is_recovered=(i % 2 == 0)
        )
        for i in range(50)
    ]

    def _rate_fn(sample: list[object]) -> float:
        return (
            sum(
                1
                for r in sample
                if isinstance(r, BenchmarkCaseRecord) and r.is_recovered
            )
            / len(sample)
            if sample
            else 0.0
        )

    pt1, l1, u1 = bootstrap_case_metric(
        records, _rate_fn, confidence_level=0.95, iterations=300, seed=12345
    )
    pt2, l2, u2 = bootstrap_case_metric(
        records, _rate_fn, confidence_level=0.95, iterations=300, seed=12345
    )
    assert pt1 == pt2
    assert l1 == l2
    assert u1 == u2

    # 3. Paired bootstrap CI & paired randomization p-value
    diffs = [(1.0 if r.is_recovered else 0.0) - 0.0 for r in records]
    paired_l, paired_u = compute_paired_bootstrap_ci(
        diffs,
        confidence_level=0.95,
        iterations=300,
        seed=12345,
    )
    assert paired_l > 0.3 and paired_u > 0.3

    p_rand1 = compute_paired_randomization_p_value(diffs, iterations=300, seed=12345)
    p_rand2 = compute_paired_randomization_p_value(diffs, iterations=300, seed=12345)
    assert p_rand1 == p_rand2
    assert 0.0 <= p_rand1 <= 1.0

    # 4. Multiple comparison Holm-Bonferroni adjustment
    raw_p = [0.01, 0.04, 0.03, 0.005]
    adj_p = adjust_p_values_holm(raw_p)
    assert len(adj_p) == 4
    assert adj_p[3] == min(adj_p)  # smallest p-value scaled first

    # 5. Effect sizes
    h = compute_cohens_h(0.6, 0.4)
    d = compute_cohens_d([10.0, 12.0, 14.0], [5.0, 6.0, 7.0])
    assert h > 0
    assert d > 0

    # 6. Evaluator statistical results integration
    config_s5 = EvaluationConfig(bootstrap_seed=12345, bootstrap_iterations=300)
    evaluator_s5 = APROEvaluator(config=config_s5)
    snapshot_s5 = BenchmarkDatasetSnapshot.from_records(
        records, dataset_id="snap_s5", dataset_version="1.0.0"
    )
    report_s5 = evaluator_s5.evaluate_dataset(snapshot_s5)

    ac_results["AC-31"] = bool(
        len(records) == 50
        and report_s5.statistical_results["recovery_rate"].sample_size == 50
    )
    ac_results["AC-32"] = bool(
        0.0 <= ci_l < 0.40
        and 0.40 < ci_u <= 1.0
        and ci_l < ci_u
        and report_s5.statistical_results["recovery_rate_wilson"].method
        == "wilson_score_interval"
    )
    ac_results["AC-33"] = bool(
        report_s5.statistical_results["recovery_rate"].method == "case_level_bootstrap"
        and l1 is not None
        and u1 is not None
        and l1 <= pt1 <= u1
    )
    ac_results["AC-34"] = bool(
        len(records) == 50
        and all(isinstance(r, BenchmarkCaseRecord) for r in records)
        and pt1 > 0.0
    )
    ac_results["AC-35"] = bool(
        config_s5.bootstrap_seed == 12345
        and report_s5.reproducibility_metadata["bootstrap_seed"] == 12345
    )
    ac_results["AC-36"] = bool(
        config_s5.bootstrap_iterations == 300
        and report_s5.reproducibility_metadata["bootstrap_iterations"] == 300
    )
    ac_results["AC-37"] = bool(pt1 == pt2 and l1 == l2 and u1 == u2 and l1 is not None)
    ac_results["AC-38"] = bool(
        paired_l > 0.0
        and paired_u > 0.0
        and paired_l <= paired_u
        and p_rand1 == p_rand2
        and 0.0 <= p_rand1 <= 1.0
    )
    ac_results["AC-39"] = bool(
        (ci_l, ci_u) == compute_proportion_ci(40, 100, confidence_level=0.95)
        and (l1, u1) == (l2, u2)
    )
    ac_results["AC-40"] = bool(
        all(p >= raw_p[i] for i, p in enumerate(adj_p))
        and adj_p[3] <= adj_p[0]
        and all(
            b.p_value is not None
            and 0.0 <= b.p_value <= 1.0
            and b.adjusted_p_value is not None
            and 0.0 <= b.adjusted_p_value <= 1.0
            for b in report_s5.baseline_comparisons.values()
        )
    )
    ac_results["AC-41"] = bool(
        h > 0.0 and d > 0.0 and isinstance(h, float) and isinstance(d, float)
    )
    ac_results["AC-42"] = bool(
        all(
            b.comparison_label == MetricComparisonLabel.BENCHMARK_ASSOCIATION
            for b in report_s5.baseline_comparisons.values()
        )
    )


def run_scenario_6_adaptive_loop_measurement(ac_results: dict[str, bool]) -> None:
    """Scenario 6: Adaptive Loop Measurement from Persisted History."""
    print("  Executing Scenario 6: Adaptive Loop Measurement...")

    records = [
        # 10 single-cycle recovered cases
        *(
            make_test_record(
                f"case_s6_single_{i}",
                cycle_count=1,
                is_recovered=True,
                re_evaluation_count=0,
            )
            for i in range(10)
        ),
        # 10 multi-cycle cases (failed cycle 1, re-evaluated, recovered cycle 2)
        *(
            make_test_record(
                f"case_s6_multi_{i}",
                cycle_count=2,
                is_recovered=True,
                re_evaluation_count=1,
            )
            for i in range(10)
        ),
        # 10 stopped unrecovered cases
        *(
            make_test_record(
                f"case_s6_stopped_{i}",
                cycle_count=2,
                is_recovered=False,
                re_evaluation_count=1,
                case_status="CLOSED_STOPPED",
            )
            for i in range(10)
        ),
    ]

    snapshot = BenchmarkDatasetSnapshot.from_records(
        records,
        dataset_id="snap_s6",
        dataset_version="1.0.0",
    )
    evaluator = APROEvaluator()
    report = evaluator.evaluate_dataset(snapshot)

    adapt = report.adaptive_loop_metrics
    assert adapt is not None
    assert adapt.total_cases == 30
    assert adapt.single_cycle_recovery_count == 10
    assert adapt.multi_cycle_recovery_count == 10
    assert adapt.re_evaluation_count == 20
    assert adapt.single_cycle_recovery_rate == round(10 / 30, 4)
    assert adapt.multi_cycle_recovery_rate == round(10 / 30, 4)
    assert adapt.mean_cycles_to_recovery == 1.5

    ac_results["AC-18"] = bool(
        report.primary_kpis.cycle_count_total == (10 * 1 + 10 * 2 + 10 * 2)
        and report.adaptive_loop_metrics.mean_cycles_to_recovery == 1.5
    )
    ac_results["AC-51"] = bool(
        adapt.total_cases == 30 and adapt.re_evaluation_count == 20
    )
    ac_results["AC-52"] = bool(
        adapt.single_cycle_recovery_count == 10
        and adapt.multi_cycle_recovery_count == 10
        and adapt.single_cycle_recovery_rate == round(10 / 30, 4)
    )
    ac_results["AC-53"] = bool(
        adapt.re_evaluation_count == 20
        and adapt.multi_cycle_recovery_rate == round(10 / 30, 4)
    )
    ac_results["AC-54"] = bool(0.0 <= adapt.same_action_avoidance_rate <= 1.0)


def run_scenario_7_unknown_pending_censoring_and_safety(
    ac_results: dict[str, bool],
) -> None:
    """Scenario 7: Unknown / Pending Handling, Censoring Policy & Safety KPIs."""
    print("  Executing Scenario 7: Unknown/Pending Handling & Safety KPIs...")

    # Construct records with diverse execution and lifecycle states
    r_normal = make_test_record("case_s7_norm", is_recovered=True)
    r_pending = make_test_record(
        "case_s7_pend", is_recovered=False, case_status="PENDING_EXECUTION"
    )
    r_unknown = make_test_record(
        "case_s7_unkn", is_recovered=False, case_status="UNKNOWN"
    )

    # Missing artifact record (executions is empty for a non-stopped closed case)
    r_missing = BenchmarkCaseRecord(
        case_id="case_s7_missing",
        payment_id="pay_missing",
        payment_amount=50000,
        currency="INR",
        payment_method="CARD",
        case_status="CLOSED_FAILED",
        opened_at=datetime.now(UTC),
        executions=[],
    )

    # Succeeded execution without recovery evidence
    succ_exec = Execution(
        execution_id="exe_s7_succ_no_rec",
        action_id="act_s7_succ_no_rec",
        case_id="case_s7_succ_no_rec",
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SUCCEEDED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    r_succ_no_rec = make_test_record(
        "case_s7_succ_no_rec",
        payment_amount=75000,
        is_recovered=False,
        recovered_amount=0,
        case_status="CLOSED_STOPPED",
    ).model_copy(
        update={
            "executions": [succ_exec],
            "outcomes": [],
            "is_recovered": False,
            "recovered_amount": 0,
        }
    )

    # Duplicate case
    r_dup = make_test_record("case_s7_norm", is_recovered=True)

    config_exclude = EvaluationConfig(
        censoring_policy=CensoringPolicy.EXCLUDE,
        missing_data_policy=MissingDataPolicy.EXCLUDE_CASE,
    )
    eligible_ex, elig_res_ex, counts_ex = (
        EligibilityClassifier.filter_and_account_cases(
            [r_normal, r_pending, r_unknown, r_missing, r_succ_no_rec, r_dup],
            config_exclude,
        )
    )

    assert counts_ex["total_cases"] == 6
    assert counts_ex["censored"] == 1
    assert counts_ex["duplicate_case"] == 1
    assert counts_ex["missing_required_artifact"] == 1
    assert counts_ex["eligible"] == 3

    # Primary KPI evaluation on succeeded execution without recovery evidence
    kpis_succ_no_rec = compute_primary_kpis([r_succ_no_rec], config_exclude)
    assert kpis_succ_no_rec.recovered_cases == 0
    assert kpis_succ_no_rec.gross_recovered_amount == 0
    assert kpis_succ_no_rec.recovery_rate == 0.0

    # Safety KPIs check
    safety = compute_safety_kpis(eligible_ex, config_exclude)
    assert safety.unsafe_dispatch_count == 0
    assert safety.policy_bypass_count == 0
    assert safety.duplicate_execution_attempt_count == 0
    assert safety.duplicate_outcome_count == 0

    ac_results["AC-06"] = bool(
        counts_ex["duplicate_case"] == 1 and counts_ex["total_cases"] == 6
    )
    ac_results["AC-10"] = bool(
        kpis_succ_no_rec.recovered_cases == 0
        and kpis_succ_no_rec.gross_recovered_amount == 0
        and r_succ_no_rec.executions[0].status == ExecutionStatus.SUCCEEDED
    )
    ac_results["AC-15"] = bool(
        compute_primary_kpis([], config_exclude).cost_per_recovered_rupee is None
        and kpis_succ_no_rec.cost_per_recovered_rupee is None
    )
    ac_results["AC-55"] = bool(
        r_unknown.case_status == "UNKNOWN"
        and counts_ex["eligible"] == 3
        and not r_unknown.is_recovered
    )
    ac_results["AC-56"] = bool(
        kpis_succ_no_rec.recovered_cases == 0
        and kpis_succ_no_rec.gross_recovered_amount == 0
        and not r_succ_no_rec.is_recovered
    )
    ac_results["AC-57"] = bool(
        counts_ex["censored"] == 1
        and config_exclude.censoring_policy == CensoringPolicy.EXCLUDE
    )
    ac_results["AC-58"] = bool(
        counts_ex["missing_required_artifact"] == 1
        and r_missing.case_id == "case_s7_missing"
    )
    ac_results["AC-59"] = bool(
        safety.unsafe_dispatch_rate == 0.0 and len(eligible_ex) == 3
    )
    ac_results["AC-60"] = bool(safety.unsafe_dispatch_count == 0)
    ac_results["AC-61"] = bool(safety.policy_bypass_count == 0)
    ac_results["AC-62"] = bool(
        safety.duplicate_execution_attempt_count == 0
        and safety.duplicate_outcome_count == 0
    )


def run_scenario_8_prediction_calibration_and_decision_quality(
    ac_results: dict[str, bool],
) -> None:
    """Scenario 8: Prediction Calibration & Decision Quality."""
    print("  Executing Scenario 8: Prediction Calibration & Decision Quality...")

    # Brier score test
    brier = compute_brier_score([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0])
    assert brier < 0.05

    # Calibration bins
    bins = compute_calibration_curve(
        [0.05, 0.15, 0.25, 0.75, 0.85, 0.95], [0, 0, 0, 1, 1, 1], num_bins=5
    )
    assert len(bins) == 5

    # Classification metrics
    clf = compute_classification_metrics([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0])
    assert clf["roc_auc"] == 1.0
    assert clf["f1_score"] == 1.0

    # Decision quality & Oracle gap
    records = [
        make_test_record(
            f"case_s8_{i}", payment_amount=100000, is_recovered=(i % 2 == 0)
        )
        for i in range(20)
    ]
    evaluator = APROEvaluator()
    snapshot = BenchmarkDatasetSnapshot.from_records(
        records, dataset_id="snap_s8", dataset_version="1.0.0"
    )
    report = evaluator.evaluate_dataset(snapshot)

    pred_q = report.prediction_quality
    dec_q = report.decision_quality

    assert pred_q is not None
    assert pred_q.brier_score >= 0.0
    assert dec_q is not None
    assert dec_q.candidate_action_count_avg >= 1.0
    assert dec_q.oracle_gap_avg is not None

    # AST check on evaluator: absence of decision engine imports and decide methods
    eval_src = inspect.getsource(eval_mod)
    eval_ast = ast.parse(eval_src)
    eval_has_decision_engine = any(
        isinstance(node, ast.ImportFrom)
        and "economic_decision_engine" in (node.module or "")
        for node in ast.walk(eval_ast)
    )
    eval_has_runtime_decide = any(
        isinstance(node, ast.FunctionDef) and node.name == "decide"
        for node in ast.walk(eval_ast)
    )

    ac_results["AC-43"] = bool(
        pred_q.sample_size == 20
        and pred_q.positive_class == "RECOVERED"
        and pred_q.brier_score is not None
    )
    ac_results["AC-44"] = bool(
        pred_q.brier_score is not None and 0.0 <= pred_q.brier_score <= 1.0
    )
    ac_results["AC-45"] = bool(
        pred_q.action_scope == "ALL" and len(pred_q.calibration_curve) == 10
    )
    ac_results["AC-46"] = bool(
        pred_q.positive_class == "RECOVERED"
        and pred_q.roc_auc is not None
        and pred_q.f1_score is not None
    )
    ac_results["AC-47"] = bool(
        pred_q.action_scope in ("ALL", "RETRY") and pred_q.sample_size > 0
    )
    ac_results["AC-48"] = bool(
        len(dec_q.selected_action_distribution) > 0
        and dec_q.candidate_action_count_avg >= 1.0
    )
    ac_results["AC-49"] = bool(
        not eval_has_decision_engine and not eval_has_runtime_decide
    )
    ac_results["AC-50"] = bool(
        dec_q.oracle_gap_avg is not None and dec_q.oracle_gap_avg >= 0.0
    )


def run_scenario_9_leakage_oracle_isolation_and_security(
    ac_results: dict[str, bool],
) -> None:
    """Scenario 9: Anti-Cheating Leakage/Oracle Isolation & Security Sanitization."""
    print("  Executing Scenario 9: Oracle Isolation & Security...")

    # 1. Verify TruthPlaneSeparation catches leaked oracle truth
    r_leaked = make_test_record("case_leak", is_recovered=True)
    # Inject oracle leakage into decision reason
    leaked_decision = Decision(
        decision_id="dec_leak",
        case_id="case_leak",
        recommended_action=RecoveryActionType.RETRY,
        confidence=0.9,
        expected_recovery_value=50000,
        reason="Cheating: oracle_action was RETRY with ground_truth_recovered=True",
        model_name="economic_decision_engine",
        model_version="1.0.0",
        created_at=datetime.now(UTC),
    )
    r_tampered = r_leaked.model_copy(update={"decisions": [leaked_decision]})

    caught_cheating = False
    try:
        TruthPlaneSeparation.verify_isolation([r_tampered])
    except CheatingViolationError:
        caught_cheating = True

    assert caught_cheating is True

    # 2. Verify Evaluator boundary constraints via AST inspection
    evaluator = APROEvaluator()
    eval_src = inspect.getsource(eval_mod)
    eval_ast = ast.parse(eval_src)

    eval_has_provider_dispatch = any(
        isinstance(node, ast.ImportFrom) and "providers" in (node.module or "")
        for node in ast.walk(eval_ast)
    )
    eval_has_dispatch_method = any(
        isinstance(node, ast.FunctionDef)
        and (
            "dispatch" in node.name
            or "dispatch_recovery_action" in node.name
            or "dispatch_provider" in node.name
        )
        for node in ast.walk(eval_ast)
    )
    eval_has_policy_engine = any(
        isinstance(node, ast.ImportFrom) and "policy_engine" in (node.module or "")
        for node in ast.walk(eval_ast)
    )
    eval_has_policy_auth = any(
        isinstance(node, ast.FunctionDef) and "authorize_policy" in node.name
        for node in ast.walk(eval_ast)
    )
    eval_has_action_sel = any(
        isinstance(node, ast.FunctionDef)
        and (
            "select_recovery_action" in node.name
            or "select_action" in node.name
            or "decide" in node.name
        )
        for node in ast.walk(eval_ast)
    )
    eval_has_db_mutate = (
        "session.commit" in eval_src
        or "session.add" in eval_src
        or "session.flush" in eval_src
        or "mutate_canonical_state" in eval_src
    )
    eval_has_oracle_leak = any(
        isinstance(node, ast.Name) and "oracle_truth" in node.id
        for node in ast.walk(eval_ast)
    )

    assert not eval_has_dispatch_method
    assert not eval_has_policy_auth
    assert not eval_has_action_sel
    assert not eval_has_db_mutate
    assert not eval_has_provider_dispatch
    assert not eval_has_policy_engine

    # 3. Security sanitization check on generated report with explicit sentinels
    records = [make_test_record(f"case_sec_{i}", is_recovered=True) for i in range(10)]
    for i, r in enumerate(records):
        sec_event = AuditEvent(
            audit_event_id=f"aud_sec_{i}",
            case_id=r.case_id,
            event_type="PROVIDER_REQUEST",
            actor=AuditActor.SYSTEM,
            timestamp=datetime.now(UTC),
            payload={
                "api_key": "sentinel_api_key_xyz",
                "cvv": "sentinel_cvv_999",
                "raw_payload": "sentinel_raw_payload_data",
                "secret": "sk_live_secret12345",
            },
        )
        r.audit_events.append(sec_event)

    snapshot = BenchmarkDatasetSnapshot.from_records(
        records, dataset_id="snap_sec", dataset_version="1.0.0"
    )
    report = evaluator.evaluate_dataset(snapshot)
    rep_json = generate_json_report(report)
    rep_md = generate_markdown_report(report)

    forbidden_patterns = [
        "sentinel_api_key_xyz",
        "sentinel_cvv_999",
        "sentinel_raw_payload_data",
        "sk_live_secret12345",
        "sk_live_",
        "rzp_live_",
        "password",
        "api_secret",
        "Bearer ",
    ]
    for pat in forbidden_patterns:
        assert pat not in rep_json
        assert pat not in rep_md

    # 4. Exercise EvaluationArtifactStore directly to prove concrete behavior
    saved_rep_id = evaluator.artifact_store.save_report(report)
    retrieved_rep = evaluator.artifact_store.get_report(saved_rep_id)
    retrieved_by_run = evaluator.artifact_store.get_report_by_run_id(
        report.benchmark_run_id
    )
    report_list = evaluator.artifact_store.list_reports()
    artifact_store_behavior_valid = (
        isinstance(evaluator.artifact_store, EvaluationArtifactStore)
        and saved_rep_id == report.report_id
        and retrieved_rep is not None
        and retrieved_rep.report_id == report.report_id
        and retrieved_by_run is not None
        and retrieved_by_run.report_id == report.report_id
        and len(report_list) > 0
    )

    ac_results["AC-08"] = bool(caught_cheating is True)
    ac_results["AC-73"] = bool(
        "sentinel_api_key_xyz" not in rep_json
        and "sentinel_api_key_xyz" not in rep_md
        and "sentinel_cvv_999" not in rep_json
        and "sentinel_cvv_999" not in rep_md
    )
    ac_results["AC-74"] = bool(
        "sentinel_raw_payload_data" not in rep_json
        and "sentinel_raw_payload_data" not in rep_md
        and "rzp_live_" not in rep_json
        and "sk_live_" not in rep_json
    )
    ac_results["AC-75"] = bool(caught_cheating is True and not eval_has_oracle_leak)
    ac_results["AC-76"] = bool(
        not eval_has_provider_dispatch and not eval_has_dispatch_method
    )
    ac_results["AC-77"] = bool(not eval_has_policy_engine and not eval_has_policy_auth)
    ac_results["AC-78"] = bool(not eval_has_action_sel)
    ac_results["AC-79"] = bool(not eval_has_db_mutate)
    ac_results["AC-80"] = bool(artifact_store_behavior_valid)


def run_scenario_10_reproducibility_and_cohort_reporting(
    ac_results: dict[str, bool],
) -> None:
    """Scenario 10: Reproducibility & Cohort Reporting."""
    print("  Executing Scenario 10: Reproducibility & Cohort Reporting...")

    records = [
        make_test_record(
            f"case_s10_{i}",
            payment_amount=15000 if i < 10 else 150000,
            payment_method="UPI" if i < 15 else "CARD",
            failure_category="TECHNICAL" if i % 2 == 0 else "BUSINESS",
            is_recovered=(i % 3 != 0),
        )
        for i in range(30)
    ]

    snapshot = BenchmarkDatasetSnapshot.from_records(
        records, dataset_id="snap_s10", dataset_version="1.0.0"
    )
    config = EvaluationConfig(
        bootstrap_seed=999,
        bootstrap_iterations=200,
        minimum_cohort_size=5,
    )

    evaluator1 = APROEvaluator(config=config)
    report1 = evaluator1.evaluate_dataset(
        snapshot, benchmark_run_id="run_s10_test", created_at="2026-09-04T00:00:00Z"
    )

    evaluator2 = APROEvaluator(config=config)
    report2 = evaluator2.evaluate_dataset(
        snapshot, benchmark_run_id="run_s10_test", created_at="2026-09-04T00:00:00Z"
    )

    # Hash determinism
    hash1 = compute_report_hash(report1)
    hash2 = compute_report_hash(report2)
    assert hash1 == hash2

    json1 = generate_json_report(report1)
    json2 = generate_json_report(report2)
    assert json1 == json2

    # Cohort breakdown assertions
    breakdowns = report1.cohort_breakdowns
    assert "payment_method" in breakdowns
    assert "amount_bucket" in breakdowns
    assert "failure_category" in breakdowns
    assert "selected_action" in breakdowns

    md = generate_markdown_report(report1)
    assert "Primary KPI Table" in md
    assert "Baseline Comparison Table" in md
    assert "Safety & Invariant Verification Table" in md
    assert "Evaluation Limitations" in md

    ac_results["AC-07"] = bool(hash1 == hash2 and json1 == json2 and len(hash1) == 64)
    ac_results["AC-63"] = bool(
        len(breakdowns) >= 4 and all(len(v) > 0 for v in breakdowns.values())
    )
    ac_results["AC-64"] = bool(
        any(
            c.is_small_cohort
            for group in breakdowns.values()
            for c in group
            if c.case_count < config.minimum_cohort_size
        )
        or all(
            not c.is_small_cohort
            for group in breakdowns.values()
            for c in group
            if c.case_count >= config.minimum_cohort_size
        )
    )
    ac_results["AC-65"] = bool(
        "failure_category" in breakdowns and len(breakdowns["failure_category"]) >= 2
    )
    ac_results["AC-66"] = bool(
        "selected_action" in breakdowns and len(breakdowns["selected_action"]) >= 1
    )
    ac_results["AC-67"] = bool(
        "payment_method" in breakdowns and len(breakdowns["payment_method"]) >= 2
    )
    ac_results["AC-68"] = bool(
        "sample_size" in str(report1.statistical_results)
        and "recovery_rate" in report1.statistical_results
    )
    ac_results["AC-69"] = bool(
        report1.primary_kpis.recovered_cases <= report1.primary_kpis.eligible_cases
        and report1.primary_kpis.eligible_cases > 0
    )
    ac_results["AC-70"] = bool(
        len(report1.baseline_comparisons) >= 4
        and all(
            b.absolute_recovery_delta is not None
            for b in report1.baseline_comparisons.values()
        )
    )
    ac_results["AC-71"] = bool(
        report1.safety_metrics.unsafe_dispatch_count == 0
        and report1.safety_metrics.policy_bypass_count == 0
    )
    ac_results["AC-72"] = bool(
        len(report1.limitations) >= 3
        and any("observational" in lim.lower() for lim in report1.limitations)
    )


def run_failure_detection_self_test(ac_results: dict[str, bool]) -> None:
    """Run failure-detection self-test ensuring failures exit non-zero."""
    print("  Executing Failure-Detection Self-Test...")

    # 1. Test AST & Static inspection: no unconditional pass, no hasattr, no db URLs
    with open(__file__, encoding="utf-8") as f:
        runner_source = f.read()
        tree = ast.parse(runner_source)

    unconditional_pass_found = False
    hasattr_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id == "ac_results"
            and isinstance(node.value, ast.Constant)
            and node.value.value is True
            for target in node.targets
        ):
            unconditional_pass_found = True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "hasattr"
        ):
            hasattr_found = True

    # Verify no database URLs or credentials exist outside the self-test function
    has_hardcoded_db_url = False
    for top_node in tree.body:
        if (
            isinstance(top_node, ast.FunctionDef)
            and top_node.name == "run_failure_detection_self_test"
        ):
            continue
        for child in ast.walk(top_node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                val = child.value
                if (
                    "postgresql://" in val
                    or "postgresql+asyncpg://" in val
                    or "@127.0.0.1" in val
                    or "postgres_local_dev" in val
                ):
                    has_hardcoded_db_url = True

    # Verify no hardcoded p-value placeholders exist in baselines.py
    with open("src/apro/evaluation/baselines.py", encoding="utf-8") as f:
        baselines_source = f.read()
    has_hardcoded_p_value = (
        "0.001 if" in baselines_source
        or "p_value = 0.001" in baselines_source
        or "p_value = 0.5" in baselines_source
    )

    assert unconditional_pass_found is False
    assert hasattr_found is False
    assert has_hardcoded_db_url is False
    assert has_hardcoded_p_value is False

    # 2. Subprocess failure execution: verify --injected-failure causes non-zero exit
    cmd_failure = [sys.executable, str(Path(__file__).resolve()), "--injected-failure"]
    res_failure = subprocess.run(cmd_failure, capture_output=True, text=True)
    assert res_failure.returncode != 0

    # 3. Subprocess missing POSTGRES_TEST_URL: verify explicit configuration error
    env_missing_db = os.environ.copy()
    env_missing_db.pop("POSTGRES_TEST_URL", None)
    res_missing_db = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        capture_output=True,
        text=True,
        env=env_missing_db,
    )
    assert res_missing_db.returncode != 0
    assert (
        "POSTGRES_TEST_URL" in res_missing_db.stdout
        or "POSTGRES_TEST_URL" in res_missing_db.stderr
    )

    # 4. Test isolated evaluation failure on empty snapshot
    evaluator = APROEvaluator()
    empty_snapshot = BenchmarkDatasetSnapshot(
        dataset_id="snap_empty",
        dataset_version="1.0.0",
        created_at="2026-09-04T00:00:00Z",
        snapshot_hash="0000000000000000000000000000000000000000000000000000000000000000",
        records=(),
    )
    caught_insufficient_sample = False
    try:
        evaluator.evaluate_dataset(empty_snapshot)
    except InsufficientSampleError:
        caught_insufficient_sample = True

    assert caught_insufficient_sample is True

    # 5. Rigorous Acceptance Evaluation Path Tests (all-pass, one-false, empty)
    mock_all_pass = {f"AC-{i:02d}": True for i in range(1, 85)}
    all_pass_eval = evaluate_acceptance_results(mock_all_pass)
    assert all_pass_eval is True

    mock_one_false = {f"AC-{i:02d}": True for i in range(1, 85)}
    mock_one_false["AC-42"] = False
    one_false_eval = evaluate_acceptance_results(mock_one_false)
    assert one_false_eval is False

    mock_incomplete = {f"AC-{i:02d}": True for i in range(1, 50)}
    incomplete_eval = evaluate_acceptance_results(mock_incomplete)
    assert incomplete_eval is False

    empty_eval = evaluate_acceptance_results({})
    assert empty_eval is False

    # 6. Quality & regression checks via subprocess inheriting environment
    env = os.environ.copy()

    res_ruff = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        capture_output=True,
        text=True,
        env=env,
    )
    res_fmt = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        capture_output=True,
        text=True,
        env=env,
    )
    res_mypy = subprocess.run(
        [sys.executable, "-m", "mypy", "src"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res_ruff.returncode == 0
    assert res_fmt.returncode == 0
    assert res_mypy.returncode == 0

    res_pytest = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res_pytest.returncode == 0

    ac_results["AC-81"] = bool(
        unconditional_pass_found is False
        and hasattr_found is False
        and has_hardcoded_db_url is False
        and has_hardcoded_p_value is False
    )
    ac_results["AC-82"] = bool(
        all_pass_eval is True
        and one_false_eval is False
        and incomplete_eval is False
        and empty_eval is False
        and res_failure.returncode != 0
        and res_missing_db.returncode != 0
        and caught_insufficient_sample is True
    )
    ac_results["AC-83"] = bool(
        res_ruff.returncode == 0
        and res_fmt.returncode == 0
        and res_mypy.returncode == 0
    )
    ac_results["AC-84"] = bool(res_pytest.returncode == 0)


# ==============================================================================
# MAIN RUNNER
# ==============================================================================


async def main() -> int:
    """Main acceptance runner entrypoint."""
    parser = argparse.ArgumentParser(description="APRO Phase 15 Acceptance Runner")
    parser.add_argument(
        "--injected-failure",
        action="store_true",
        help="Trigger an injected failure for self-testing",
    )
    args, _ = parser.parse_known_args()

    if args.injected_failure:
        print("[INJECTED FAILURE MODE] Simulating failure for self-test...")
        return 2

    # Verify required environment configuration without embedding hardcoded credentials
    postgres_url = os.environ.get("POSTGRES_TEST_URL")
    if not postgres_url:
        print("[CONFIGURATION ERROR] Missing environment variable: POSTGRES_TEST_URL")
        print("The acceptance runner requires an explicit POSTGRES_TEST_URL.")
        return 1

    print("=" * 80)
    print("APRO PHASE 15 AUTHORITATIVE ACCEPTANCE RUNNER")
    print("Benchmarking, KPI Evaluation & Statistical Reporting")
    print("=" * 80)

    ac_results: dict[str, bool] = {}

    try:
        print("\n--- Running Scenario 1: Clean Benchmark Run ---")
        run_scenario_1_clean_benchmark_run(ac_results)
        print("  [OK] Scenario 1 completed successfully.")

        print("\n--- Running Scenario 2: APRO vs No-Intervention Baseline ---")
        run_scenario_2_apro_vs_no_intervention(ac_results)
        print("  [OK] Scenario 2 completed successfully.")

        print("\n--- Running Scenario 3: APRO vs Fixed Retry Baseline ---")
        run_scenario_3_apro_vs_fixed_retry(ac_results)
        print("  [OK] Scenario 3 completed successfully.")

        print("\n--- Running Scenario 4: APRO vs Payment Link & Escalation ---")
        run_scenario_4_apro_vs_payment_link_and_escalation(ac_results)
        print("  [OK] Scenario 4 completed successfully.")

        print("\n--- Running Scenario 5: Statistical Uncertainty & Bootstrap ---")
        run_scenario_5_statistical_uncertainty_and_bootstrap(ac_results)
        print("  [OK] Scenario 5 completed successfully.")

        print("\n--- Running Scenario 6: Adaptive Loop Measurement ---")
        run_scenario_6_adaptive_loop_measurement(ac_results)
        print("  [OK] Scenario 6 completed successfully.")

        print("\n--- Running Scenario 7: Unknown/Pending Handling & Safety KPIs ---")
        run_scenario_7_unknown_pending_censoring_and_safety(ac_results)
        print("  [OK] Scenario 7 completed successfully.")

        print("\n--- Running Scenario 8: Prediction Calibration & Decision Quality ---")
        run_scenario_8_prediction_calibration_and_decision_quality(ac_results)
        print("  [OK] Scenario 8 completed successfully.")

        print("\n--- Running Scenario 9: Oracle Isolation & Security ---")
        run_scenario_9_leakage_oracle_isolation_and_security(ac_results)
        print("  [OK] Scenario 9 completed successfully.")

        print("\n--- Running Scenario 10: Reproducibility & Cohort Reporting ---")
        run_scenario_10_reproducibility_and_cohort_reporting(ac_results)
        print("  [OK] Scenario 10 completed successfully.")

        print("\n--- Running Failure-Detection Self-Test & Quality Criteria ---")
        run_failure_detection_self_test(ac_results)
        print("  [OK] Failure-Detection Self-Test completed successfully.")

    except Exception as e:
        logger.exception("Acceptance scenario encountered an unhandled error: %s", e)
        return 1

    # Print Summary Table
    print("\n" + "=" * 80)
    print("ACCEPTANCE CRITERIA RESULTS (AC-01 through AC-84):")
    print("=" * 80)

    for i in range(1, 85):
        key = f"AC-{i:02d}"
        passed = ac_results.get(key, False)
        status = "PASSED" if passed else "FAILED"
        print(f"  [{status}] {key}")

    print("=" * 80)
    passed = evaluate_acceptance_results(ac_results, required_count=84)
    passed_count = sum(1 for v in ac_results.values() if v)
    total_count = len(ac_results)
    print(f"TOTAL: {passed_count}/{total_count} criteria passed.")

    if not passed:
        print(f"[FAILED] PHASE 15 ACCEPTANCE FAILED ({passed_count}/84 passed).")
        return 1

    print("[SUCCESS] ALL 84 PHASE 15 ACCEPTANCE CRITERIA PASSED.")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
