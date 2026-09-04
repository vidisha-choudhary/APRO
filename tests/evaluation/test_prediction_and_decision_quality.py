"""Unit tests for Phase 8 calibration and Phase 9 decision quality (Phase 15)."""

from datetime import UTC, datetime

from apro.domain.models import Decision
from apro.evaluation.calibration import (
    compute_brier_score,
    compute_calibration_curve,
    compute_classification_metrics,
)
from apro.evaluation.config import EvaluationConfig
from apro.evaluation.evaluator import APROEvaluator
from apro.evaluation.models import (
    BenchmarkCaseRecord,
    OfflineEvaluationTruth,
)


def test_brier_score_computation() -> None:
    """AC-44: Test Brier score calculation is deterministic."""
    # Perfect predictions
    assert compute_brier_score([1.0, 0.0, 1.0], [1, 0, 1]) == 0.0
    # Complete opposite
    assert compute_brier_score([0.0, 1.0, 0.0], [1, 0, 1]) == 1.0
    # Realistic predictions
    score = compute_brier_score([0.8, 0.2, 0.9, 0.3], [1, 0, 1, 0])
    # Total error: 0.04 + 0.04 + 0.01 + 0.09 = 0.18 / 4 = 0.045
    assert score == 0.045


def test_calibration_curve_binning() -> None:
    """AC-45: Test calibration curve partitions probabilities into valid bins."""
    preds = [0.05, 0.15, 0.85, 0.95]
    outs = [0, 0, 1, 1]
    bins = compute_calibration_curve(preds, outs, num_bins=5)

    assert len(bins) == 5
    # First bin [0.0, 0.2) should have 2 samples (0.05, 0.15) with empirical rate 0.0
    assert bins[0].sample_count == 2
    assert bins[0].empirical_success_rate == 0.0

    # Last bin [0.8, 1.0] should have 2 samples (0.85, 0.95) with empirical rate 1.0
    assert bins[4].sample_count == 2
    assert bins[4].empirical_success_rate == 1.0


def test_classification_metrics() -> None:
    """AC-46: Test precision, recall, F1, log loss, and ROC-AUC."""
    preds = [0.9, 0.8, 0.3, 0.1]
    outs = [1, 1, 0, 0]
    metrics = compute_classification_metrics(preds, outs)

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["log_loss"] is not None and metrics["log_loss"] < 0.3


def test_decision_quality_metrics_and_oracle_gap() -> None:
    """AC-48, AC-50: Test Phase 9 decision metrics, ERV, and regret."""
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

    # Case where APRO chose optimal RETRY
    c1 = BenchmarkCaseRecord(
        case_id="c1",
        payment_id="p1",
        payment_amount=100000,
        opened_at=now,
        is_recovered=True,
        recovered_amount=100000,
        final_action_type="RETRY",
        decisions=[
            Decision(
                decision_id="d1",
                case_id="c1",
                recommended_action="RETRY",
                confidence=0.9,
                expected_recovery_value=85000,
                reason="Transient failure",
                model_name="test_model",
                model_version="1.0",
                created_at=now,
            )
        ],
        offline_truth=OfflineEvaluationTruth(
            ground_truth_recovered=True,
            ground_truth_recovered_amount=100000,
            ground_truth_best_action="RETRY",
        ),
    )

    evaluator = APROEvaluator(EvaluationConfig())
    dq = evaluator._evaluate_decision_quality([c1])

    assert dq.selected_action_distribution.get("RETRY") == 1
    assert dq.selected_action_erv_avg == 85000.0
    assert dq.best_action_selection_rate == 1.0
    assert dq.action_regret_avg == 0.0
