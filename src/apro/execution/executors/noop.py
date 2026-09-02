"""Internal No-Op Executor for STOP actions in the APRO Execution Framework."""

from datetime import UTC, datetime

from apro.domain.enums import ExecutionMode, ExecutionStatus, RecoveryActionType
from apro.execution.exceptions import ExecutionAuthorizationError
from apro.execution.interfaces import BaseExecutor
from apro.execution.models import (
    ApprovedExecutionRequest,
    ExecutionResult,
)


class NoOpExecutor(BaseExecutor):
    """Internal non-intervention executor for STOP recovery decisions."""

    @property
    def action_type(self) -> RecoveryActionType:
        return RecoveryActionType.STOP

    @property
    def supported_modes(self) -> set[ExecutionMode]:
        return {ExecutionMode.INTERNAL, ExecutionMode.SIMULATION}

    def validate(self, request: ApprovedExecutionRequest) -> None:
        if request.execution_mode not in self.supported_modes:
            msg = (
                f"NoOpExecutor does not support mode '{request.execution_mode.value}'. "
                f"Supported modes: {[m.value for m in self.supported_modes]}."
            )
            raise ExecutionAuthorizationError(msg)

    async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
        self.validate(request)
        started_at = request.requested_at or datetime.now(UTC)
        completed_at = datetime.now(UTC)
        noop_ref = f"noop_{request.case_id}_{request.execution_id[:8]}"

        return ExecutionResult(
            execution_id=request.execution_id,
            action_id=request.action_id,
            case_id=request.case_id,
            status=ExecutionStatus.SUCCEEDED,
            execution_mode=request.execution_mode,
            provider_reference=noop_ref,
            error_code=None,
            error_message=None,
            started_at=started_at,
            completed_at=completed_at,
            executor_name="NoOpExecutor",
            metadata={
                "internal_action": "NO_OP_STOP",
                "stop_reason": request.parameters.get(
                    "stop_reason", "POLICY_DIRECTED_STOP"
                ),
                "policy_decision_id": request.policy_decision_id,
            },
        )


__all__ = ["NoOpExecutor"]
