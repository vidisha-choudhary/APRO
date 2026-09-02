"""Simulation Payment Link Executor for the APRO Execution Framework."""

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


class SimulationPaymentLinkExecutor(BaseExecutor):
    """Provider-neutral simulation executor for PAYMENT_LINK recovery actions."""

    def __init__(self, config: SimulationExecutionConfig | None = None) -> None:
        self._config = config or SimulationExecutionConfig()

    @property
    def action_type(self) -> RecoveryActionType:
        return RecoveryActionType.ALTERNATE_RECOVERY

    @property
    def supported_modes(self) -> set[ExecutionMode]:
        return {ExecutionMode.SIMULATION}

    def validate(self, request: ApprovedExecutionRequest) -> None:
        if request.execution_mode not in self.supported_modes:
            mode_val = request.execution_mode.value
            supp = [m.value for m in self.supported_modes]
            msg = (
                f"SimulationPaymentLinkExecutor does not support mode '{mode_val}'. "
                f"Supported modes: {supp}."
            )
            raise ExecutionAuthorizationError(msg)

        expire_by = request.parameters.get("expire_by_minutes")
        if expire_by is not None and (
            not isinstance(expire_by, (int, float)) or expire_by <= 0
        ):
            msg = f"Invalid expire_by_minutes '{expire_by}'; must be positive."
            raise ExecutionValidationError(msg)

    async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
        self.validate(request)
        started_at = request.requested_at or datetime.now(UTC)
        completed_at = datetime.now(UTC)

        status = self._config.simulated_status
        ref = (
            self._config.simulated_provider_reference
            or f"plink_sim_{request.execution_id}"
        )
        err_code = self._config.simulated_error_code
        err_msg = self._config.simulated_error_message

        if status == ExecutionStatus.FAILED and not err_code:
            err_code = "SIMULATED_PAYMENT_LINK_CREATION_FAILED"
            err_msg = err_msg or "Simulated payment link creation failed."
        elif status == ExecutionStatus.UNKNOWN and not err_code:
            err_code = "SIMULATED_PAYMENT_LINK_TIMEOUT"
            err_msg = (
                err_msg or "Simulated gateway response timeout during link creation."
            )

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
            executor_name="SimulationPaymentLinkExecutor",
            metadata={
                "simulated": True,
                "action": request.action_type.value,
                "short_url": (
                    f"https://rzp.io/i/sim_{request.execution_id}"
                    if status == ExecutionStatus.SUCCEEDED
                    else None
                ),
            },
        )


__all__ = ["SimulationPaymentLinkExecutor"]
