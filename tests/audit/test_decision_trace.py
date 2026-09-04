"""Tests for DecisionTraceRecord generation and provenance."""

from datetime import UTC, datetime

from apro.audit.tracing import build_decision_trace
from apro.domain.enums import RecoveryActionType
from apro.domain.models import Decision


def test_build_decision_trace_with_candidates() -> None:
    """Decision trace records candidate actions and model versions."""
    dec = Decision(
        decision_id="dec_trace_test",
        case_id="case_trace_test",
        recommended_action=RecoveryActionType.ALTERNATE_RECOVERY,
        confidence=0.91,
        expected_recovery_value=7200,
        reason="Economic engine selected max ERV action",
        model_name="economic_decision_engine",
        model_version="2.1.0",
        created_at=datetime.now(UTC),
    )
    candidates = [
        {"action": "RETRY", "erv": 4000, "cost": 500},
        {"action": "ALTERNATE_RECOVERY", "erv": 7200, "cost": 1500},
        {"action": "OUTREACH", "erv": 5500, "cost": 800},
    ]

    trace = build_decision_trace(
        decision=dec,
        cycle_number=1,
        candidate_actions=candidates,
    )
    assert trace.decision_id == "dec_trace_test"
    assert trace.selected_action == "ALTERNATE_RECOVERY"
    assert trace.expected_recovery_value == 7200
    assert trace.model_version == "2.1.0"
    assert len(trace.candidate_actions) == 3
    assert trace.candidate_actions[1]["action"] == "ALTERNATE_RECOVERY"
