"""Unit tests for the Executor Registry and routing."""

import pytest

from apro.domain.enums import ExecutionMode, RecoveryActionType
from apro.execution.exceptions import ExecutorNotFoundError
from apro.execution.executors.escalation import EscalationExecutor
from apro.execution.executors.noop import NoOpExecutor
from apro.execution.executors.outreach import SimulationOutreachExecutor
from apro.execution.executors.payment_link import SimulationPaymentLinkExecutor
from apro.execution.executors.retry import SimulationRetryExecutor
from apro.execution.registry import (
    DEFAULT_EXECUTOR_REGISTRY,
    ExecutorRegistry,
    build_default_executor_registry,
)


def test_default_executor_registry_routes():
    """Verify DEFAULT_EXECUTOR_REGISTRY routes all supported actions and modes."""
    registry = DEFAULT_EXECUTOR_REGISTRY

    # Retry
    retry_exec = registry.get(RecoveryActionType.RETRY, ExecutionMode.SIMULATION)
    assert isinstance(retry_exec, SimulationRetryExecutor)

    # Payment Link
    plink_exec = registry.get("PAYMENT_LINK", ExecutionMode.SIMULATION)
    assert isinstance(plink_exec, SimulationPaymentLinkExecutor)
    alt_exec = registry.get(
        RecoveryActionType.ALTERNATE_RECOVERY, ExecutionMode.SIMULATION
    )
    assert isinstance(alt_exec, SimulationPaymentLinkExecutor)

    # Outreach
    outreach_exec = registry.get(RecoveryActionType.OUTREACH, ExecutionMode.SIMULATION)
    assert isinstance(outreach_exec, SimulationOutreachExecutor)

    # Escalation
    esc_exec = registry.get(RecoveryActionType.ESCALATE, ExecutionMode.INTERNAL)
    assert isinstance(esc_exec, EscalationExecutor)

    # Stop
    stop_exec = registry.get(RecoveryActionType.STOP, ExecutionMode.INTERNAL)
    assert isinstance(stop_exec, NoOpExecutor)


def test_registry_unsupported_action_raises_error():
    """Verify unsupported action fails closed with ExecutorNotFoundError."""
    registry = build_default_executor_registry()
    with pytest.raises(ExecutorNotFoundError, match="No executor registered"):
        registry.get("UNKNOWN_ACTION", ExecutionMode.SIMULATION)


def test_registry_unsupported_mode_raises_error():
    """Verify unsupported mode fails closed with ExecutorNotFoundError."""
    registry = build_default_executor_registry()
    with pytest.raises(ExecutorNotFoundError, match="No executor registered"):
        # RAZORPAY_TEST_MODE has no concrete provider registered in Phase 11
        registry.get(RecoveryActionType.RETRY, ExecutionMode.RAZORPAY_TEST_MODE)


def test_registry_duplicate_registration_conflict():
    """Verify registering duplicate without override raises ValueError."""
    registry = ExecutorRegistry()
    registry.register(SimulationRetryExecutor())
    with pytest.raises(ValueError, match="Conflicting executor registration"):
        registry.register(SimulationRetryExecutor())
