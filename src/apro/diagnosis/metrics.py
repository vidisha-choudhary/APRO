"""Metric calculation, classification formulas, and confusion matrix for Phase 7."""

import math

from pydantic import BaseModel, ConfigDict, Field

from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DiagnosisCategory,
)
from apro.diagnosis.traces import DiagnosisPredictionTrace


class PerClassMetric(BaseModel):
    """Evaluation metrics for a single diagnosis taxonomy category."""

    model_config = ConfigDict(frozen=True)

    category: DiagnosisCategory
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    support: int = Field(ge=0)


class DiagnosisMetrics(BaseModel):
    """Consolidated classification and calibration metrics for Model A evaluation."""

    model_config = ConfigDict(frozen=True)

    case_count: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    balanced_accuracy: float = Field(ge=0.0, le=1.0)
    macro_precision: float = Field(ge=0.0, le=1.0)
    macro_recall: float = Field(ge=0.0, le=1.0)
    macro_f1: float = Field(ge=0.0, le=1.0)
    weighted_f1: float = Field(ge=0.0, le=1.0)
    log_loss: float = Field(ge=0.0)
    brier_score: float = Field(ge=0.0)
    expected_calibration_error: float = Field(ge=0.0, le=1.0)
    top_1_accuracy: float = Field(ge=0.0, le=1.0)
    top_2_accuracy: float = Field(ge=0.0, le=1.0)
    per_class: dict[DiagnosisCategory, PerClassMetric]
    confusion_matrix: list[list[int]]
    average_decision_latency_ms: float = Field(default=0.0, ge=0.0)


def calculate_diagnosis_metrics(
    traces: list[DiagnosisPredictionTrace],
    num_calibration_bins: int = 10,
) -> DiagnosisMetrics:
    """Calculate multi-class classification and calibration metrics from traces."""
    n = len(traces)
    classes = list(DIAGNOSIS_TAXONOMY_ORDER)
    num_classes = len(classes)
    class_to_idx = {c: i for i, c in enumerate(classes)}

    if n == 0:
        empty_per_class = {
            c: PerClassMetric(category=c, precision=0.0, recall=0.0, f1=0.0, support=0)
            for c in classes
        }
        return DiagnosisMetrics(
            case_count=0,
            accuracy=0.0,
            balanced_accuracy=0.0,
            macro_precision=0.0,
            macro_recall=0.0,
            macro_f1=0.0,
            weighted_f1=0.0,
            log_loss=0.0,
            brier_score=0.0,
            expected_calibration_error=0.0,
            top_1_accuracy=0.0,
            top_2_accuracy=0.0,
            per_class=empty_per_class,
            confusion_matrix=[[0] * num_classes for _ in range(num_classes)],
            average_decision_latency_ms=0.0,
        )

    # 1. Build Confusion Matrix and per-class counts
    # Rows: Actual class, Columns: Predicted class
    matrix = [[0] * num_classes for _ in range(num_classes)]
    tp: dict[DiagnosisCategory, int] = dict.fromkeys(classes, 0)
    fp: dict[DiagnosisCategory, int] = dict.fromkeys(classes, 0)
    fn: dict[DiagnosisCategory, int] = dict.fromkeys(classes, 0)
    support: dict[DiagnosisCategory, int] = dict.fromkeys(classes, 0)

    correct_top1 = 0
    correct_top2 = 0
    total_log_loss = 0.0
    total_brier = 0.0
    total_latency = 0.0

    eps = 1e-15

    for t in traces:
        actual = t.actual_category
        predicted = t.predicted_category
        total_latency += t.decision_latency_ms

        if actual is None:
            continue

        act_idx = class_to_idx[actual]
        pred_idx = class_to_idx[predicted]
        matrix[act_idx][pred_idx] += 1
        support[actual] += 1

        if predicted == actual:
            correct_top1 += 1
            tp[actual] += 1
        else:
            fp[predicted] += 1
            fn[actual] += 1

        # Top-2 check
        sorted_probs = sorted(
            t.class_probabilities.items(), key=lambda item: item[1], reverse=True
        )
        top2_cats = [item[0] for item in sorted_probs[:2]]
        if actual in top2_cats:
            correct_top2 += 1

        # Log loss & Brier score
        actual_prob = max(eps, min(1.0, t.class_probabilities.get(actual, 0.0)))
        total_log_loss += -math.log(actual_prob)

        brier_sum = 0.0
        for c in classes:
            p = t.class_probabilities.get(c, 0.0)
            target = 1.0 if c == actual else 0.0
            brier_sum += (p - target) ** 2
        total_brier += brier_sum

    # 2. Per-class Precision, Recall, F1
    per_class_results: dict[DiagnosisCategory, PerClassMetric] = {}
    for c in classes:
        c_tp = tp[c]
        c_fp = fp[c]
        c_fn = fn[c]
        c_sup = support[c]

        prec = (c_tp / (c_tp + c_fp)) if (c_tp + c_fp) > 0 else 0.0
        rec = (c_tp / (c_tp + c_fn)) if (c_tp + c_fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        per_class_results[c] = PerClassMetric(
            category=c,
            precision=round(prec, 4),
            recall=round(rec, 4),
            f1=round(f1, 4),
            support=c_sup,
        )

    # 3. Macro and Weighted Aggregates
    macro_prec = sum(m.precision for m in per_class_results.values()) / num_classes
    macro_rec = sum(m.recall for m in per_class_results.values()) / num_classes
    macro_f1 = sum(m.f1 for m in per_class_results.values()) / num_classes

    # Balanced accuracy is average of recalls for classes with support > 0
    active_classes = [c for c in classes if support[c] > 0]
    if active_classes:
        balanced_acc = sum(per_class_results[c].recall for c in active_classes) / len(
            active_classes
        )
    else:
        balanced_acc = 0.0

    weighted_f1 = (
        sum(per_class_results[c].f1 * support[c] for c in classes) / n if n > 0 else 0.0
    )

    acc = correct_top1 / n
    top2_acc = correct_top2 / n
    avg_log_loss = total_log_loss / n
    avg_brier = total_brier / n

    # 4. Expected Calibration Error (ECE)
    bin_size = 1.0 / num_calibration_bins
    bin_counts = [0] * num_calibration_bins
    bin_corrects = [0] * num_calibration_bins
    bin_conf_sums = [0.0] * num_calibration_bins

    for t in traces:
        if t.actual_category is None:
            continue
        conf = t.confidence
        bin_idx = min(num_calibration_bins - 1, max(0, int(conf / bin_size)))
        bin_counts[bin_idx] += 1
        bin_conf_sums[bin_idx] += conf
        if t.predicted_category == t.actual_category:
            bin_corrects[bin_idx] += 1

    ece = 0.0
    for b in range(num_calibration_bins):
        cnt = bin_counts[b]
        if cnt > 0:
            bin_acc = bin_corrects[b] / cnt
            bin_conf = bin_conf_sums[b] / cnt
            ece += (cnt / n) * abs(bin_acc - bin_conf)

    return DiagnosisMetrics(
        case_count=n,
        accuracy=round(acc, 4),
        balanced_accuracy=round(balanced_acc, 4),
        macro_precision=round(macro_prec, 4),
        macro_recall=round(macro_rec, 4),
        macro_f1=round(macro_f1, 4),
        weighted_f1=round(weighted_f1, 4),
        log_loss=round(avg_log_loss, 4),
        brier_score=round(avg_brier, 4),
        expected_calibration_error=round(ece, 4),
        top_1_accuracy=round(acc, 4),
        top_2_accuracy=round(top2_acc, 4),
        per_class=per_class_results,
        confusion_matrix=matrix,
        average_decision_latency_ms=round(total_latency / n, 4),
    )
