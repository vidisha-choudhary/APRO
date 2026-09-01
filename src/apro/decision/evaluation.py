"""Evaluation engine, metrics formulation, and segment analysis for Phase 9."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.dataset.models import GovernedDataset
from apro.decision.baselines import BaseDecisionModel
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.enums import (
    RECOVERY_ACTION_ORDER,
    RecoveryAction,
)
from apro.decision.traces import RecoveryDecisionTrace
from apro.diagnosis.classifiers.interface import BaseDiagnosisModel
from apro.recovery_prediction.classifiers.interface import (
    BaseRecoveryOutcomeModel,
)
from apro.recovery_prediction.models import OutcomePrediction
from apro.simulation.enums import SimulatedActionType, SimulatedOutcomeStatus


class DecisionEvaluationMetrics(BaseModel):
    """Consolidated decision quality and counterfactual metrics."""

    model_config = ConfigDict(frozen=True)

    case_count: int = Field(ge=0)
    decision_accuracy_vs_oracle: float = Field(ge=0.0, le=1.0)
    mean_utility: float
    median_utility: float
    mean_decision_regret: float = Field(ge=0.0)
    median_decision_regret: float = Field(ge=0.0)
    oracle_gap: float = Field(ge=0.0)
    recovery_rate: float = Field(ge=0.0, le=1.0)
    total_recovered_amount: int = Field(ge=0)
    mean_recovered_amount: float = Field(ge=0.0)
    intervention_rate: float = Field(ge=0.0, le=1.0)
    no_intervention_rate: float = Field(ge=0.0, le=1.0)
    unnecessary_intervention_rate: float = Field(ge=0.0, le=1.0)
    ineligible_selection_rate: float = Field(ge=0.0, le=1.0)
    constraint_violation_count: int = Field(default=0, ge=0)
    selected_action_distribution: dict[str, int] = Field(default_factory=dict)
    average_decision_latency_ms: float = Field(default=0.0, ge=0.0)


def calculate_decision_metrics(
    traces: list[RecoveryDecisionTrace],
) -> DecisionEvaluationMetrics:
    """Calculate consolidated decision metrics from structured decision traces."""
    if not traces:
        return DecisionEvaluationMetrics(
            case_count=0,
            decision_accuracy_vs_oracle=0.0,
            mean_utility=0.0,
            median_utility=0.0,
            mean_decision_regret=0.0,
            median_decision_regret=0.0,
            oracle_gap=0.0,
            recovery_rate=0.0,
            total_recovered_amount=0,
            mean_recovered_amount=0.0,
            intervention_rate=0.0,
            no_intervention_rate=0.0,
            unnecessary_intervention_rate=0.0,
            ineligible_selection_rate=0.0,
            constraint_violation_count=0,
            selected_action_distribution={},
        )

    n = len(traces)
    correct_oracle = sum(1 for t in traces if t.is_oracle_match)
    acc = correct_oracle / n

    utilities = [float(t.expected_recovery_value or 0) for t in traces]
    mean_u = sum(utilities) / n
    sorted_u = sorted(utilities)
    med_u = (
        sorted_u[n // 2]
        if n % 2 == 1
        else 0.5 * (sorted_u[n // 2 - 1] + sorted_u[n // 2])
    )

    regrets = [float(t.decision_regret) for t in traces]
    mean_reg = sum(regrets) / n
    sorted_reg = sorted(regrets)
    med_reg = (
        sorted_reg[n // 2]
        if n % 2 == 1
        else 0.5 * (sorted_reg[n // 2 - 1] + sorted_reg[n // 2])
    )

    oracle_gaps = [float(t.oracle_gap) for t in traces]
    mean_gap = sum(oracle_gaps) / n

    realized_vals = [t.realized_value_under_selected for t in traces]
    tot_rec = sum(realized_vals)
    mean_rec = tot_rec / n
    rec_count = sum(1 for v in realized_vals if v > 0)
    rec_rate = rec_count / n

    action_dist: dict[str, int] = {}
    active_interventions = 0
    no_interventions = 0
    unnecessary_count = 0
    ineligible_count = 0
    violation_count = 0

    for t in traces:
        act_key = t.selected_action.value if t.selected_action else "NONE"
        action_dist[act_key] = action_dist.get(act_key, 0) + 1

        if t.selected_action in (
            RecoveryAction.RETRY,
            RecoveryAction.PAYMENT_LINK,
            RecoveryAction.OUTREACH,
            RecoveryAction.ESCALATE,
        ):
            active_interventions += 1
        else:
            no_interventions += 1

        if t.is_unnecessary_intervention:
            unnecessary_count += 1

        # Real computed constraint tracking
        if t.is_ineligible_selection:
            ineligible_count += 1
        if t.is_constraint_violation:
            violation_count += 1

    interv_rate = active_interventions / n
    no_interv_rate = no_interventions / n
    unnecessary_rate = unnecessary_count / n
    ineligible_rate = ineligible_count / n
    avg_lat = sum(t.decision_latency_ms for t in traces) / n

    return DecisionEvaluationMetrics(
        case_count=n,
        decision_accuracy_vs_oracle=round(acc, 4),
        mean_utility=round(mean_u, 2),
        median_utility=round(med_u, 2),
        mean_decision_regret=round(mean_reg, 2),
        median_decision_regret=round(med_reg, 2),
        oracle_gap=round(mean_gap, 2),
        recovery_rate=round(rec_rate, 4),
        total_recovered_amount=tot_rec,
        mean_recovered_amount=round(mean_rec, 2),
        intervention_rate=round(interv_rate, 4),
        no_intervention_rate=round(no_interv_rate, 4),
        unnecessary_intervention_rate=round(unnecessary_rate, 4),
        ineligible_selection_rate=round(ineligible_rate, 4),
        constraint_violation_count=violation_count,
        selected_action_distribution=action_dist,
        average_decision_latency_ms=round(avg_lat, 4),
    )


class EconomicDecisionEvaluator:
    """Evaluates recovery decision strategies against simulation benchmarks."""

    def evaluate(
        self,
        decision_engine: EconomicDecisionEngine | BaseDecisionModel,
        dataset: GovernedDataset,
        diagnosis_model: BaseDiagnosisModel,
        outcome_model: BaseRecoveryOutcomeModel,
    ) -> tuple[DecisionEvaluationMetrics, list[RecoveryDecisionTrace]]:
        """Run complete decision evaluation on a GovernedDataset."""
        traces: list[RecoveryDecisionTrace] = []

        for rec in dataset.records:
            model_in = rec.model_input
            truth = rec.evaluation_truth
            p_amount = model_in.features.payment_amount
            ds_version = dataset.manifest.dataset_version

            # Upstream Model A Diagnosis
            diag_res = diagnosis_model.predict(model_in)

            # Upstream Model B Predictions across all 5 actions
            preds: dict[RecoveryAction, OutcomePrediction] = {}
            for act in RECOVERY_ACTION_ORDER:
                preds[act] = outcome_model.predict(
                    model_in, act, diagnosis_result=diag_res
                )

            # Execute Live Decision Engine
            decision = decision_engine.decide(
                model_input=model_in,
                diagnosis_result=diag_res,
                outcome_predictions=preds,
            )

            # Evaluator-Side Potential Outcome Comparison
            oracle_action = RecoveryAction(truth.best_achievable_action.value)
            oracle_val = truth.best_achievable_value

            if decision.selected_action is not None:
                sim_action = SimulatedActionType(decision.selected_action.value)
                realized_status = truth.potential_outcomes.get(
                    sim_action, SimulatedOutcomeStatus.FAILURE
                )
                realized_val = (
                    p_amount if realized_status == SimulatedOutcomeStatus.SUCCESS else 0
                )
            else:
                realized_val = 0

            regret = max(0, oracle_val - realized_val)

            # Authoritative Oracle Gap Formula (Correction H):
            # max(0, oracle_value - expected_recovery_value_of_selected_action)
            selected_erv = (
                decision.expected_recovery_value
                if decision.expected_recovery_value is not None
                else 0
            )
            oracle_gap = max(0, oracle_val - selected_erv)

            is_match = decision.selected_action == oracle_action
            is_unnecessary = (
                decision.selected_action
                in (
                    RecoveryAction.RETRY,
                    RecoveryAction.PAYMENT_LINK,
                    RecoveryAction.OUTREACH,
                )
                and oracle_action == RecoveryAction.STOP
            )

            # Real constraint evaluation (Correction G)
            is_ineligible = False
            if decision.selected_action is not None:
                act_elig = decision.eligibility_by_action.get(decision.selected_action)
                if act_elig is not None and not act_elig.is_eligible:
                    is_ineligible = True

            is_violation = is_ineligible

            # Value Tier
            tier = (
                "HIGH_VALUE"
                if p_amount >= 1000000
                else "MEDIUM_VALUE"
                if p_amount >= 200000
                else "LOW_VALUE"
            )

            # Diagnosis confidence tier
            diag_conf = diag_res.confidence if diag_res else 0.50
            if diag_conf >= 0.75:
                diag_tier = "HIGH_CONFIDENCE"
            elif diag_conf >= 0.55:
                diag_tier = "MEDIUM_CONFIDENCE"
            else:
                diag_tier = "LOW_CONFIDENCE"

            diag_name = (
                diag_res.predicted_category.value if diag_res else "UNKNOWN_DIAGNOSIS"
            )

            trace = RecoveryDecisionTrace(
                decision_id=decision.decision_id,
                record_id=model_in.record_id,
                scenario_id=model_in.scenario_id,
                recovery_case_id=decision.recovery_case_id,
                selected_action=decision.selected_action,
                decision_status=decision.decision_status,
                utility_by_action=decision.utility_by_action,
                eligibility_by_action=decision.eligibility_by_action,
                expected_recovery_value=decision.expected_recovery_value,
                expected_gross_recovery=decision.expected_gross_recovery,
                expected_cost=decision.expected_cost,
                decision_confidence=decision.decision_confidence,
                rationale=decision.rationale,
                decision_latency_ms=decision.decision_latency_ms,
                diagnosis_model_version=decision.diagnosis_model_version,
                outcome_model_version=decision.outcome_model_version,
                policy_version=decision.policy_version,
                economic_config_version=decision.economic_config_version,
                decision_model_version=decision.decision_model_version,
                action_schema_version=decision.action_schema_version,
                feature_schema_version=decision.feature_schema_version,
                dataset_version=ds_version,
                oracle_best_action=oracle_action,
                oracle_best_value=oracle_val,
                realized_value_under_selected=realized_val,
                decision_regret=regret,
                oracle_gap=oracle_gap,
                is_oracle_match=is_match,
                is_unnecessary_intervention=is_unnecessary,
                is_ineligible_selection=is_ineligible,
                is_constraint_violation=is_violation,
                scenario_family=truth.scenario_family.value,
                payment_method=model_in.features.payment_method.value,
                payment_value_tier=tier,
                scenario_difficulty=truth.scenario_difficulty.value,
                failure_diagnosis=diag_name,
                diagnosis_confidence_tier=diag_tier,
                seed=model_in.generation_seed,
                historical_failure_count=model_in.features.previous_failure_count,
                metadata_completeness=1.0,
            )
            traces.append(trace)

        metrics = calculate_decision_metrics(traces)
        return metrics, traces

    def evaluate_segments(
        self, traces: list[RecoveryDecisionTrace]
    ) -> dict[str, dict[str, Any]]:
        """Compute performance slices across all 8 required segment dimensions."""
        dimensions = [
            "scenario_family",
            "payment_method",
            "payment_value_tier",
            "scenario_difficulty",
            "failure_diagnosis",
            "diagnosis_confidence_tier",
            "selected_action",
            "seed",
        ]
        segment_results: dict[str, dict[str, Any]] = {}

        for dim in dimensions:
            grouped: dict[str, list[RecoveryDecisionTrace]] = {}
            for t in traces:
                if dim == "selected_action":
                    val = t.selected_action.value if t.selected_action else "NONE"
                else:
                    raw_v = getattr(t, dim, "UNKNOWN")
                    val = raw_v.value if hasattr(raw_v, "value") else str(raw_v)
                grouped.setdefault(val, []).append(t)

            dim_metrics: dict[str, Any] = {}
            for group_val, grp_traces in sorted(grouped.items()):
                n_grp = len(grp_traces)
                m_grp = calculate_decision_metrics(grp_traces)
                dim_metrics[group_val] = {
                    "case_count": n_grp,
                    "decision_accuracy_vs_oracle": m_grp.decision_accuracy_vs_oracle,
                    "mean_utility": m_grp.mean_utility,
                    "median_utility": m_grp.median_utility,
                    "mean_decision_regret": m_grp.mean_decision_regret,
                    "median_decision_regret": m_grp.median_decision_regret,
                    "mean_oracle_gap": m_grp.oracle_gap,
                    "recovery_rate": m_grp.recovery_rate,
                    "total_recovered_amount": m_grp.total_recovered_amount,
                    "intervention_rate": m_grp.intervention_rate,
                    "unnecessary_intervention_rate": (
                        m_grp.unnecessary_intervention_rate
                    ),
                    "constraint_violation_count": m_grp.constraint_violation_count,
                }
            segment_results[dim] = dim_metrics

        return segment_results

    def compare_distribution_shift(
        self,
        in_distribution: DecisionEvaluationMetrics,
        shifted_distribution: DecisionEvaluationMetrics,
    ) -> dict[str, Any]:
        """Compare in-distribution decision metrics against shifted benchmark."""
        u_d = shifted_distribution.mean_utility - in_distribution.mean_utility
        reg_d = (
            shifted_distribution.mean_decision_regret
            - in_distribution.mean_decision_regret
        )
        gap_d = shifted_distribution.oracle_gap - in_distribution.oracle_gap
        return {
            "in_distribution": in_distribution.model_dump(),
            "shifted_distribution": shifted_distribution.model_dump(),
            "deltas": {
                "decision_accuracy_delta": round(
                    shifted_distribution.decision_accuracy_vs_oracle
                    - in_distribution.decision_accuracy_vs_oracle,
                    4,
                ),
                "mean_utility_delta": round(u_d, 2),
                "mean_regret_delta": round(reg_d, 2),
                "oracle_gap_delta": round(gap_d, 2),
                "recovery_rate_delta": round(
                    shifted_distribution.recovery_rate - in_distribution.recovery_rate,
                    4,
                ),
                "intervention_rate_delta": round(
                    shifted_distribution.intervention_rate
                    - in_distribution.intervention_rate,
                    4,
                ),
            },
        }

    def perform_error_analysis(
        self, traces: list[RecoveryDecisionTrace]
    ) -> dict[str, Any]:
        """Perform comprehensive error analysis across all 7 error categories."""
        tot = len(traces)
        wrong_decisions = [t for t in traces if not t.is_oracle_match]
        high_conf_wrongs = [
            t for t in traces if not t.is_oracle_match and t.decision_confidence >= 0.75
        ]
        negative_utility_cases = [
            t
            for t in traces
            if t.expected_recovery_value is not None and t.expected_recovery_value < 0
        ]
        large_regret_cases = [t for t in traces if t.decision_regret >= 50000]
        unnecessary_interventions = [t for t in traces if t.is_unnecessary_intervention]

        # Near-tie decisions (margin <= 500 paise / Rs 5.00)
        near_ties = []
        for t in traces:
            if t.utility_by_action and t.expected_recovery_value is not None:
                close_cnt = sum(
                    1
                    for u in t.utility_by_action.values()
                    if u.eligible
                    and abs(u.expected_recovery_value - t.expected_recovery_value)
                    <= 500
                )
                if close_cnt > 1:
                    near_ties.append(t)

        # Policy-filtered best prediction actions
        policy_filtered_best = []
        for t in traces:
            if t.utility_by_action:
                best_prob_u = max(
                    t.utility_by_action.values(),
                    key=lambda u: u.predicted_success_probability,
                )
                if not best_prob_u.eligible:
                    policy_filtered_best.append(t)

        action_error_breakdown: dict[str, int] = {}
        for t in wrong_decisions:
            act_str = t.selected_action.value if t.selected_action else "NONE"
            action_error_breakdown[act_str] = action_error_breakdown.get(act_str, 0) + 1

        dis_rate = len(wrong_decisions) / max(1, tot)
        high_conf_rate = len(high_conf_wrongs) / max(1, tot)

        return {
            "total_cases": tot,
            "total_oracle_disagreements": len(wrong_decisions),
            "oracle_disagreement_rate": round(dis_rate, 4),
            "high_confidence_wrong_count": len(high_conf_wrongs),
            "high_confidence_wrong_rate": round(high_conf_rate, 4),
            "negative_utility_count": len(negative_utility_cases),
            "near_tie_decision_count": len(near_ties),
            "policy_filtered_best_prediction_count": len(policy_filtered_best),
            "large_regret_count": len(large_regret_cases),
            "unnecessary_intervention_count": len(unnecessary_interventions),
            "ineligible_selection_count": sum(
                1 for t in traces if t.is_ineligible_selection
            ),
            "constraint_violation_count": sum(
                1 for t in traces if t.is_constraint_violation
            ),
            "action_error_breakdown": action_error_breakdown,
        }
