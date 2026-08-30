"""Evaluation harness, segment analysis, and error analysis for Model A."""

from typing import Any

from apro.dataset.models import GovernedDataset
from apro.diagnosis.classifiers.interface import BaseDiagnosisModel
from apro.diagnosis.features import (
    DiagnosisFeatureVector,
)
from apro.diagnosis.labels import construct_diagnosis_label
from apro.diagnosis.metrics import DiagnosisMetrics, calculate_diagnosis_metrics
from apro.diagnosis.traces import DiagnosisPredictionTrace
from apro.simulation.config import SimulationConfig
from apro.simulation.enums import PaymentValueTier


def _get_val_tier(amount: int, config: SimulationConfig) -> PaymentValueTier:
    for tier, (min_amt, max_amt) in config.amount_ranges.items():
        if min_amt <= amount <= max_amt:
            return tier
    if amount < config.amount_ranges[PaymentValueTier.LOW_VALUE][0]:
        return PaymentValueTier.LOW_VALUE
    return PaymentValueTier.HIGH_VALUE


class DiagnosisEvaluator:
    """Evaluates Model A predictions, computes segment breakdowns and error analysis."""

    def __init__(self, simulation_config: SimulationConfig | None = None) -> None:
        self._sim_config = simulation_config or SimulationConfig()

    def evaluate_model(
        self,
        model: BaseDiagnosisModel,
        dataset: GovernedDataset,
        feature_vectors: list[DiagnosisFeatureVector] | None = None,
    ) -> tuple[DiagnosisMetrics, list[DiagnosisPredictionTrace]]:
        """Run model across records to produce metrics and prediction traces."""
        traces: list[DiagnosisPredictionTrace] = []
        builder = model.feature_builder

        for i, rec in enumerate(dataset.records):
            model_input = rec.model_input
            eval_truth = rec.evaluation_truth
            snap = model_input.features

            feat = (
                feature_vectors[i]
                if feature_vectors and i < len(feature_vectors)
                else builder.transform(model_input)
            )

            # Generate prediction
            res = model.predict(model_input, feature_vector=feat)

            # Evaluator-side ground truth label
            lbl = construct_diagnosis_label(eval_truth)
            actual_cat = lbl.failure_category
            is_corr = res.predicted_category == actual_cat

            val_tier = _get_val_tier(snap.payment_amount, self._sim_config)

            trace = DiagnosisPredictionTrace(
                prediction_id=res.prediction_id,
                record_id=model_input.record_id,
                scenario_id=model_input.scenario_id,
                dataset_version=model_input.dataset_version,
                feature_schema_version=model.feature_schema_version,
                taxonomy_version=model.taxonomy_version,
                model_name=model.model_name,
                model_version=model.model_version,
                predicted_category=res.predicted_category,
                class_probabilities=res.class_probabilities,
                confidence=res.confidence,
                uncertainty_state=res.uncertainty_state,
                actual_category=actual_cat,
                is_correct=is_corr,
                decision_latency_ms=res.decision_latency_ms,
                scenario_family=eval_truth.scenario_family,
                payment_value_tier=val_tier,
                payment_method=snap.payment_method,
                scenario_difficulty=eval_truth.scenario_difficulty,
                seed=model_input.generation_seed,
            )
            traces.append(trace)

        metrics = calculate_diagnosis_metrics(traces)
        return metrics, traces

    def evaluate_segments(
        self, traces: list[DiagnosisPredictionTrace]
    ) -> dict[str, dict[str, DiagnosisMetrics]]:
        """Compute diagnosis metrics sliced by scenario and failure dimensions."""
        dimensions = [
            "scenario_family",
            "payment_value_tier",
            "payment_method",
            "scenario_difficulty",
            "seed",
        ]
        results: dict[str, dict[str, DiagnosisMetrics]] = {}

        for dim in dimensions:
            seg_groups: dict[str, list[DiagnosisPredictionTrace]] = {}
            for t in traces:
                val = getattr(t, dim)
                val_str = val.value if hasattr(val, "value") else str(val)
                seg_groups.setdefault(val_str, []).append(t)

            dim_metrics: dict[str, DiagnosisMetrics] = {}
            for k, group_traces in seg_groups.items():
                dim_metrics[k] = calculate_diagnosis_metrics(group_traces)
            results[dim] = dim_metrics

        return results

    def perform_error_analysis(
        self, traces: list[DiagnosisPredictionTrace]
    ) -> dict[str, Any]:
        """Perform structured evaluator-side error analysis."""
        misclassified = [t for t in traces if t.is_correct is False]
        high_conf_wrong = [t for t in misclassified if t.confidence >= 0.70]
        low_conf = [t for t in traces if t.confidence < 0.45]

        # Count systematic confusion pairs (Actual -> Predicted)
        confusion_pairs: dict[str, int] = {}
        for t in misclassified:
            if t.actual_category:
                key = f"{t.actual_category.value} -> {t.predicted_category.value}"
                confusion_pairs[key] = confusion_pairs.get(key, 0) + 1

        sorted_confusions = sorted(
            confusion_pairs.items(), key=lambda item: item[1], reverse=True
        )

        return {
            "total_cases": len(traces),
            "misclassified_count": len(misclassified),
            "error_rate": (round(len(misclassified) / max(1, len(traces)), 4)),
            "high_confidence_wrong_count": len(high_conf_wrong),
            "low_confidence_count": len(low_conf),
            "top_confusion_pairs": [
                {"pair": p, "count": c} for p, c in sorted_confusions[:5]
            ],
        }

    def compare_distribution_shift(
        self,
        in_dist_metrics: DiagnosisMetrics,
        shifted_metrics: DiagnosisMetrics,
    ) -> dict[str, Any]:
        """Quantify performance shifts between in-dist and shifted benchmarks."""
        f1_delta = round(shifted_metrics.macro_f1 - in_dist_metrics.macro_f1, 4)
        acc_delta = round(shifted_metrics.accuracy - in_dist_metrics.accuracy, 4)
        loss_delta = round(shifted_metrics.log_loss - in_dist_metrics.log_loss, 4)
        ece_delta = round(
            shifted_metrics.expected_calibration_error
            - in_dist_metrics.expected_calibration_error,
            4,
        )

        return {
            "in_distribution": {
                "accuracy": in_dist_metrics.accuracy,
                "macro_f1": in_dist_metrics.macro_f1,
                "log_loss": in_dist_metrics.log_loss,
                "ece": in_dist_metrics.expected_calibration_error,
            },
            "shifted_distribution": {
                "accuracy": shifted_metrics.accuracy,
                "macro_f1": shifted_metrics.macro_f1,
                "log_loss": shifted_metrics.log_loss,
                "ece": shifted_metrics.expected_calibration_error,
            },
            "deltas": {
                "macro_f1_delta": f1_delta,
                "accuracy_delta": acc_delta,
                "log_loss_delta": loss_delta,
                "ece_delta": ece_delta,
            },
        }


def select_best_candidate(
    candidates_metrics: dict[str, DiagnosisMetrics],
    primary_metric: str = "macro_f1",
    tie_breaker_metric: str = "log_loss",
) -> tuple[str, str]:
    """Select best candidate using primary metric and tie-breaker."""
    if not candidates_metrics:
        msg = "Cannot select from empty candidate metrics dictionary."
        raise ValueError(msg)

    higher_is_better = {
        "macro_f1",
        "accuracy",
        "balanced_accuracy",
        "weighted_f1",
        "top_2_accuracy",
    }

    def sort_key(
        item: tuple[str, DiagnosisMetrics],
    ) -> tuple[float, float, str]:
        name, m = item
        p_val = getattr(m, primary_metric, 0.0)
        p_score = p_val if primary_metric in higher_is_better else -p_val

        t_val = getattr(m, tie_breaker_metric, 0.0)
        t_score = t_val if tie_breaker_metric in higher_is_better else -t_val

        return (p_score, t_score, name)

    sorted_candidates = sorted(candidates_metrics.items(), key=sort_key, reverse=True)
    best_name, best_m = sorted_candidates[0]

    p_val = getattr(best_m, primary_metric, 0.0)
    t_val = getattr(best_m, tie_breaker_metric, 0.0)
    rationale = (
        f"Selected '{best_name}' via primary_metric='{primary_metric}' "
        f"({p_val:.4f}) with tie_breaker='{tie_breaker_metric}' ({t_val:.4f})."
    )
    return best_name, rationale
