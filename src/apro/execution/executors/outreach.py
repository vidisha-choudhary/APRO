"""Simulation Outreach Executor for the APRO Execution Framework."""

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


class SimulationOutreachExecutor(BaseExecutor):
    """Provider-neutral simulation executor for OUTREACH interventions."""

    def __init__(self, config: SimulationExecutionConfig | None = None) -> None:
        self._config = config or SimulationExecutionConfig()

    @property
    def action_type(self) -> RecoveryActionType:
        return RecoveryActionType.OUTREACH

    @property
    def supported_modes(self) -> set[ExecutionMode]:
        return {ExecutionMode.SIMULATION}

    def validate(self, request: ApprovedExecutionRequest) -> None:
        if request.execution_mode not in self.supported_modes:
            mode_val = request.execution_mode.value
            supp = [m.value for m in self.supported_modes]
            msg = (
                f"SimulationOutreachExecutor does not support mode '{mode_val}'. "
                f"Supported modes: {supp}."
            )
            raise ExecutionAuthorizationError(msg)

        channel = request.parameters.get("channel", "sms")
        if channel not in ("sms", "email", "whatsapp", "in_app"):
            msg = f"Unsupported outreach channel '{channel}'."
            raise ExecutionValidationError(msg)

    async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
        self.validate(request)
        started_at = request.requested_at or datetime.now(UTC)
        completed_at = datetime.now(UTC)

        status = self._config.simulated_status
        ref = (
            self._config.simulated_provider_reference
            or f"sim_outreach_{request.execution_id}"
        )
        err_code = self._config.simulated_error_code
        err_msg = self._config.simulated_error_message
        channel = request.parameters.get("channel", "sms")
        msg_template = request.parameters.get(
            "message", "Payment recovery notice: please update payment method."
        )

        if status == ExecutionStatus.FAILED and not err_code:
            err_code = "SIMULATED_OUTREACH_DELIVERY_FAILED"
            err_msg = err_msg or "Simulated customer message delivery failed."
        elif status == ExecutionStatus.UNKNOWN and not err_code:
            err_code = "SIMULATED_OUTREACH_TIMEOUT"
            err_msg = err_msg or "Simulated messaging carrier timeout."

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
            executor_name="SimulationOutreachExecutor",
            metadata={
                "simulated": True,
                "action": request.action_type.value,
                "channel": channel,
                "message": msg_template,
                "delivery_status": (
                    "DELIVERED"
                    if status == ExecutionStatus.SUCCEEDED
                    else "UNDELIVERED"
                ),
            },
        )


__all__ = ["SimulationOutreachExecutor"]
