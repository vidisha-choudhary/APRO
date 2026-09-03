"""Tests for deterministic idempotency and provider reference handling."""

from datetime import UTC, datetime

from apro.domain.enums import ExecutionMode, RecoveryActionType
from apro.execution.models import ApprovedExecutionRequest
from apro.providers.razorpay.mapper import map_approved_request_to_payment_link_request


def _make_request(exec_id: str, case_id: str) -> ApprovedExecutionRequest:
    now = datetime.now(UTC)
    return ApprovedExecutionRequest(
        execution_id=exec_id,
        case_id=case_id,
        action_id="act_test_idem",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        policy_decision_id="pol_test_idem",
        idempotency_key=f"idem_{case_id}_PLINK",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters={"amount": 50000},
        requested_at=now,
        policy_version="pol-v1",
        rule_set_version="rules-v1",
        action_schema_version="act-v1",
    )


def test_deterministic_provider_reference_id() -> None:
    """Verify equivalent requests produce deterministic provider reference_id."""
    req1 = _make_request("exec_111", "case_abc")
    req2 = _make_request("exec_111", "case_abc")

    plink_req1 = map_approved_request_to_payment_link_request(req1)
    plink_req2 = map_approved_request_to_payment_link_request(req2)

    assert plink_req1.reference_id == plink_req2.reference_id
    assert plink_req1.reference_id is not None
    assert len(plink_req1.reference_id) <= 40
