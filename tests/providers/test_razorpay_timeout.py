"""Tests for timeout and ambiguous transport handling in Razorpay adapter."""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import ExecutionMode, ExecutionStatus, RecoveryActionType
from apro.execution.models import ApprovedExecutionRequest
from apro.providers.razorpay.adapter import RazorpayTestModePaymentLinkExecutor
from apro.providers.razorpay.client import RazorpayTestModeClient
from apro.providers.razorpay.config import RazorpayTestModeConfig
from apro.providers.razorpay.stub import DeterministicRazorpayStub


@pytest.mark.asyncio
async def test_provider_timeout_maps_to_unknown_without_blind_retry() -> None:
    """Verify transport timeout returns ExecutionStatus.UNKNOWN."""
    stub = DeterministicRazorpayStub(should_timeout=True)
    cfg = RazorpayTestModeConfig(
        key_id="rzp_test_mock_12345",
        key_secret="mock_secret_12345",
        timeout_seconds=2.0,
    )
    client = RazorpayTestModeClient(config=cfg, transport=stub)
    executor = RazorpayTestModePaymentLinkExecutor(client=client)

    now = datetime.now(UTC)
    req = ApprovedExecutionRequest(
        execution_id="exec_timeout_01",
        case_id="case_timeout_01",
        action_id="act_timeout_01",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        policy_decision_id="pol_timeout_01",
        idempotency_key="idem_timeout_01",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters={"amount": 50000},
        requested_at=now,
        policy_version="pol-v1",
        rule_set_version="rules-v1",
        action_schema_version="act-v1",
    )

    result = await executor.execute(req)

    assert result.status == ExecutionStatus.UNKNOWN
    assert result.error_code == "PROVIDER_TIMEOUT"
    assert "timed out" in (result.error_message or "")
