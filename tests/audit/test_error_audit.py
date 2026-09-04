"""Tests for error, failure, and edge condition telemetry."""

import pytest

from apro.audit.enums import AuditEventType
from apro.audit.service import AuditService
from apro.domain.enums import AuditActor, PolicyDecisionResult
from apro.domain.models import PolicyDecision


@pytest.mark.asyncio
async def test_policy_block_audit() -> None:
    """Policy BLOCK event is audited cleanly with reason code."""
    service = AuditService()
    pol = PolicyDecision(
        policy_decision_id="pol_block_1",
        decision_id="dec_block_1",
        case_id="case_block_1",
        result=PolicyDecisionResult.BLOCK,
        reason="H3_MAX_VELOCITY: Rate limit exceeded for customer",
        policy_version="policy-v1",
        created_at=pytest.importorskip("datetime").datetime.now(
            pytest.importorskip("datetime").UTC
        ),
    )
    ev = await service.record_policy_decision(pol)
    assert ev.event_type == AuditEventType.POLICY_DECISION_CREATED
    assert ev.payload["result"] == "BLOCK"
    assert "H3_MAX_VELOCITY" in ev.payload["reason_code"]


@pytest.mark.asyncio
async def test_error_observed_audit() -> None:
    """Error observed events capture sanitized failure categories."""
    service = AuditService()
    ev = await service.record_event(
        case_id="case_err_1",
        event_type=AuditEventType.ERROR_OBSERVED,
        actor=AuditActor.SYSTEM,
        payload={
            "error_category": "PROVIDER_TIMEOUT",
            "safe_code": "504_GATEWAY_TIMEOUT",
            "details": "Gateway timeout from simulated Razorpay stub",
        },
    )
    assert ev.event_type == AuditEventType.ERROR_OBSERVED
    assert ev.payload["error_category"] == "PROVIDER_TIMEOUT"
