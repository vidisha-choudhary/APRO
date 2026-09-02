"""Simulation Retry Executor for the APRO Execution Framework."""

from datetime import UTC, datetime

from apro.domain.enums import ExecutionMode, ExecutionStatus, RecoveryActionType
from apro.execution.exceptions import (
    ExecutionAuthorizationError,
    ExecutionValidationError,
)
from apro.execution.interfaces import BaseExecutor
from apro.execution.models import (
    ApprovedExecutionRequest,
    ExecutionResult,
    SimulationExecutionConfig,
)


class SimulationRetryExecutor(BaseExecutor):
    """Provider-neutral simulation executor for RETRY recovery actions."""

    def __init__(self, config: SimulationExecutionConfig | None = None) -> None:
        self._config = config or SimulationExecutionConfig()

    @property
    def action_type(self) -> RecoveryActionType:
        return RecoveryActionType.RETRY

    @property
    def supported_modes(self) -> set[ExecutionMode]:
        return {ExecutionMode.SIMULATION}

    def validate(self, request: ApprovedExecutionRequest) -> None:
        if request.execution_mode not in self.supported_modes:
            mode_val = request.execution_mode.value
            supp = [m.value for m in self.supported_modes]
            msg = (
                f"SimulationRetryExecutor does not support mode '{mode_val}'. "
                f"Supported modes: {supp}."
            )
            raise ExecutionAuthorizationError(msg)

        delay = request.parameters.get("retry_delay_seconds")
        if delay is not None and (not isinstance(delay, (int, float)) or delay < 0):
            msg = f"Invalid retry_delay_seconds '{delay}'; must be non-negative."
            raise ExecutionValidationError(msg)

    async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
        self.validate(request)
        started_at = request.requested_at or datetime.now(UTC)
        completed_at = datetime.now(UTC)

        status = self._config.simulated_status
        ref = (
            self._config.simulated_provider_reference
            or f"sim_retry_{request.execution_id}"
        )
        err_code = self._config.simulated_error_code
        err_msg = self._config.simulated_error_message

        if status == ExecutionStatus.FAILED and not err_code:
            err_code = "SIMULATED_RETRY_FAILURE"
            err_msg = err_msg or "Simulated payment retry declined by issuer."
        elif status == ExecutionStatus.UNKNOWN and not err_code:
            err_code = "SIMULATED_RETRY_TIMEOUT"
            err_msg = err_msg or "Simulated gateway response timeout after dispatch."

        return ExecutionResult(
            execution_id=request.execution_id,
            action_id=request.action_id,
            case_id=request.case_id,
            status=status,
            execution_mode=request.execution_mode,
            provider_reference=ref if status != ExecutionStatus.FAILED else None,
            error_code=err_code,
            error_message=err_msg,
            started_at=started_at,
            completed_at=completed_at,
            executor_name="SimulationRetryExecutor",
            metadata={
                "simulated": True,
                "action": request.action_type.value,
                "retry_delay_seconds": request.parameters.get("retry_delay_seconds", 0),
            },
        )


__all__ = ["SimulationRetryExecutor"]
