"""Unit tests for individual executors."""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    RecoveryActionType,
)
from apro.execution.exceptions import (
    ExecutionValidationError,
)
from apro.execution.executors.escalation import EscalationExecutor
from apro.execution.executors.noop import NoOpExecutor
from apro.execution.executors.outreach import SimulationOutreachExecutor
from apro.execution.executors.payment_link import SimulationPaymentLinkExecutor
from apro.execution.executors.retry import SimulationRetryExecutor
from apro.execution.models import (
    ApprovedExecutionRequest,
    SimulationExecutionConfig,
)


def _make_req(
    action_type: RecoveryActionType,
    mode: ExecutionMode,
    parameters: dict | None = None,
) -> ApprovedExecutionRequest:
    now = datetime.now(UTC)
    return ApprovedExecutionRequest(
        execution_id="exec_test_01",
        case_id="case_test_01",
        action_id="act_test_01",
        action_type=action_type,
        policy_decision_id="pol_test_01",
        idempotency_key="idem_test_01",
        execution_mode=mode,
        parameters=parameters or {},
        requested_at=now,
        policy_version="policy-v1",
        rule_set_version="ruleset-v1",
        action_schema_version="action-v1",
    )


@pytest.mark.asyncio
async def test_simulation_retry_executor_success():
    """Verify SimulationRetryExecutor produces expected SUCCEEDED result."""
    executor = SimulationRetryExecutor()
    req = _make_req(
        RecoveryActionType.RETRY, ExecutionMode.SIMULATION, {"retry_delay_seconds": 10}
    )
    result = await executor.execute(req)

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.provider_reference == "sim_retry_exec_test_01"
    assert result.executor_name == "SimulationRetryExecutor"
    assert result.metadata["simulated"] is True


@pytest.mark.asyncio
async def test_simulation_retry_executor_simulated_failure():
    """Verify SimulationRetryExecutor supports simulated failure configuration."""
    cfg = SimulationExecutionConfig(simulated_status=ExecutionStatus.FAILED)
    executor = SimulationRetryExecutor(config=cfg)
    req = _make_req(RecoveryActionType.RETRY, ExecutionMode.SIMULATION)
    result = await executor.execute(req)

    assert result.status == ExecutionStatus.FAILED
    assert result.error_code == "SIMULATED_RETRY_FAILURE"
    assert result.provider_reference is None


@pytest.mark.asyncio
async def test_simulation_payment_link_executor_success():
    """Verify SimulationPaymentLinkExecutor produces simulated payment link."""
    executor = SimulationPaymentLinkExecutor()
    req = _make_req(RecoveryActionType.ALTERNATE_RECOVERY, ExecutionMode.SIMULATION)
    result = await executor.execute(req)

    assert result.status == ExecutionStatus.SUCCEEDED
    assert "plink_sim_" in (result.provider_reference or "")
    assert "https://rzp.io/i/sim_" in (result.metadata.get("short_url") or "")


@pytest.mark.asyncio
async def test_simulation_outreach_executor_channels():
    """Verify SimulationOutreachExecutor handles outreach channels."""
    executor = SimulationOutreachExecutor()
    req = _make_req(
        RecoveryActionType.OUTREACH,
        ExecutionMode.SIMULATION,
        {"channel": "whatsapp", "message": "Hi, please retry your payment."},
    )
    result = await executor.execute(req)

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.metadata["channel"] == "whatsapp"
    assert result.metadata["delivery_status"] == "DELIVERED"


@pytest.mark.asyncio
async def test_simulation_outreach_executor_invalid_channel():
    """Verify SimulationOutreachExecutor rejects unsupported channels."""
    executor = SimulationOutreachExecutor()
    req = _make_req(
        RecoveryActionType.OUTREACH,
        ExecutionMode.SIMULATION,
        {"channel": "carrier_pigeon"},
    )
    with pytest.raises(ExecutionValidationError, match="Unsupported outreach channel"):
        await executor.execute(req)


@pytest.mark.asyncio
async def test_escalation_executor():
    """Verify EscalationExecutor generates human-review reference."""
    executor = EscalationExecutor()
    req = _make_req(RecoveryActionType.ESCALATE, ExecutionMode.INTERNAL)
    result = await executor.execute(req)

    assert result.status == ExecutionStatus.SUCCEEDED
    assert "esc_review_" in (result.provider_reference or "")
    assert result.metadata["internal_action"] == "HUMAN_ESCALATION"


@pytest.mark.asyncio
async def test_noop_executor():
    """Verify NoOpExecutor generates non-intervention stop record."""
    executor = NoOpExecutor()
    req = _make_req(RecoveryActionType.STOP, ExecutionMode.INTERNAL)
    result = await executor.execute(req)

    assert result.status == ExecutionStatus.SUCCEEDED
    assert "noop_" in (result.provider_reference or "")
    assert result.metadata["internal_action"] == "NO_OP_STOP"
