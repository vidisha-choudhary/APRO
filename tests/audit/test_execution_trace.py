"""Tests for ExecutionTraceRecord generation and sanitization."""

from datetime import UTC, datetime, timedelta

from apro.audit.tracing import build_execution_trace
from apro.domain.enums import ExecutionMode, ExecutionStatus
from apro.domain.models import Execution


def test_build_execution_trace_sanitizes_provider_reference() -> None:
    """Execution trace records duration and sanitizes raw provider references."""
    start = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    end = start + timedelta(milliseconds=350)
    exc = Execution(
        execution_id="exec_test_123",
        action_id="act_test_123",
        case_id="case_test_123",
        execution_type="payment_link_executor",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SUCCEEDED,
        provider_reference="plink_12345 (key_secret=secret_xyz999)",
        started_at=start,
        completed_at=end,
    )
    trace = build_execution_trace(exc)

    assert trace.execution_id == "exec_test_123"
    assert trace.duration_ms == 350.0
    assert trace.status == "SUCCEEDED"
    assert "secret_xyz999" not in str(trace.provider_reference)
