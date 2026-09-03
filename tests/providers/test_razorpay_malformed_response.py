"""Tests for malformed JSON and unexpected response handling."""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import ExecutionMode, ExecutionStatus, RecoveryActionType
from apro.execution.models import ApprovedExecutionRequest
from apro.providers.razorpay.adapter import RazorpayTestModePaymentLinkExecutor
from apro.providers.razorpay.client import RazorpayTestModeClient
from apro.providers.razorpay.config import RazorpayTestModeConfig
from apro.providers.razorpay.stub import DeterministicRazorpayStub


@pytest.mark.asyncio
async def test_malformed_json_response_handling() -> None:
    """Verify non-JSON response returns UNKNOWN with PROVIDER_MALFORMED_RESPONSE."""
    stub = DeterministicRazorpayStub(
        simulated_status_code=200,
        simulated_body="<html><body>502 Bad Gateway</body></html>",
    )
    cfg = RazorpayTestModeConfig(
        key_id="rzp_test_mock_12345",
        key_secret="mock_secret_12345",
    )
    client = RazorpayTestModeClient(config=cfg, transport=stub)
    executor = RazorpayTestModePaymentLinkExecutor(client=client)

    now = datetime.now(UTC)
    req = ApprovedExecutionRequest(
        execution_id="exec_malformed_01",
        case_id="case_malformed_01",
        action_id="act_malformed_01",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        policy_decision_id="pol_malformed_01",
        idempotency_key="idem_malformed_01",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters={"amount": 50000},
        requested_at=now,
        policy_version="pol-v1",
        rule_set_version="rules-v1",
        action_schema_version="act-v1",
    )

    result = await executor.execute(req)

    assert result.status == ExecutionStatus.UNKNOWN
    assert result.error_code == "PROVIDER_MALFORMED_RESPONSE"
