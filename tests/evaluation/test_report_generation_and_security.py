"""Unit tests for report generation, stability, and security sanitization (Phase 15)."""

import json
from datetime import UTC, datetime

from apro.evaluation.config import EvaluationConfig
from apro.evaluation.dataset import BenchmarkDatasetSnapshot
from apro.evaluation.evaluator import APROEvaluator
from apro.evaluation.models import (
    BenchmarkCaseRecord,
    OfflineEvaluationTruth,
)
from apro.evaluation.report import (
    compute_report_hash,
    generate_json_report,
    generate_markdown_report,
)


def _build_test_snapshot() -> BenchmarkDatasetSnapshot:
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)
    cases = [
        BenchmarkCaseRecord(
            case_id=f"case_{i}",
            payment_id=f"pay_{i}",
            payment_amount=100000,
            currency="INR",
            payment_method="UPI",
            case_status="CLOSED_RECOVERED" if i % 2 == 0 else "CLOSED_STOPPED",
            failure_code="GATEWAY_TIMEOUT",
            failure_category="TRANSIENT_SYSTEM",
            opened_at=now,
            closed_at=now,
            duration_seconds=15.0,
            is_recovered=(i % 2 == 0),
            recovered_amount=100000 if (i % 2 == 0) else 0,
            intervention_count=1,
            final_action_type="RETRY",
            offline_truth=OfflineEvaluationTruth(
                ground_truth_recovered=(i % 2 == 0),
                ground_truth_recovered_amount=100000 if (i % 2 == 0) else 0,
                ground_truth_best_action="RETRY",
            ),
        )
        for i in range(10)
    ]
    return BenchmarkDatasetSnapshot.from_records(
        cases, dataset_id="sec-test-bench", dataset_version="1.0.0"
    )


def test_report_generation_and_hash_stability() -> None:
    """AC-68, AC-69, AC-70, AC-71, AC-72: Test report generation and hash stability."""
    snapshot = _build_test_snapshot()
    evaluator = APROEvaluator(EvaluationConfig())

    report1 = evaluator.evaluate_dataset(
        snapshot,
        benchmark_run_id="run_fixed_123",
        created_at="2026-09-04T12:00:00Z",
    )
    report2 = evaluator.evaluate_dataset(
        snapshot,
        benchmark_run_id="run_fixed_123",
        created_at="2026-09-04T12:00:00Z",
    )

    # 1. Report Hash is deterministic
    hash1 = compute_report_hash(report1)
    hash2 = compute_report_hash(report2)
    assert hash1 == hash2

    # 2. Markdown output contains mandatory sections
    md = generate_markdown_report(report1)
    assert "# APRO Phase 15 — Authoritative Benchmark Evaluation Report" in md
    assert "## 1. Executive Summary" in md
    assert "## 2. Primary KPI Table" in md
    assert "## 3. Baseline Comparison Table" in md
    assert "## 4. Safety & Invariant Verification Table" in md
    assert "## 9. Evaluation Limitations & Scope" in md
    assert "## 10. Reproducibility Metadata" in md

    # 3. JSON output is valid
    json_str = generate_json_report(report1)
    parsed = json.loads(json_str)
    assert parsed["report_id"] == report1.report_id
    assert parsed["primary_kpis"]["case_count"] == 10


def test_security_sentinel_leakage_absence() -> None:
    """AC-73, AC-74, AC-75: Ensure credentials and secrets are absent."""
    snapshot = _build_test_snapshot()
    evaluator = APROEvaluator(EvaluationConfig())
    report = evaluator.evaluate_dataset(snapshot, benchmark_run_id="run_sec_test")

    json_dump = json.dumps(report.model_dump())
    md_dump = generate_markdown_report(report)

    sentinel_secrets = [
        "rzp_live_secret",
        "rzp_test_secret",
        "postgres_local_dev_2026",
        "4111222233334444",  # Card PAN
        "Authorization: Bearer",
        "password",
        "SECRET_KEY",
    ]

    for secret in sentinel_secrets:
        assert secret not in json_dump, f"Secret {secret} leaked into report JSON!"
        assert secret not in md_dump, f"Secret {secret} leaked into report Markdown!"
