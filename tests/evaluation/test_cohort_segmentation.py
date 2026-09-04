"""Unit tests for cohort segmentation and small cohort flagging (Phase 15)."""

from datetime import UTC, datetime

from apro.evaluation.config import EvaluationConfig
from apro.evaluation.models import BenchmarkCaseRecord
from apro.evaluation.segmentation import (
    compute_all_cohort_breakdowns,
    get_amount_bucket,
    segment_cases,
)


def test_amount_bucketing() -> None:
    """AC-63: Test standard payment amount bucketing."""
    assert "LOW_VALUE" in get_amount_bucket(50000)  # ₹500
    assert "MEDIUM_VALUE" in get_amount_bucket(250000)  # ₹2,500
    assert "HIGH_VALUE" in get_amount_bucket(1000000)  # ₹10,000


def test_cohort_segmentation_and_small_cohort_flag() -> None:
    """AC-63, AC-64, AC-65, AC-66, AC-67: Test segmentation and small cohort flag."""
    cfg = EvaluationConfig(minimum_cohort_size=3)
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

    # 4 UPI cases and 2 CARD cases (CARD is small cohort < 3)
    cases = [
        BenchmarkCaseRecord(
            case_id=f"c_upi_{i}",
            payment_id=f"p_upi_{i}",
            payment_amount=100000,
            payment_method="UPI",
            failure_category="TRANSIENT_SYSTEM",
            final_action_type="RETRY",
            opened_at=now,
            is_recovered=True,
            recovered_amount=100000,
        )
        for i in range(4)
    ] + [
        BenchmarkCaseRecord(
            case_id=f"c_card_{i}",
            payment_id=f"p_card_{i}",
            payment_amount=500000,
            payment_method="CARD",
            failure_category="CUSTOMER_ACTIONABLE",
            final_action_type="PAYMENT_LINK",
            opened_at=now,
            is_recovered=False,
            recovered_amount=0,
        )
        for i in range(2)
    ]

    breakdowns = segment_cases(cases, "payment_method", cfg)

    assert len(breakdowns) == 2
    upi_b = next(b for b in breakdowns if b.cohort_key == "UPI")
    card_b = next(b for b in breakdowns if b.cohort_key == "CARD")

    assert upi_b.case_count == 4
    assert not upi_b.is_small_cohort
    assert upi_b.recovery_rate == 1.0
    assert upi_b.gross_recovered == 400000

    assert card_b.case_count == 2
    assert card_b.is_small_cohort  # 2 < minimum_cohort_size (3)
    assert card_b.recovery_rate == 0.0

    # All breakdowns compute without error
    all_b = compute_all_cohort_breakdowns(cases, cfg)
    assert "failure_category" in all_b
    assert "selected_action" in all_b
    assert "payment_method" in all_b
    assert "amount_bucket" in all_b
