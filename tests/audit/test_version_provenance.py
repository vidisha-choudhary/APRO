"""Tests for AI and policy model version provenance preservation."""

from datetime import UTC, datetime

from apro.audit.tracing import build_decision_trace, build_policy_trace
from apro.domain.enums import PolicyDecisionResult, RecoveryActionType
from apro.domain.models import Decision, PolicyDecision


def test_decision_model_version_provenance() -> None:
    """Historical decision records retain their exact model and dataset versions."""
    dec = Decision(
        decision_id="dec_historical",
        case_id="case_hist",
        recommended_action=RecoveryActionType.RETRY,
        confidence=0.88,
        expected_recovery_value=4500,
        reason="Model recommended retry",
        model_name="xgboost_recovery_ranker",
        model_version="1.0.0-legacy",
        created_at=datetime(2026, 1, 15, 10, 0, tzinfo=UTC),
    )
    trace = build_decision_trace(dec, cycle_number=1)
    assert trace.model_version == "1.0.0-legacy"
    assert trace.model_name == "xgboost_recovery_ranker"
    assert trace.selected_action == "RETRY"


def test_policy_version_provenance() -> None:
    """Policy decision records retain their exact policy versions."""
    pol = PolicyDecision(
        policy_decision_id="pol_hist",
        decision_id="dec_hist",
        case_id="case_hist",
        result=PolicyDecisionResult.ALLOW,
        reason="H1_MAX_ATTEMPTS: Allowed under attempt ceiling",
        policy_version="policy-v1.0.0-legacy",
        created_at=datetime(2026, 1, 15, 10, 1, tzinfo=UTC),
    )
    trace = build_policy_trace(pol)
    assert trace.policy_version == "policy-v1.0.0-legacy"
    assert trace.policy_outcome == "ALLOW"
    assert "H1_MAX_ATTEMPTS" in trace.reason_code
