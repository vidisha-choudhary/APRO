"""Internal Escalation Executor for the APRO Execution Framework."""

from datetime import UTC, datetime

from apro.domain.enums import ExecutionMode, ExecutionStatus, RecoveryActionType
from apro.execution.exceptions import ExecutionAuthorizationError
from apro.execution.interfaces import BaseExecutor
from apro.execution.models import (
    ApprovedExecutionRequest,
    ExecutionResult,
)


class EscalationExecutor(BaseExecutor):
    """Internal human-review escalation executor for ESCALATE actions."""

    @property
    def action_type(self) -> RecoveryActionType:
        return RecoveryActionType.ESCALATE

    @property
    def supported_modes(self) -> set[ExecutionMode]:
        return {ExecutionMode.INTERNAL, ExecutionMode.SIMULATION}

    def validate(self, request: ApprovedExecutionRequest) -> None:
        if request.execution_mode not in self.supported_modes:
            mode_val = request.execution_mode.value
            supp = [m.value for m in self.supported_modes]
            msg = (
                f"EscalationExecutor does not support mode '{mode_val}'. "
                f"Supported modes: {supp}."
            )
            raise ExecutionAuthorizationError(msg)

    async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
        self.validate(request)
        started_at = request.requested_at or datetime.now(UTC)
        completed_at = datetime.now(UTC)
        review_ref = f"esc_review_{request.case_id}_{request.execution_id[:8]}"

        return ExecutionResult(
            execution_id=request.execution_id,
            action_id=request.action_id,
            case_id=request.case_id,
            status=ExecutionStatus.SUCCEEDED,
            execution_mode=request.execution_mode,
            provider_reference=review_ref,
            error_code=None,
            error_message=None,
            started_at=started_at,
            completed_at=completed_at,
            executor_name="EscalationExecutor",
            metadata={
                "internal_action": "HUMAN_ESCALATION",
                "human_review_reference": review_ref,
                "reason": request.parameters.get(
                    "reason", "POLICY_DIRECTED_ESCALATION"
                ),
                "policy_decision_id": request.policy_decision_id,
            },
        )


__all__ = ["EscalationExecutor"]
