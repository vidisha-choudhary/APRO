"""Evaluation engine, segment analysis, and error diagnosis for Model B."""

import time
from typing import Any

from apro.dataset.models import GovernedDataset
from apro.diagnosis.classifiers.interface import BaseDiagnosisModel
from apro.recovery_prediction.classifiers.interface import (
    BaseRecoveryOutcomeModel,
)
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_ORDER,
    PredictionUncertaintyState,
)
from apro.recovery_prediction.features import RecoveryFeatureVector
from apro.recovery_prediction.labels import construct_outcome_label
from apro.recovery_prediction.metrics import (
    RecoveryOutcomeMetrics,
    calculate_recovery_outcome_metrics,
)
from apro.recovery_prediction.traces import RecoveryPredictionTrace


def select_best_candidate(
    candidates_metrics: dict[str, RecoveryOutcomeMetrics],
    primary_metric: str = "macro_f1",
    tie_breaker_metric: str = "log_loss",
) -> tuple[str, str]:
    """Select best candidate model using primary metric and tie-breaker."""
    if not candidates_metrics:
        msg = "Cannot select from empty candidate metrics dictionary."
        raise ValueError(msg)

    def sort_key(
        item: tuple[str, RecoveryOutcomeMetrics],
    ) -> tuple[float, float, str]:
        name, m = item
        primary_val = getattr(m, primary_metric, 0.0)
        tie_val = getattr(m, tie_breaker_metric, 0.0)

        lower_better = (
            "log_loss",
            "brier_score",
            "expected_calibration_error",
            "mae",
            "rmse",
        )
        p_score = -primary_val if primary_metric in lower_better else primary_val
        t_score = -tie_val if tie_breaker_metric in lower_better else tie_val

        return (p_score, t_score, name)

    sorted_candidates = sorted(candidates_metrics.items(), key=sort_key, reverse=True)
    best_name, best_m = sorted_candidates[0]

    primary_val = getattr(best_m, primary_metric, 0.0)
    tie_val = getattr(best_m, tie_breaker_metric, 0.0)
    rationale = (
        f"Selected '{best_name}' via primary_metric='{primary_metric}' "
        f"({primary_val:.4f}) with tie_breaker='{tie_breaker_metric}' "
        f"({tie_val:.4f})."
    )
    return best_name, rationale


class RecoveryOutcomeEvaluator:
    """Evaluates Model B against governed datasets with counterfactual analysis."""

    def evaluate_model(
        self,
        model: BaseRecoveryOutcomeModel,
        dataset: GovernedDataset,
        diagnosis_model: BaseDiagnosisModel | None = None,
        feature_vectors: list[RecoveryFeatureVector] | None = None,
    ) -> tuple[RecoveryOutcomeMetrics, list[RecoveryPredictionTrace]]:
        """Evaluate Model B across all records and recovery actions."""
        traces: list[RecoveryPredictionTrace] = []
        diag_map = {}

        if diagnosis_model is not None:
            for rec in dataset.records:
                diag_map[rec.model_input.record_id] = diagnosis_model.predict(
                    rec.model_input
                )

        fb = model.feature_builder
        best_vals = {
            r.evaluation_truth.scenario_id: (r.evaluation_truth.best_achievable_value)
            for r in dataset.records
        }

        # Cache precomputed vectors if available
        feat_dict = {}
        if feature_vectors:
            for f in feature_vectors:
                feat_dict[(f.record_id, f.action)] = f

        for rec in dataset.records:
            model_in = rec.model_input
            truth = rec.evaluation_truth
            diag_res = diag_map.get(model_in.record_id)
            p_amount = model_in.features.payment_amount
            ds_version = dataset.manifest.dataset_version

            tier = (
                "HIGH_VALUE"
                if p_amount >= 1000000
                else "MEDIUM_VALUE"
                if p_amount >= 200000
                else "LOW_VALUE"
            )

            for act in RECOVERY_ACTION_ORDER:
                feat = feat_dict.get((model_in.record_id, act)) or fb.transform(
                    model_in, act, diagnosis_result=diag_res
                )

                t0 = time.perf_counter()
                pred = model.predict(
                    model_in,
                    act,
                    diagnosis_result=diag_res,
                    feature_vector=feat,
                )
                t_latency = (time.perf_counter() - t0) * 1000.0

                label = construct_outcome_label(
                    truth_record=truth,
                    action=act,
                    payment_amount=p_amount,
                    dataset_version=ds_version,
                )

                is_correct = pred.predicted_outcome_state == label.outcome_state
                amt_err = pred.predicted_recovered_amount - label.recovered_amount

                trace = RecoveryPredictionTrace(
                    prediction_id=pred.prediction_id,
                    record_id=model_in.record_id,
                    scenario_id=model_in.scenario_id,
                    action=act,
                    dataset_version=ds_version,
                    feature_schema_version=pred.feature_schema_version,
                    action_schema_version=pred.action_schema_version,
                    diagnosis_model_version=pred.diagnosis_model_version,
                    model_version=pred.model_version,
                    predicted_success_probability=pred.predicted_success_probability,
                    predicted_outcome_state=pred.predicted_outcome_state,
                    predicted_recovered_amount=pred.predicted_recovered_amount,
                    confidence=pred.confidence,
                    uncertainty_state=pred.uncertainty_state,
                    actual_outcome_state=label.outcome_state,
                    actual_recovered_amount=label.recovered_amount,
                    is_correct_outcome=is_correct,
                    amount_error=amt_err,
                    scenario_family=truth.scenario_family.value,
                    payment_method=model_in.features.payment_method.value,
                    payment_value_tier=tier,
                    scenario_difficulty=truth.scenario_difficulty.value,
                    decision_latency_ms=round(t_latency, 4),
                )
                traces.append(trace)

        metrics = calculate_recovery_outcome_metrics(
            traces, best_achievable_values=best_vals
        )
        avg_lat = sum(t.decision_latency_ms for t in traces) / max(1, len(traces))
        metrics = metrics.model_copy(
            update={"average_decision_latency_ms": round(avg_lat, 4)}
        )
        return metrics, traces

    def evaluate_segments(
        self, traces: list[RecoveryPredictionTrace]
    ) -> dict[str, dict[str, Any]]:
        """Compute performance breakdown across segment dimensions."""
        dimensions = [
            "action",
            "scenario_family",
            "payment_method",
            "payment_value_tier",
            "scenario_difficulty",
        ]
        segment_results: dict[str, dict[str, Any]] = {}

        for dim in dimensions:
            grouped: dict[str, list[RecoveryPredictionTrace]] = {}
            for t in traces:
                val = str(getattr(t, dim, "UNKNOWN"))
                grouped.setdefault(val, []).append(t)

            dim_metrics: dict[str, Any] = {}
            for group_val, grp_traces in grouped.items():
                n = len(grp_traces)
                correct = sum(1 for t in grp_traces if t.is_correct_outcome)
                mae = sum(abs(t.amount_error) for t in grp_traces) / max(1, n)
                dim_metrics[group_val] = {
                    "case_count": n,
                    "accuracy": round(correct / max(1, n), 4),
                    "mae": round(mae, 2),
                }
            segment_results[dim] = dim_metrics

        return segment_results

    def compare_distribution_shift(
        self,
        in_distribution: RecoveryOutcomeMetrics,
        shifted_distribution: RecoveryOutcomeMetrics,
    ) -> dict[str, Any]:
        """Compare in-distribution against shifted benchmark distribution."""
        po_in = in_distribution.potential_outcome_metrics
        po_shift = shifted_distribution.potential_outcome_metrics
        return {
            "in_distribution": in_distribution.model_dump(),
            "shifted_distribution": shifted_distribution.model_dump(),
            "deltas": {
                "macro_f1_delta": round(
                    shifted_distribution.macro_f1 - in_distribution.macro_f1, 4
                ),
                "accuracy_delta": round(
                    shifted_distribution.accuracy - in_distribution.accuracy, 4
                ),
                "log_loss_delta": round(
                    shifted_distribution.log_loss - in_distribution.log_loss, 4
                ),
                "mae_delta": round(shifted_distribution.mae - in_distribution.mae, 2),
                "oracle_gap_delta": round(
                    po_shift.oracle_gap - po_in.oracle_gap,
                    2,
                ),
            },
        }

    def perform_error_analysis(
        self, traces: list[RecoveryPredictionTrace]
    ) -> dict[str, Any]:
        """Aggregate systematic prediction mistakes and high-confidence errors."""
        tot = len(traces)
        errors = [t for t in traces if not t.is_correct_outcome]
        high_conf_errors = [
            t
            for t in errors
            if t.uncertainty_state == PredictionUncertaintyState.HIGH_CONFIDENCE
        ]

        action_error_breakdown: dict[str, int] = {}
        for t in errors:
            act_str = t.action.value
            action_error_breakdown[act_str] = action_error_breakdown.get(act_str, 0) + 1

        large_amount_errors = [t for t in traces if abs(t.amount_error) >= 100000]

        return {
            "total_cases": tot,
            "total_errors": len(errors),
            "error_rate": round(len(errors) / max(1, tot), 4),
            "high_confidence_wrong_count": len(high_conf_errors),
            "high_confidence_error_rate": round(len(high_conf_errors) / max(1, tot), 4),
            "large_amount_error_count": len(large_amount_errors),
            "action_error_breakdown": action_error_breakdown,
        }
