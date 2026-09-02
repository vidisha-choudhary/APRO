"""APRO Phase 11 — Execution Framework."""

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    RecoveryActionStatus,
    RecoveryActionType,
)
from apro.execution.enums import (
    EXECUTION_REQUEST_SCHEMA_VERSION,
    EXECUTION_RESULT_SCHEMA_VERSION,
    EXECUTION_SCHEMA_VERSION,
)
from apro.execution.exceptions import (
    ExecutionAuthorizationError,
    ExecutionError,
    ExecutionStateError,
    ExecutionValidationError,
    ExecutorNotFoundError,
    IdempotencyConflictError,
)
from apro.execution.executors import (
    EscalationExecutor,
    NoOpExecutor,
    SimulationOutreachExecutor,
    SimulationPaymentLinkExecutor,
    SimulationRetryExecutor,
)
from apro.execution.interfaces import BaseExecutor
from apro.execution.models import (
    ApprovedExecutionRequest,
    ExecutionResult,
    SimulationExecutionConfig,
)
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.execution.registry import (
    DEFAULT_EXECUTOR_REGISTRY,
    ExecutorRegistry,
    build_default_executor_registry,
)
from apro.execution.validation import (
    FORBIDDEN_SECRET_KEYS,
    build_approved_execution_request,
    validate_execution_preconditions,
    validate_parameter_secrets,
    validate_policy_authorization,
)

__all__ = [
    "DEFAULT_EXECUTOR_REGISTRY",
    "EXECUTION_REQUEST_SCHEMA_VERSION",
    "EXECUTION_RESULT_SCHEMA_VERSION",
    "EXECUTION_SCHEMA_VERSION",
    "FORBIDDEN_SECRET_KEYS",
    "ApprovedExecutionRequest",
    "BaseExecutor",
    "EscalationExecutor",
    "ExecutionAuthorizationError",
    "ExecutionError",
    "ExecutionMode",
    "ExecutionOrchestrator",
    "ExecutionResult",
    "ExecutionStateError",
    "ExecutionStatus",
    "ExecutionValidationError",
    "ExecutorNotFoundError",
    "ExecutorRegistry",
    "IdempotencyConflictError",
    "NoOpExecutor",
    "RecoveryActionStatus",
    "RecoveryActionType",
    "SimulationExecutionConfig",
    "SimulationOutreachExecutor",
    "SimulationPaymentLinkExecutor",
    "SimulationRetryExecutor",
    "build_approved_execution_request",
    "build_default_executor_registry",
    "validate_execution_preconditions",
    "validate_parameter_secrets",
    "validate_policy_authorization",
]
