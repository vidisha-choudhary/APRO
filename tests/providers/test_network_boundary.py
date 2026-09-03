"""Tests verifying socket/network boundaries during execution."""

import socket
from datetime import UTC, datetime

import pytest

from apro.domain.enums import ExecutionMode, RecoveryActionType
from apro.execution.models import ApprovedExecutionRequest
from apro.providers.razorpay.adapter import RazorpayTestModePaymentLinkExecutor
from apro.providers.razorpay.client import RazorpayTestModeClient
from apro.providers.razorpay.config import RazorpayTestModeConfig
from apro.providers.razorpay.stub import DeterministicRazorpayStub


@pytest.mark.asyncio
async def test_zero_real_socket_connections_with_stub(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify stubbed execution triggers zero real OS socket connections."""
    socket_called = False

    def forbidden_socket(*_args: object, **_kwargs: object) -> None:
        nonlocal socket_called
        socket_called = True
        msg = "Forbidden OS socket connection attempted during stub execution"
        raise RuntimeError(msg)

    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    stub = DeterministicRazorpayStub()
    cfg = RazorpayTestModeConfig(
        key_id="rzp_test_mock_12345",
        key_secret="mock_secret_12345",
    )
    client = RazorpayTestModeClient(config=cfg, transport=stub)
    executor = RazorpayTestModePaymentLinkExecutor(client=client)

    now = datetime.now(UTC)
    req = ApprovedExecutionRequest(
        execution_id="exec_net_01",
        case_id="case_net_01",
        action_id="act_net_01",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        policy_decision_id="pol_net_01",
        idempotency_key="idem_net_01",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters={"amount": 50000},
        requested_at=now,
        policy_version="pol-v1",
        rule_set_version="rules-v1",
        action_schema_version="act-v1",
    )

    result = await executor.execute(req)
    assert result.status.value == "SUCCEEDED"
    assert not socket_called
