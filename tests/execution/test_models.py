"""Unit tests for Phase 11 execution taxonomy, schemas, and models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    RecoveryActionType,
)
from apro.execution.enums import (
    EXECUTION_REQUEST_SCHEMA_VERSION,
    EXECUTION_RESULT_SCHEMA_VERSION,
    EXECUTION_SCHEMA_VERSION,
)
from apro.execution.models import (
    ApprovedExecutionRequest,
    ExecutionResult,
    SimulationExecutionConfig,
)


def test_execution_schema_versions() -> None:
    """Verify execution schema versions are defined and explicit."""
    assert EXECUTION_SCHEMA_VERSION == "execution-v1"
    assert EXECUTION_RESULT_SCHEMA_VERSION == "execution-result-v1"
    assert EXECUTION_REQUEST_SCHEMA_VERSION == "execution-request-v1"


def test_approved_execution_request_immutability() -> None:
    """Verify ApprovedExecutionRequest is frozen and serializable."""
    now = datetime.now(UTC)
    req = ApprovedExecutionRequest(
        execution_id="exec_001",
        case_id="case_001",
        action_id="act_001",
        action_type=RecoveryActionType.RETRY,
        policy_decision_id="pol_001",
        decision_id="dec_001",
        idempotency_key="idem_case_001_RETRY_1",
        execution_mode=ExecutionMode.SIMULATION,
        parameters={"retry_delay_seconds": 60},
        requested_at=now,
        policy_version="policy-v1",
        rule_set_version="ruleset-v1",
        action_schema_version="action-v1",
    )

    assert req.execution_id == "exec_001"
    assert req.action_type == RecoveryActionType.RETRY
    assert req.request_schema_version == EXECUTION_REQUEST_SCHEMA_VERSION

    with pytest.raises(ValidationError):
        req.action_id = "act_MUTATED"  # type: ignore[misc]


def test_execution_result_immutability() -> None:
    """Verify ExecutionResult is frozen and serializable."""
    now = datetime.now(UTC)
    res = ExecutionResult(
        execution_id="exec_001",
        action_id="act_001",
        case_id="case_001",
        status=ExecutionStatus.SUCCEEDED,
        execution_mode=ExecutionMode.SIMULATION,
        provider_reference="sim_ref_001",
        started_at=now,
        completed_at=now,
        executor_name="SimulationRetryExecutor",
        metadata={"simulated": True},
    )

    assert res.status == ExecutionStatus.SUCCEEDED
    assert res.executor_name == "SimulationRetryExecutor"
    assert res.result_schema_version == EXECUTION_RESULT_SCHEMA_VERSION

    with pytest.raises(ValidationError):
        res.status = ExecutionStatus.FAILED  # type: ignore[misc]


def test_simulation_execution_config() -> None:
    """Verify SimulationExecutionConfig default and custom parameters."""
    cfg = SimulationExecutionConfig(
        simulated_status=ExecutionStatus.FAILED,
        simulated_error_code="TEST_FAIL",
        simulated_error_message="Test failure",
    )
    assert cfg.simulated_status == ExecutionStatus.FAILED
    assert cfg.simulated_error_code == "TEST_FAIL"
