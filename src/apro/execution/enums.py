"""Execution framework enums and schema versions."""

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    RecoveryActionStatus,
    RecoveryActionType,
)

EXECUTION_SCHEMA_VERSION = "execution-v1"
EXECUTION_RESULT_SCHEMA_VERSION = "execution-result-v1"
EXECUTION_REQUEST_SCHEMA_VERSION = "execution-request-v1"

__all__ = [
    "EXECUTION_REQUEST_SCHEMA_VERSION",
    "EXECUTION_RESULT_SCHEMA_VERSION",
    "EXECUTION_SCHEMA_VERSION",
    "ExecutionMode",
    "ExecutionStatus",
    "RecoveryActionStatus",
    "RecoveryActionType",
]
