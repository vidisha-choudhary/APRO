from datetime import UTC, datetime

from apro.evaluation.config import EvaluationConfig
from apro.evaluation.dataset import BenchmarkDatasetSnapshot
from apro.evaluation.evaluator import APROEvaluator
from apro.evaluation.models import BenchmarkCaseRecord, OfflineEvaluationTruth
from apro.evaluation.statistics import (
    adjust_p_values_holm,
    bootstrap_case_metric,
    compute_cohens_d,
    compute_cohens_h,
    compute_paired_bootstrap_ci,
    compute_paired_randomization_p_value,
    compute_proportion_ci,
)


def test_wilson_score_proportion_ci() -> None:
    """AC-32, AC-39: Test Wilson score confidence interval calculation."""
    # 70 recovered out of 100 cases
    lower, upper = compute_proportion_ci(70, 100, confidence_level=0.95)

    assert 0.60 <= lower <= 0.62
    assert 0.78 <= upper <= 0.80
    assert lower < 0.70 < upper


def test_bootstrap_case_level_reproducibility() -> None:
    """AC-34, AC-35, AC-36, AC-37: Test case-level bootstrap repeatability."""
    data = [1, 0, 1, 1, 0, 1, 0, 1, 1, 1] * 10  # 100 cases

    def _mean_fn(sample: list[object]) -> float:
        return sum(float(x) for x in sample) / len(sample)

    pt1, lower1, upper1 = bootstrap_case_metric(
        data, _mean_fn, confidence_level=0.95, iterations=500, seed=42
    )
    pt2, lower2, upper2 = bootstrap_case_metric(
        data, _mean_fn, confidence_level=0.95, iterations=500, seed=42
    )

    assert pt1 == pt2 == 0.7
    assert lower1 == lower2
    assert upper1 == upper2
    assert lower1 < pt1 < upper1


def test_paired_bootstrap_ci() -> None:
    """AC-38: Test paired case-level differences bootstrap."""
    # 100 cases where APRO recovered and Baseline failed (delta = +1)
    diffs = [1] * 50 + [0] * 50  # mean delta = +0.50

    l_ci, u_ci = compute_paired_bootstrap_ci(
        diffs, confidence_level=0.95, iterations=500, seed=101
    )

    assert 0.38 <= l_ci <= 0.42
    assert 0.58 <= u_ci <= 0.62
    assert l_ci > 0  # Statistically significant positive difference


def test_paired_randomization_p_value_reproducibility_and_bounds() -> None:
    """AC-38, AC-40: Test paired randomization test reproducibility and bounds."""
    diffs = [1] * 40 + [0] * 10

    p1 = compute_paired_randomization_p_value(diffs, iterations=1000, seed=42)
    p2 = compute_paired_randomization_p_value(diffs, iterations=1000, seed=42)

    # Identical seed and inputs produce identical p-values
    assert p1 == p2
    assert 0.0 <= p1 <= 1.0
    assert p1 < 0.005  # Strong positive difference has small p-value


def test_paired_randomization_p_value_sensitivity_to_data() -> None:
    """Test that changing underlying paired differences changes the p-value."""
    strong_diffs = [1] * 50
    weak_diffs = [1] * 28 + [-1] * 22
    null_diffs = [1] * 25 + [-1] * 25
    empty_diffs: list[int] = []

    p_strong = compute_paired_randomization_p_value(
        strong_diffs, iterations=1000, seed=42
    )
    p_weak = compute_paired_randomization_p_value(weak_diffs, iterations=1000, seed=42)
    p_null = compute_paired_randomization_p_value(null_diffs, iterations=1000, seed=42)
    p_empty = compute_paired_randomization_p_value(
        empty_diffs, iterations=1000, seed=42
    )

    # Validate sensitivity & ordering
    assert p_strong < p_weak < p_null
    assert p_null == 1.0
    assert p_empty == 1.0

    # Ensure not hardcoded constants
    assert p_strong != 0.001 or p_weak != 0.5
    assert 0.0 <= p_strong <= 1.0
    assert 0.0 <= p_weak <= 1.0


def test_holm_step_down_p_value_adjustment() -> None:
    """AC-40: Test Holm step-down multiple-comparison adjustment."""
    raw_p = [0.01, 0.04, 0.03, 0.005]  # 4 tests
    adjusted = adjust_p_values_holm(raw_p)

    assert len(adjusted) == 4
    # Sorted order of raw_p:
    # 1. 0.005 (rank 0, mult 4) -> 0.005 * 4 = 0.02
    # 2. 0.010 (rank 1, mult 3) -> 0.010 * 3 = 0.03
    # 3. 0.030 (rank 2, mult 2) -> 0.030 * 2 = 0.06
    # 4. 0.040 (rank 3, mult 1) -> 0.040 * 1 = 0.04 -> max(0.06, 0.04) = 0.06
    assert adjusted[3] == 0.02  # original index 3 (raw 0.005)
    assert adjusted[0] == 0.03  # original index 0 (raw 0.01)
    assert adjusted[2] == 0.06  # original index 2 (raw 0.03)
    assert adjusted[1] == 0.06  # original index 1 (raw 0.04)


def test_effect_sizes() -> None:
    """AC-41: Test Cohen's h and Cohen's d effect sizes."""
    # Difference between 70% and 50% recovery rates
    h = compute_cohens_h(0.70, 0.50)
    assert 0.40 <= h <= 0.45

    # Difference between two continuous metric distributions
    x = [10.0, 12.0, 11.0, 13.0, 12.0]
    y = [5.0, 6.0, 5.5, 6.5, 5.0]
    d = compute_cohens_d(x, y)
    assert d > 5.0


def test_benchmark_report_exposes_calculated_p_values_reproducibly() -> None:
    """AC-40, AC-42: Test benchmark report baseline p-values are computed."""
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)
    records = [
        BenchmarkCaseRecord(
            case_id=f"case_stat_{i}",
            payment_id=f"pay_stat_{i}",
            payment_amount=10000,
            opened_at=now,
            is_recovered=(i % 2 == 0),
            recovered_amount=10000 if (i % 2 == 0) else 0,
            intervention_count=1 if (i % 2 == 0) else 0,
            offline_truth=OfflineEvaluationTruth(
                ground_truth_recovered=(i % 2 == 0),
                ground_truth_recovered_amount=10000 if (i % 2 == 0) else 0,
                counterfactual_outcomes={
                    "RETRY": {
                        "status": "SUCCESS" if (i % 4 == 0) else "FAILURE",
                        "recovered_amount": 10000 if (i % 4 == 0) else 0,
                    }
                },
            ),
        )
        for i in range(40)
    ]

    snapshot = BenchmarkDatasetSnapshot.from_records(
        records, dataset_id="snap_p_val", dataset_version="1.0.0"
    )
    config = EvaluationConfig(bootstrap_seed=777, bootstrap_iterations=500)
    evaluator = APROEvaluator(config=config)

    report1 = evaluator.evaluate_dataset(snapshot)
    report2 = evaluator.evaluate_dataset(snapshot)

    assert "Fixed Retry" in report1.baseline_comparisons
    res1 = report1.baseline_comparisons["Fixed Retry"]
    res2 = report2.baseline_comparisons["Fixed Retry"]

    assert res1.p_value is not None
    assert res1.adjusted_p_value is not None
    assert 0.0 <= res1.p_value <= 1.0
    assert 0.0 <= res1.adjusted_p_value <= 1.0
    # Reproducibility
    assert res1.p_value == res2.p_value
    assert res1.adjusted_p_value == res2.adjusted_p_value
