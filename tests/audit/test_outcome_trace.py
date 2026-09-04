"""Tests for OutcomeTraceRecord generation and outcome types."""

from datetime import UTC, datetime

from apro.audit.tracing import build_outcome_trace
from apro.domain.enums import OutcomeType
from apro.domain.models import Outcome


def test_build_outcome_trace_distinction() -> None:
    """Outcome trace records exact outcome type and recovered amount."""
    now = datetime.now(UTC)
    outcome = Outcome(
        outcome_id="out_trace_1",
        case_id="case_trace_1",
        execution_id="exec_trace_1",
        type=OutcomeType.PENDING,
        amount_recovered=0,
        evidence_reference="provenance=SIMULATOR;in_flight=true",
        observed_at=now,
    )
    trace = build_outcome_trace(outcome)

    assert trace.outcome_id == "out_trace_1"
    assert trace.outcome_type == "PENDING"
    assert trace.amount_recovered == 0
    assert trace.provenance == "SIMULATOR"
