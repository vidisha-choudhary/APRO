"""Disposition resolver for APRO Phase 13 Recovery Loop."""

from apro.domain.enums import (
    OutcomeType,
    PaymentStatus,
)
from apro.domain.models import Outcome, Payment, RecoveryCase
from apro.recovery_loop.enums import (
    LoopTerminationReason,
    RecoveryLoopDisposition,
)
from apro.recovery_loop.guards import LoopSafetyGuard
from apro.recovery_loop.models import ActionHistoryRecord


class DispositionResolver:
    """Deterministically resolves control disposition based on outcome evidence,
    case state, and safety guards.
    """

    def __init__(self, safety_guard: LoopSafetyGuard | None = None) -> None:
        self.safety_guard = safety_guard or LoopSafetyGuard()

    def resolve(
        self,
        outcome: Outcome,
        case: RecoveryCase,
        payment: Payment,
        history: tuple[ActionHistoryRecord, ...] | list[ActionHistoryRecord],
        cycle_number: int,
    ) -> tuple[RecoveryLoopDisposition, LoopTerminationReason | None]:
        """Resolve next loop disposition from outcome and current case state.

        Returns:
            (disposition, termination_reason)
        """
        # 1. Successful Recovery
        if (
            outcome.type == OutcomeType.RECOVERED
            or payment.status == PaymentStatus.CAPTURED
        ):
            return (
                RecoveryLoopDisposition.COMPLETE,
                LoopTerminationReason.RECOVERY_CONFIRMED,
            )

        # 2. Pending outcome: wait for definitive evidence, zero new action
        if outcome.type == OutcomeType.PENDING:
            return RecoveryLoopDisposition.WAIT_FOR_OUTCOME, None

        # 3. Explicit STOP outcome
        if outcome.type == OutcomeType.STOPPED:
            return RecoveryLoopDisposition.STOP, LoopTerminationReason.EXPLICIT_STOP

        # 4. Explicit Escalation outcome
        if outcome.type == OutcomeType.ESCALATED:
            return (
                RecoveryLoopDisposition.ESCALATE,
                LoopTerminationReason.HUMAN_ESCALATION_REQUIRED,
            )

        # 5. Expiration outcome
        if outcome.type == OutcomeType.EXPIRED:
            return RecoveryLoopDisposition.STOP, LoopTerminationReason.CASE_EXPIRED

        # 6. Failed recovery outcome -> Check safety bounds for re-evaluation
        if outcome.type == OutcomeType.FAILED:
            can_continue, termination_reason = self.safety_guard.evaluate_loop_bounds(
                case=case,
                payment=payment,
                history=history,
                cycle_number=cycle_number,
            )

            if not can_continue:
                if (
                    termination_reason
                    == LoopTerminationReason.HUMAN_ESCALATION_REQUIRED
                ):
                    return RecoveryLoopDisposition.ESCALATE, termination_reason
                return RecoveryLoopDisposition.STOP, termination_reason

            return RecoveryLoopDisposition.RE_EVALUATE, None

        # Fallback conservative termination
        return RecoveryLoopDisposition.STOP, LoopTerminationReason.UNRECOVERABLE_FAILURE
