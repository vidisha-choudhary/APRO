"""Unit tests for benchmark summary report generation (Phase 6)."""

import json

from apro.evaluation.baselines import AlwaysRetryStrategy, NoInterventionStrategy
from apro.evaluation.benchmark import BenchmarkConfig, BenchmarkRunner
from apro.evaluation.reports import (
    generate_benchmark_summary_json,
    generate_benchmark_summary_markdown,
)


def test_benchmark_summary_reporting() -> None:
    """AC-22, Correction E: Test report generation with truthful safety signals."""
    runner = BenchmarkRunner()
    config = BenchmarkConfig(
        benchmark_version="benchmark-report-v1",
        dataset_version="dataset-report-v1",
        target_case_count=50,
        seeds=[42, 101],
    )
    dataset = runner.generate_benchmark_dataset(config)
    result = runner.run_benchmark(
        dataset, [NoInterventionStrategy(), AlwaysRetryStrategy()]
    )

    # 1. JSON report
    json_str = generate_benchmark_summary_json(result)
    parsed = json.loads(json_str)
    assert parsed["manifest"]["benchmark_version"] == "benchmark-report-v1"
    assert "No Intervention" in parsed["strategy_metrics"]
    assert "Always Retry" in parsed["strategy_metrics"]
    assert "coverage" in parsed

    # 2. Markdown report
    md_str = generate_benchmark_summary_markdown(result)
    assert "# APRO Benchmark Summary Report" in md_str
    assert "benchmark-report-v1" in md_str
    assert "No Intervention" in md_str
    assert "Always Retry" in md_str
    assert "Multi-Seed Statistical Summary" in md_str
    assert "Scenario Dimension Coverage" in md_str

    # Correction E: verify truthfulness in Section 5
    assert "Policy Violation Count:** `N/A (unavailable in Phase 6)`" in md_str
    assert "Duplicate Execution Count:** `N/A (unavailable in Phase 6)`" in md_str
    assert (
        "Captured Payment Intervention Count:** `N/A (unavailable in Phase 6)`"
        in md_str
    )
    assert "Average Decision Latency:" in md_str
    assert "ms / decision" in md_str
