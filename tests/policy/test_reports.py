"""Unit tests for Phase 10 Markdown and JSON report generators."""

import tempfile
from pathlib import Path

from apro.policy.evaluation import PolicySafetyMetrics
from apro.policy.reports import (
    export_policy_metrics_json,
    format_policy_markdown_report,
)


def test_format_policy_markdown_report():
    """Verify Markdown report generation format."""
    metrics = PolicySafetyMetrics(
        total_evaluations=100,
        allow_count=70,
        block_count=20,
        require_human_approval_count=10,
        allow_rate=0.70,
        block_rate=0.20,
        require_human_approval_rate=0.10,
        constraint_violation_count=0,
        high_value_approval_count=8,
        low_confidence_approval_count=2,
        reason_code_counts={"POLICY_ALLOWED": 70, "HIGH_VALUE_REQUIRES_APPROVAL": 8},
    )

    report_md = format_policy_markdown_report(metrics)
    assert "# APRO Phase 10 — Policy & Safety Engine Evaluation Report" in report_md
    assert "70.00%" in report_md
    assert "Zero Violations" in report_md
    assert "`HIGH_VALUE_REQUIRES_APPROVAL`" in report_md


def test_export_policy_metrics_json():
    """Verify JSON export of metrics."""
    metrics = PolicySafetyMetrics(
        total_evaluations=50,
        allow_count=35,
        block_count=10,
        require_human_approval_count=5,
        allow_rate=0.70,
        block_rate=0.20,
        require_human_approval_rate=0.10,
        constraint_violation_count=0,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "metrics.json"
        export_policy_metrics_json(metrics, json_path)
        assert json_path.exists()
