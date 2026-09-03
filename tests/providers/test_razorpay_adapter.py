"""Tests for Razorpay TEST mode executors."""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import ExecutionMode, ExecutionStatus, RecoveryActionType
from apro.execution.exceptions import ExecutionAuthorizationError
from apro.execution.models import ApprovedExecutionRequest
from apro.providers.razorpay.adapter import (
    RazorpayTestModeOutreachExecutor,
    RazorpayTestModePaymentLinkExecutor,
)
from apro.providers.razorpay.client import RazorpayTestModeClient
from apro.providers.razorpay.config import RazorpayTestModeConfig
from apro.providers.razorpay.stub import DeterministicRazorpayStub


@pytest.fixture
def stub_client() -> tuple[RazorpayTestModeClient, DeterministicRazorpayStub]:
    stub = DeterministicRazorpayStub()
    cfg = RazorpayTestModeConfig(
        key_id="rzp_test_mock_12345",
        key_secret="mock_secret_12345",
    )
    client = RazorpayTestModeClient(config=cfg, transport=stub)
    return client, stub


@pytest.mark.asyncio
async def test_payment_link_executor_success(
    stub_client: tuple[RazorpayTestModeClient, DeterministicRazorpayStub],
) -> None:
    """Verify Payment Link executor succeeds and returns valid ExecutionResult."""
    client, stub = stub_client
    executor = RazorpayTestModePaymentLinkExecutor(client=client)

    now = datetime.now(UTC)
    req = ApprovedExecutionRequest(
        execution_id="exec_adapter_01",
        case_id="case_adapter_01",
        action_id="act_adapter_01",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        policy_decision_id="pol_adapter_01",
        idempotency_key="idem_adapter_01",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters={"amount": 60000, "customer_name": "Test Customer"},
        requested_at=now,
        policy_version="pol-v1",
        rule_set_version="rules-v1",
        action_schema_version="act-v1",
    )

    executor.validate(req)
    result = await executor.execute(req)

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.provider_reference is not None
    assert result.provider_reference.startswith("plink_stub_")
    assert result.metadata["amount"] == 60000
    assert "short_url" in result.metadata
    assert len(stub.recorded_requests) == 1


@pytest.mark.asyncio
async def test_payment_link_executor_unsupported_mode_raises_error(
    stub_client: tuple[RazorpayTestModeClient, DeterministicRazorpayStub],
) -> None:
    """Verify simulation mode raises ExecutionAuthorizationError."""
    client, _ = stub_client
    executor = RazorpayTestModePaymentLinkExecutor(client=client)

    now = datetime.now(UTC)
    req = ApprovedExecutionRequest(
        execution_id="exec_adapter_02",
        case_id="case_adapter_02",
        action_id="act_adapter_02",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        policy_decision_id="pol_adapter_02",
        idempotency_key="idem_adapter_02",
        execution_mode=ExecutionMode.SIMULATION,
        parameters={"amount": 60000},
        requested_at=now,
        policy_version="pol-v1",
        rule_set_version="rules-v1",
        action_schema_version="act-v1",
    )

    with pytest.raises(ExecutionAuthorizationError):
        executor.validate(req)


@pytest.mark.asyncio
async def test_outreach_executor_success(
    stub_client: tuple[RazorpayTestModeClient, DeterministicRazorpayStub],
) -> None:
    """Verify Outreach executor succeeds and returns valid ExecutionResult."""
    client, stub = stub_client
    executor = RazorpayTestModeOutreachExecutor(client=client)

    now = datetime.now(UTC)
    req = ApprovedExecutionRequest(
        execution_id="exec_adapter_03",
        case_id="case_adapter_03",
        action_id="act_adapter_03",
        action_type=RecoveryActionType.OUTREACH,
        policy_decision_id="pol_adapter_03",
        idempotency_key="idem_adapter_03",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters={"payment_link_id": "plink_stub_123456", "medium": "sms"},
        requested_at=now,
        policy_version="pol-v1",
        rule_set_version="rules-v1",
        action_schema_version="act-v1",
    )

    executor.validate(req)
    result = await executor.execute(req)

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.provider_reference == "plink_stub_123456"
    assert result.metadata["delivery_status"] == "DELIVERED"
    assert len(stub.recorded_requests) == 1
