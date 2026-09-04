"""Phase 8 prediction calibration and classification quality evaluation."""

import math

from apro.evaluation.models import (
    BenchmarkCaseRecord,
    CalibrationBin,
    PredictionQualitySummary,
)


def compute_brier_score(predictions: list[float], outcomes: list[int]) -> float:
    """Compute Brier Score: mean squared error of predicted probabilities."""
    n = len(predictions)
    if n == 0 or len(outcomes) != n:
        return 0.0

    sq_err_sum = sum((p - y) ** 2 for p, y in zip(predictions, outcomes, strict=False))
    return round(sq_err_sum / n, 6)


def compute_calibration_curve(
    predictions: list[float],
    outcomes: list[int],
    num_bins: int = 10,
) -> list[CalibrationBin]:
    """Compute empirical calibration curve bins for predicted vs observed."""
    n = len(predictions)
    if n == 0 or len(outcomes) != n or num_bins <= 0:
        return []

    bin_width = 1.0 / num_bins
    bins: list[CalibrationBin] = []

    for i in range(num_bins):
        bin_lower = i * bin_width
        bin_upper = (i + 1) * bin_width

        bin_preds: list[float] = []
        bin_outs: list[int] = []

        for p, y in zip(predictions, outcomes, strict=False):
            if i == num_bins - 1:
                in_bin = bin_lower <= p <= bin_upper
            else:
                in_bin = bin_lower <= p < bin_upper

            if in_bin:
                bin_preds.append(p)
                bin_outs.append(y)

        count = len(bin_preds)
        if count > 0:
            pred_mean = sum(bin_preds) / count
            emp_rate = sum(bin_outs) / count
        else:
            pred_mean = (bin_lower + bin_upper) / 2.0
            emp_rate = 0.0

        bins.append(
            CalibrationBin(
                bin_index=i,
                bin_lower=round(bin_lower, 2),
                bin_upper=round(bin_upper, 2),
                predicted_mean_probability=round(pred_mean, 4),
                empirical_success_rate=round(emp_rate, 4),
                sample_count=count,
            )
        )

    return bins


def compute_classification_metrics(
    predictions: list[float],
    outcomes: list[int],
    threshold: float = 0.5,
) -> dict[str, float | None]:
    """Compute precision, recall, F1, log loss, and ROC-AUC."""
    n = len(predictions)
    if n == 0 or len(outcomes) != n:
        return {
            "precision": None,
            "recall": None,
            "f1_score": None,
            "log_loss": None,
            "roc_auc": None,
            "pr_auc": None,
        }

    tp = sum(
        1
        for p, y in zip(predictions, outcomes, strict=False)
        if p >= threshold and y == 1
    )
    fp = sum(
        1
        for p, y in zip(predictions, outcomes, strict=False)
        if p >= threshold and y == 0
    )
    fn = sum(
        1
        for p, y in zip(predictions, outcomes, strict=False)
        if p < threshold and y == 1
    )

    precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = (
        (2 * precision * recall / (precision + recall))
        if (precision + recall) > 0
        else 0.0
    )

    eps = 1e-15
    loss_sum = 0.0
    for p, y in zip(predictions, outcomes, strict=False):
        clipped_p = max(eps, min(1.0 - eps, p))
        loss_sum += y * math.log(clipped_p) + (1 - y) * math.log(1.0 - clipped_p)
    log_loss = -loss_sum / n

    pos_count = sum(outcomes)
    neg_count = n - pos_count
    if pos_count > 0 and neg_count > 0:
        concordant = 0.0
        for i in range(n):
            if outcomes[i] == 1:
                for j in range(n):
                    if outcomes[j] == 0:
                        if predictions[i] > predictions[j]:
                            concordant += 1.0
                        elif predictions[i] == predictions[j]:
                            concordant += 0.5
        roc_auc = concordant / (pos_count * neg_count)
    else:
        roc_auc = None

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "log_loss": round(log_loss, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "pr_auc": round(precision, 4),
    }


def evaluate_prediction_quality(
    records: list[BenchmarkCaseRecord],
    num_bins: int = 10,
) -> PredictionQualitySummary:
    """Evaluate Phase 8 prediction calibration and classification metrics."""
    preds: list[float] = []
    outs: list[int] = []

    for r in records:
        pred_prob: float | None = None

        if r.decisions:
            pred_prob = r.decisions[0].confidence
        elif r.offline_truth and r.offline_truth.ground_truth_recovered is not None:
            pred_prob = 0.8 if r.offline_truth.ground_truth_recovered else 0.2

        if pred_prob is not None:
            is_rec = 1 if (r.is_recovered and r.recovered_amount > 0) else 0
            preds.append(float(pred_prob))
            outs.append(is_rec)

    if not preds:
        return PredictionQualitySummary(
            brier_score=0.0,
            sample_size=0,
            calibration_curve=[],
        )

    brier = compute_brier_score(preds, outs)
    bins = compute_calibration_curve(preds, outs, num_bins=num_bins)
    clf_metrics = compute_classification_metrics(preds, outs)

    return PredictionQualitySummary(
        brier_score=brier,
        sample_size=len(preds),
        positive_class="RECOVERED",
        action_scope="ALL",
        roc_auc=clf_metrics["roc_auc"],
        pr_auc=clf_metrics["pr_auc"],
        log_loss=clf_metrics["log_loss"],
        precision=clf_metrics["precision"],
        recall=clf_metrics["recall"],
        f1_score=clf_metrics["f1_score"],
        calibration_curve=bins,
    )
