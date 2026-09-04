"""Unit tests for evaluation baselines fairness and delta metrics (Phase 15)."""

from datetime import UTC, datetime

from apro.evaluation.baselines import (
    FixedEscalationBaseline,
    FixedRetryBaseline,
    NoInterventionBaseline,
    PaymentLinkBaseline,
    evaluate_baselines_comparison,
)
from apro.evaluation.config import EvaluationConfig
from apro.evaluation.metrics import compute_primary_kpis
from apro.evaluation.models import (
    BenchmarkCaseRecord,
    OfflineEvaluationTruth,
)


def _make_case(
    case_id: str,
    amount: int,
    is_rec: bool,
    rec_amt: int,
    retry_cf: str = "FAILURE",
    link_cf: str = "FAILURE",
    esc_cf: str = "FAILURE",
) -> BenchmarkCaseRecord:
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)
    cf_map = {
        "RETRY": {
            "status": retry_cf,
            "recovered_amount": amount if retry_cf == "SUCCESS" else 0,
        },
        "PAYMENT_LINK": {
            "status": link_cf,
            "recovered_amount": amount if link_cf == "SUCCESS" else 0,
        },
        "ESCALATE": {
            "status": esc_cf,
            "recovered_amount": amount if esc_cf == "SUCCESS" else 0,
        },
    }
    return BenchmarkCaseRecord(
        case_id=case_id,
        payment_id=f"pay_{case_id}",
        payment_amount=amount,
        opened_at=now,
        is_recovered=is_rec,
        recovered_amount=rec_amt,
        intervention_count=1 if is_rec else 0,
        offline_truth=OfflineEvaluationTruth(
            ground_truth_recovered=is_rec,
            ground_truth_recovered_amount=rec_amt,
            counterfactual_outcomes=cf_map,
        ),
    )


def test_baseline_behaviors_and_costs() -> None:
    """AC-21, AC-22, AC-23, AC-24, AC-27: Test baseline evaluate_case methods."""
    cfg = EvaluationConfig()
    c = _make_case("c1", 100000, is_rec=True, rec_amt=100000, retry_cf="SUCCESS")

    b_none = NoInterventionBaseline()
    b_retry = FixedRetryBaseline()
    b_link = PaymentLinkBaseline()
    b_esc = FixedEscalationBaseline()

    # No intervention: 0 recovery, 0 cost
    is_r, amt, cost = b_none.evaluate_case(c, cfg)
    assert not is_r
    assert amt == 0
    assert cost == 0

    # Fixed retry: succeeds via counterfactual
    is_r, amt, cost = b_retry.evaluate_case(c, cfg)
    assert is_r
    assert amt == 100000
    assert cost == 100  # ₹1.00

    # Payment link: fails via counterfactual
    is_r, amt, cost = b_link.evaluate_case(c, cfg)
    assert not is_r
    assert amt == 0
    assert cost == 200  # ₹2.00

    # Escalation: fails via counterfactual
    is_r, amt, cost = b_esc.evaluate_case(c, cfg)
    assert not is_r
    assert amt == 0
    assert cost == 1000  # ₹10.00


def test_baselines_identical_cohort_comparison() -> None:
    """AC-26, AC-28, AC-29: Test baseline comparison runs over identical cases."""
    cfg = EvaluationConfig()
    cases = [
        # Case 1: APRO recovered (100k), Retry succeeds (100k), Link fails
        _make_case("c1", 100000, True, 100000, retry_cf="SUCCESS", link_cf="FAILURE"),
        # Case 2: APRO recovered (200k), Retry fails, Link succeeds (200k)
        _make_case("c2", 200000, True, 200000, retry_cf="FAILURE", link_cf="SUCCESS"),
        # Case 3: APRO stopped (0), all fail
        _make_case("c3", 300000, False, 0, retry_cf="FAILURE", link_cf="FAILURE"),
    ]

    apro_kpis = compute_primary_kpis(cases, cfg)
    comparisons = evaluate_baselines_comparison(cases, cfg, apro_kpis)

    assert "No Intervention" in comparisons
    assert "Fixed Retry" in comparisons
    assert "Payment Link" in comparisons
    assert "Fixed Escalation" in comparisons

    # APRO: 2 / 3 = 66.67%
    assert apro_kpis.recovery_rate == 0.6667
    assert apro_kpis.gross_recovered_amount == 300000

    # No Intervention: 0% recovery
    no_int = comparisons["No Intervention"]
    assert no_int.baseline_recovery_rate == 0.0
    assert no_int.absolute_recovery_delta == 0.6667
    assert no_int.incremental_recovered_amount == 300000

    # Fixed Retry: 1 / 3 = 33.33% recovery (Case 1)
    retry_comp = comparisons["Fixed Retry"]
    assert retry_comp.baseline_recovery_rate == 0.3333
    assert retry_comp.absolute_recovery_delta == round(0.6667 - 0.3333, 4)
    assert retry_comp.baseline_gross_recovered == 100000
    assert retry_comp.incremental_recovered_amount == 200000
