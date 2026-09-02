"""Deterministic Executor Registry for the APRO Execution Framework."""

from typing import Any

from apro.domain.enums import ExecutionMode, RecoveryActionType
from apro.execution.exceptions import ExecutorNotFoundError
from apro.execution.executors.escalation import EscalationExecutor
from apro.execution.executors.noop import NoOpExecutor
from apro.execution.executors.outreach import SimulationOutreachExecutor
from apro.execution.executors.payment_link import SimulationPaymentLinkExecutor
from apro.execution.executors.retry import SimulationRetryExecutor
from apro.execution.interfaces import BaseExecutor
from apro.recovery_prediction.enums import RecoveryAction


def _normalize_action_key(action: RecoveryActionType | RecoveryAction | str) -> str:
    """Normalize action string or enum to a canonical action key."""
    val = action.value if hasattr(action, "value") else str(action)
    val = val.upper()
    if val in ("PAYMENT_LINK", "ALTERNATE_RECOVERY"):
        return "PAYMENT_LINK"
    return val


def _normalize_mode(mode: ExecutionMode | str) -> ExecutionMode:
    """Normalize mode string or enum to canonical ExecutionMode."""
    if isinstance(mode, ExecutionMode):
        return mode
    return ExecutionMode(str(mode).upper())


class ExecutorRegistry:
    """Deterministic routing registry for recovery action executors."""

    def __init__(self) -> None:
        self._registry: dict[tuple[str, ExecutionMode], BaseExecutor] = {}

    def register(self, executor: BaseExecutor, override: bool = False) -> None:
        """Register an executor for its supported action and execution modes."""
        action_key = _normalize_action_key(executor.action_type)
        for mode in executor.supported_modes:
            norm_mode = _normalize_mode(mode)
            key = (action_key, norm_mode)
            if key in self._registry and not override:
                msg = (
                    f"Conflicting executor registration for key {key}: "
                    "already registered."
                )
                raise ValueError(msg)
            self._registry[key] = executor

            # Also register ALTERNATE_RECOVERY alias if action is PAYMENT_LINK
            if action_key == "PAYMENT_LINK":
                alt_key = ("ALTERNATE_RECOVERY", norm_mode)
                self._registry[alt_key] = executor

    def get(
        self,
        action_type: RecoveryActionType | RecoveryAction | str,
        mode: ExecutionMode | str,
    ) -> BaseExecutor:
        """Resolve an executor for an action and mode.

        Raises:
            ExecutorNotFoundError: If no executor is registered for action and mode.
        """
        try:
            norm_mode = _normalize_mode(mode)
        except ValueError as exc:
            msg = f"Unsupported execution mode '{mode}'."
            raise ExecutorNotFoundError(msg) from exc

        action_key = _normalize_action_key(action_type)
        key = (action_key, norm_mode)
        executor = self._registry.get(key)
        if executor is None:
            msg = (
                f"No executor registered for action '{action_key}' "
                f"and mode '{norm_mode.value}'. Execution fails closed."
            )
            raise ExecutorNotFoundError(msg)
        return executor

    def has_executor(
        self,
        action_type: RecoveryActionType | RecoveryAction | str,
        mode: ExecutionMode | str,
    ) -> bool:
        """Check if an executor is registered for the action and mode."""
        try:
            norm_mode = _normalize_mode(mode)
            action_key = _normalize_action_key(action_type)
            return (action_key, norm_mode) in self._registry
        except ValueError:
            return False

    def list_registered(self) -> list[dict[str, Any]]:
        """List all currently registered (action, mode) pairs and executor names."""
        return [
            {
                "action": action,
                "mode": mode.value,
                "executor": type(exec_obj).__name__,
            }
            for (action, mode), exec_obj in self._registry.items()
        ]


def build_default_executor_registry() -> ExecutorRegistry:
    """Construct default registry pre-populated with standard executors."""
    registry = ExecutorRegistry()
    registry.register(SimulationRetryExecutor())
    registry.register(SimulationPaymentLinkExecutor())
    registry.register(SimulationOutreachExecutor())
    registry.register(EscalationExecutor())
    registry.register(NoOpExecutor())
    return registry


DEFAULT_EXECUTOR_REGISTRY = build_default_executor_registry()

__all__ = [
    "DEFAULT_EXECUTOR_REGISTRY",
    "ExecutorRegistry",
    "build_default_executor_registry",
]
