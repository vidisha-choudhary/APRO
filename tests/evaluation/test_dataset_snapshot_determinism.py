"""Tests for snapshot determinism, case accounting, and truth isolation (Phase 15)."""

from datetime import UTC, datetime

import pytest

from apro.evaluation.config import EvaluationConfig
from apro.evaluation.dataset import (
    BenchmarkDatasetSnapshot,
    EligibilityClassifier,
    TruthPlaneSeparation,
    compute_deterministic_snapshot_hash,
)
from apro.evaluation.enums import EvaluationCaseStatus
from apro.evaluation.exceptions import (
    CheatingViolationError,
    DatasetInvalidError,
)
from apro.evaluation.models import (
    BenchmarkCaseRecord,
    OfflineEvaluationTruth,
)


def _create_mock_case(
    case_id: str,
    amount: int = 100000,
    status: str = "CLOSED_RECOVERED",
    is_rec: bool = True,
    rec_amt: int = 100000,
) -> BenchmarkCaseRecord:
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)
    return BenchmarkCaseRecord(
        case_id=case_id,
        payment_id=f"pay_{case_id}",
        payment_amount=amount,
        currency="INR",
        payment_method="CARD",
        case_status=status,
        failure_code="GATEWAY_TIMEOUT",
        failure_category="TRANSIENT_SYSTEM",
        opened_at=now,
        closed_at=now,
        duration_seconds=12.5,
        is_recovered=is_rec,
        recovered_amount=rec_amt,
        cycle_count=1,
        intervention_count=1,
        offline_truth=OfflineEvaluationTruth(
            ground_truth_recovered=is_rec,
            ground_truth_recovered_amount=rec_amt,
            ground_truth_best_action="RETRY",
        ),
    )


def test_snapshot_hash_is_deterministic() -> None:
    """AC-01, AC-02: Test dataset snapshot receives deterministic SHA-256 hash."""
    cases_1 = [
        _create_mock_case("c1"),
        _create_mock_case("c2"),
        _create_mock_case("c3"),
    ]
    cases_2 = [
        _create_mock_case("c3"),
        _create_mock_case("c1"),
        _create_mock_case("c2"),
    ]

    hash_1 = compute_deterministic_snapshot_hash(cases_1)
    hash_2 = compute_deterministic_snapshot_hash(cases_2)

    assert isinstance(hash_1, str)
    assert len(hash_1) == 64
    # Independent of input case ordering due to sorting
    assert hash_1 == hash_2


def test_snapshot_creation_from_records() -> None:
    """AC-01, AC-07: Test snapshot model creation and immutability."""
    cases = [_create_mock_case("c1"), _create_mock_case("c2")]
    snapshot = BenchmarkDatasetSnapshot.from_records(
        cases, dataset_id="test-bench-v1", dataset_version="1.0.0"
    )

    assert snapshot.dataset_id == "test-bench-v1"
    assert snapshot.dataset_version == "1.0.0"
    assert len(snapshot) == 2
    assert snapshot[0].case_id == "c1"
    assert len(snapshot.snapshot_hash) == 64


def test_empty_snapshot_raises_error() -> None:
    """AC-02: Test creating snapshot with empty records raises DatasetInvalidError."""
    with pytest.raises(DatasetInvalidError):
        BenchmarkDatasetSnapshot.from_records([])


def test_case_accounting_and_eligibility() -> None:
    """AC-05, AC-06: Test deterministic case accounting and duplicate detection."""
    cfg = EvaluationConfig()
    c1 = _create_mock_case("c1")
    c2 = _create_mock_case("c2")
    c_dup = _create_mock_case("c1")  # duplicate
    c_invalid = _create_mock_case("c3", amount=0)  # invalid non-positive amount

    eligible, results, counts = EligibilityClassifier.filter_and_account_cases(
        [c1, c2, c_dup, c_invalid], cfg
    )

    assert len(eligible) == 2
    assert counts["total_cases"] == 4
    assert counts["eligible"] == 2
    assert counts["excluded"] == 2
    assert counts["duplicate_case"] == 1
    assert counts["invalid_case"] == 1

    dup_res = next(r for r in results if r.case_id == "c1" and not r.is_eligible)
    assert dup_res.status == EvaluationCaseStatus.DUPLICATE_CASE
    assert "Duplicate" in str(dup_res.exclusion_reason)


def test_truth_plane_isolation_guard() -> None:
    """AC-08: Test anti-cheating validator raises on leaked oracle truth."""
    from apro.domain.models import Decision

    now = datetime.now(UTC)
    case_clean = _create_mock_case("c_clean")
    TruthPlaneSeparation.verify_isolation([case_clean])

    # Inject oracle leakage into runtime decision reason
    leaked_decision = Decision(
        decision_id="d1",
        case_id="c_leak",
        recommended_action="RETRY",
        confidence=0.9,
        expected_recovery_value=100000,
        reason="Selected based on ground_truth_recovered knowledge",
        model_name="test",
        model_version="1.0",
        created_at=now,
    )
    case_leaked = BenchmarkCaseRecord(
        case_id="c_leak",
        payment_id="p_leak",
        payment_amount=100000,
        case_status="CLOSED_RECOVERED",
        opened_at=now,
        decisions=[leaked_decision],
    )

    with pytest.raises(CheatingViolationError) as exc_info:
        TruthPlaneSeparation.verify_isolation([case_leaked])

    assert "Oracle truth leaked" in str(exc_info.value)
