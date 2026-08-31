"""Metric calculation, classification formulas, and error evaluation for Model B."""

import math

from pydantic import BaseModel, ConfigDict, Field

from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_ORDER,
    PredictedOutcomeState,
    RecoveryAction,
)
from apro.recovery_prediction.traces import RecoveryPredictionTrace


class PerActionClassificationMetric(BaseModel):
    """Classification performance metrics for a specific recovery action."""

    model_config = ConfigDict(frozen=True)

    action: RecoveryAction
    case_count: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    balanced_accuracy: float = Field(ge=0.0, le=1.0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    log_loss: float = Field(ge=0.0)
    brier_score: float = Field(ge=0.0)
    expected_calibration_error: float = Field(ge=0.0, le=1.0)
    confusion_matrix: list[list[int]]


class PerActionAmountMetric(BaseModel):
    """Recovery amount regression error metrics for a specific recovery action."""

    model_config = ConfigDict(frozen=True)

    action: RecoveryAction
    case_count: int = Field(ge=0)
    mae: float = Field(ge=0.0)
    rmse: float = Field(ge=0.0)
    median_absolute_error: float = Field(ge=0.0)
    normalized_mae: float = Field(ge=0.0)


class PotentialOutcomeMetrics(BaseModel):
    """Evaluator-side potential outcome and counterfactual metrics."""

    model_config = ConfigDict(frozen=True)

    oracle_gap: float = Field(ge=0.0)
    counterfactual_regret: float = Field(ge=0.0)
    mean_best_achievable_value: float = Field(ge=0.0)
    mean_predicted_best_value: float = Field(ge=0.0)


class RecoveryOutcomeMetrics(BaseModel):
    """Consolidated classification and regression metrics for Model B."""

    model_config = ConfigDict(frozen=True)

    case_count: int = Field(ge=0)
    scenario_count: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    balanced_accuracy: float = Field(ge=0.0, le=1.0)
    macro_precision: float = Field(ge=0.0, le=1.0)
    macro_recall: float = Field(ge=0.0, le=1.0)
    macro_f1: float = Field(ge=0.0, le=1.0)
    log_loss: float = Field(ge=0.0)
    brier_score: float = Field(ge=0.0)
    expected_calibration_error: float = Field(ge=0.0, le=1.0)
    mae: float = Field(ge=0.0)
    rmse: float = Field(ge=0.0)
    median_absolute_error: float = Field(ge=0.0)
    per_action_classification: dict[RecoveryAction, PerActionClassificationMetric]
    per_action_amount: dict[RecoveryAction, PerActionAmountMetric]
    potential_outcome_metrics: PotentialOutcomeMetrics
    average_decision_latency_ms: float = Field(default=0.0, ge=0.0)


def _binary_ece(probs: list[float], labels: list[int], num_bins: int = 10) -> float:
    if not probs:
        return 0.0

    n = len(probs)
    bins: list[list[int]] = [[] for _ in range(num_bins)]

    for idx, p in enumerate(probs):
        bin_idx = min(num_bins - 1, int(p * num_bins))
        bins[bin_idx].append(idx)

    ece = 0.0
    for b in bins:
        if not b:
            continue
        bin_size = len(b)
        bin_avg_p = sum(probs[i] for i in b) / bin_size
        bin_acc = sum(labels[i] for i in b) / bin_size
        ece += (bin_size / n) * abs(bin_avg_p - bin_acc)

    return ece


def calculate_recovery_outcome_metrics(
    traces: list[RecoveryPredictionTrace],
    best_achievable_values: dict[str, int] | None = None,
) -> RecoveryOutcomeMetrics:
    """Calculate consolidated classification, regression, and counterfactual metrics."""
    if not traces:
        empty_class = {
            act: PerActionClassificationMetric(
                action=act,
                case_count=0,
                accuracy=0.0,
                balanced_accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1=0.0,
                log_loss=0.0,
                brier_score=0.0,
                expected_calibration_error=0.0,
                confusion_matrix=[[0, 0], [0, 0]],
            )
            for act in RECOVERY_ACTION_ORDER
        }
        empty_amount = {
            act: PerActionAmountMetric(
                action=act,
                case_count=0,
                mae=0.0,
                rmse=0.0,
                median_absolute_error=0.0,
                normalized_mae=0.0,
            )
            for act in RECOVERY_ACTION_ORDER
        }
        return RecoveryOutcomeMetrics(
            case_count=0,
            scenario_count=0,
            accuracy=0.0,
            balanced_accuracy=0.0,
            macro_precision=0.0,
            macro_recall=0.0,
            macro_f1=0.0,
            log_loss=0.0,
            brier_score=0.0,
            expected_calibration_error=0.0,
            mae=0.0,
            rmse=0.0,
            median_absolute_error=0.0,
            per_action_classification=empty_class,
            per_action_amount=empty_amount,
            potential_outcome_metrics=PotentialOutcomeMetrics(
                oracle_gap=0.0,
                counterfactual_regret=0.0,
                mean_best_achievable_value=0.0,
                mean_predicted_best_value=0.0,
            ),
        )

    # Group by action
    traces_by_act: dict[RecoveryAction, list[RecoveryPredictionTrace]] = {
        act: [] for act in RECOVERY_ACTION_ORDER
    }
    for tr in traces:
        traces_by_act[tr.action].append(tr)

    per_act_class: dict[RecoveryAction, PerActionClassificationMetric] = {}
    per_act_amt: dict[RecoveryAction, PerActionAmountMetric] = {}

    all_y_true: list[int] = []
    all_y_pred: list[int] = []
    all_probs: list[float] = []
    all_errors: list[float] = []

    for act in RECOVERY_ACTION_ORDER:
        act_traces = traces_by_act[act]
        n_act = len(act_traces)
        if n_act == 0:
            per_act_class[act] = PerActionClassificationMetric(
                action=act,
                case_count=0,
                accuracy=0.0,
                balanced_accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1=0.0,
                log_loss=0.0,
                brier_score=0.0,
                expected_calibration_error=0.0,
                confusion_matrix=[[0, 0], [0, 0]],
            )
            per_act_amt[act] = PerActionAmountMetric(
                action=act,
                case_count=0,
                mae=0.0,
                rmse=0.0,
                median_absolute_error=0.0,
                normalized_mae=0.0,
            )
            continue

        y_true = [
            1 if t.actual_outcome_state == PredictedOutcomeState.SUCCESS else 0
            for t in act_traces
        ]
        y_pred = [
            1 if t.predicted_outcome_state == PredictedOutcomeState.SUCCESS else 0
            for t in act_traces
        ]
        probs = [t.predicted_success_probability for t in act_traces]
        abs_errs = [float(abs(t.amount_error)) for t in act_traces]

        all_y_true.extend(y_true)
        all_y_pred.extend(y_pred)
        all_probs.extend(probs)
        all_errors.extend(abs_errs)

        # Confusion Matrix: [[TN, FP], [FN, TP]]
        tn = sum(
            1 for yt, yp in zip(y_true, y_pred, strict=True) if yt == 0 and yp == 0
        )
        fp = sum(
            1 for yt, yp in zip(y_true, y_pred, strict=True) if yt == 0 and yp == 1
        )
        fn = sum(
            1 for yt, yp in zip(y_true, y_pred, strict=True) if yt == 1 and yp == 0
        )
        tp = sum(
            1 for yt, yp in zip(y_true, y_pred, strict=True) if yt == 1 and yp == 1
        )

        acc = (tp + tn) / n_act
        sens = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 1.0
        b_acc = 0.5 * (sens + spec)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = 2.0 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        eps = 1e-15
        log_loss = (
            sum(
                -(
                    yt * math.log(max(eps, min(1.0 - eps, p)))
                    + (1 - yt) * math.log(max(eps, min(1.0 - eps, 1.0 - p)))
                )
                for yt, p in zip(y_true, probs, strict=True)
            )
            / n_act
        )

        brier = sum((p - yt) ** 2 for yt, p in zip(y_true, probs, strict=True)) / n_act
        ece = _binary_ece(probs, y_true)

        per_act_class[act] = PerActionClassificationMetric(
            action=act,
            case_count=n_act,
            accuracy=round(acc, 4),
            balanced_accuracy=round(b_acc, 4),
            precision=round(prec, 4),
            recall=round(rec, 4),
            f1=round(f1, 4),
            log_loss=round(log_loss, 4),
            brier_score=round(brier, 4),
            expected_calibration_error=round(ece, 4),
            confusion_matrix=[[tn, fp], [fn, tp]],
        )

        mae = sum(abs_errs) / n_act
        mse = sum(e**2 for e in abs_errs) / n_act
        rmse = math.sqrt(mse)
        sorted_errs = sorted(abs_errs)
        medae = (
            sorted_errs[n_act // 2]
            if n_act % 2 == 1
            else 0.5 * (sorted_errs[n_act // 2 - 1] + sorted_errs[n_act // 2])
        )
        mean_act_val = sum(t.actual_recovered_amount for t in act_traces) / n_act
        norm_mae = mae / max(1.0, mean_act_val)

        per_act_amt[act] = PerActionAmountMetric(
            action=act,
            case_count=n_act,
            mae=round(mae, 2),
            rmse=round(rmse, 2),
            median_absolute_error=round(medae, 2),
            normalized_mae=round(norm_mae, 4),
        )

    # Macro Averages across all actions
    active_actions = [a for a in RECOVERY_ACTION_ORDER if traces_by_act[a]]
    macro_f1 = sum(per_act_class[a].f1 for a in active_actions) / len(active_actions)
    macro_prec = sum(per_act_class[a].precision for a in active_actions) / len(
        active_actions
    )
    macro_rec = sum(per_act_class[a].recall for a in active_actions) / len(
        active_actions
    )
    macro_b_acc = sum(per_act_class[a].balanced_accuracy for a in active_actions) / len(
        active_actions
    )

    tot_n = len(traces)
    tot_correct = sum(1 for t in traces if t.is_correct_outcome)
    overall_acc = tot_correct / tot_n

    overall_mae = sum(all_errors) / tot_n
    overall_rmse = math.sqrt(sum(e**2 for e in all_errors) / tot_n)
    sorted_all_errs = sorted(all_errors)
    overall_medae = sorted_all_errs[tot_n // 2]

    overall_log_loss = sum(per_act_class[a].log_loss for a in active_actions) / len(
        active_actions
    )
    overall_brier = sum(per_act_class[a].brier_score for a in active_actions) / len(
        active_actions
    )
    overall_ece = _binary_ece(all_probs, all_y_true)

    # Potential outcome analysis
    best_vals = best_achievable_values or {}
    scenarios = sorted({t.scenario_id for t in traces})
    scen_count = len(scenarios)

    gaps: list[float] = []
    regrets: list[float] = []
    best_vals_list: list[float] = []
    pred_best_list: list[float] = []

    for sc_id in scenarios:
        sc_traces = [t for t in traces if t.scenario_id == sc_id]
        if not sc_traces:
            continue
        best_achievable = float(
            best_vals.get(sc_id, max(t.actual_recovered_amount for t in sc_traces))
        )
        best_vals_list.append(best_achievable)

        # Predicted best action value
        pred_best_amt = max(t.predicted_recovered_amount for t in sc_traces)
        pred_best_list.append(float(pred_best_amt))

        # Realized value under predicted best action
        best_pred_trace = max(sc_traces, key=lambda t: t.predicted_success_probability)
        realized_val = float(best_pred_trace.actual_recovered_amount)

        regret = max(0.0, best_achievable - realized_val)
        gap = abs(best_achievable - pred_best_amt)
        regrets.append(regret)
        gaps.append(gap)

    mean_gap = sum(gaps) / max(1, len(gaps))
    mean_regret = sum(regrets) / max(1, len(regrets))
    mean_best = sum(best_vals_list) / max(1, len(best_vals_list))
    mean_pred_best = sum(pred_best_list) / max(1, len(pred_best_list))

    return RecoveryOutcomeMetrics(
        case_count=tot_n,
        scenario_count=scen_count,
        accuracy=round(overall_acc, 4),
        balanced_accuracy=round(macro_b_acc, 4),
        macro_precision=round(macro_prec, 4),
        macro_recall=round(macro_rec, 4),
        macro_f1=round(macro_f1, 4),
        log_loss=round(overall_log_loss, 4),
        brier_score=round(overall_brier, 4),
        expected_calibration_error=round(overall_ece, 4),
        mae=round(overall_mae, 2),
        rmse=round(overall_rmse, 2),
        median_absolute_error=round(overall_medae, 2),
        per_action_classification=per_act_class,
        per_action_amount=per_act_amt,
        potential_outcome_metrics=PotentialOutcomeMetrics(
            oracle_gap=round(mean_gap, 2),
            counterfactual_regret=round(mean_regret, 2),
            mean_best_achievable_value=round(mean_best, 2),
            mean_predicted_best_value=round(mean_pred_best, 2),
        ),
    )
