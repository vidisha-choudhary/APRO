"""Immutable execution request, result, and configuration models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    RecoveryActionType,
)
from apro.execution.enums import (
    EXECUTION_REQUEST_SCHEMA_VERSION,
    EXECUTION_RESULT_SCHEMA_VERSION,
)


class ApprovedExecutionRequest(BaseModel):
    """Immutable execution request representing authorized action dispatch."""

    model_config = ConfigDict(frozen=True)

    execution_id: str
    case_id: str
    action_id: str
    action_type: RecoveryActionType
    policy_decision_id: str
    decision_id: str | None = None
    idempotency_key: str
    execution_mode: ExecutionMode
    parameters: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime
    policy_version: str
    rule_set_version: str
    action_schema_version: str
    request_schema_version: str = Field(default=EXECUTION_REQUEST_SCHEMA_VERSION)
    approval_reference: str | None = None


class ExecutionResult(BaseModel):
    """Immutable execution outcome record returned by an executor."""

    model_config = ConfigDict(frozen=True)

    execution_id: str
    action_id: str
    case_id: str
    status: ExecutionStatus
    execution_mode: ExecutionMode
    provider_reference: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    executor_name: str
    result_schema_version: str = Field(default=EXECUTION_RESULT_SCHEMA_VERSION)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimulationExecutionConfig(BaseModel):
    """Configuration for deterministic simulation executors."""

    model_config = ConfigDict(frozen=True)

    simulated_status: ExecutionStatus = ExecutionStatus.SUCCEEDED
    simulated_provider_reference: str | None = None
    simulated_error_code: str | None = None
    simulated_error_message: str | None = None
    seed: int | None = None


__all__ = [
    "ApprovedExecutionRequest",
    "ExecutionResult",
    "SimulationExecutionConfig",
]
