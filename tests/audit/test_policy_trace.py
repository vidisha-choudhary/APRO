"""Tests for PolicyTraceRecord generation and safety rules provenance."""

from datetime import UTC, datetime

from apro.audit.tracing import build_policy_trace
from apro.domain.enums import PolicyDecisionResult
from apro.domain.models import PolicyDecision


def test_build_policy_trace_with_rules() -> None:
    """Policy trace records rules triggered, outcome, and reason codes."""
    pol = PolicyDecision(
        policy_decision_id="pol_trace_test",
        decision_id="dec_trace_test",
        case_id="case_trace_test",
        result=PolicyDecisionResult.REQUIRE_HUMAN_APPROVAL,
        reason="H6_HIGH_VALUE_THRESHOLD: Recovery amount exceeds auto-approval ceiling",
        policy_version="policy-rules-v2",
        created_at=datetime.now(UTC),
    )
    trace = build_policy_trace(pol)

    assert trace.policy_decision_id == "pol_trace_test"
    assert trace.policy_outcome == "REQUIRE_HUMAN_APPROVAL"
    assert "H6_HIGH_VALUE_THRESHOLD" in trace.reason_code
    assert trace.policy_version == "policy-rules-v2"
