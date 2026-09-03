"""Safety and boundedness guards for APRO Phase 13 Recovery Loop."""

from apro.domain.enums import (
    PaymentStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Payment, RecoveryCase
from apro.recovery_loop.enums import LoopTerminationReason
from apro.recovery_loop.exceptions import (
    CaptureRaceDetectedError,
    TerminalCaseReopenError,
    UnboundedLoopError,
)
from apro.recovery_loop.models import ActionHistoryRecord

_TERMINAL_CASE_STATUSES = {
    RecoveryCaseStatus.RECOVERED,
    RecoveryCaseStatus.STOPPED,
    RecoveryCaseStatus.ESCALATED,
}

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MAX_INTERVENTIONS = 3
DEFAULT_MAX_SAME_ACTION_CONSECUTIVE = 1
HARD_CEILING_LOOP_CYCLES = 10


class LoopSafetyGuard:
    """Enforces safety invariants, terminal state protection, and loop boundedness."""

    def __init__(
        self,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        max_interventions: int = DEFAULT_MAX_INTERVENTIONS,
        max_same_action_consecutive: int = DEFAULT_MAX_SAME_ACTION_CONSECUTIVE,
        hard_cycle_ceiling: int = HARD_CEILING_LOOP_CYCLES,
    ) -> None:
        self.max_attempts = max_attempts
        self.max_interventions = max_interventions
        self.max_same_action_consecutive = max_same_action_consecutive
        self.hard_cycle_ceiling = hard_cycle_ceiling

    def check_terminal_case(self, case: RecoveryCase) -> None:
        """Verify that a recovery case is not already in a terminal state."""
        if case.status in _TERMINAL_CASE_STATUSES:
            msg = (
                f"RecoveryCase '{case.case_id}' is in terminal state '{case.status}' "
                "and cannot re-enter the recovery loop."
            )
            raise TerminalCaseReopenError(msg)

    def check_payment_capture_race(self, payment: Payment) -> None:
        """Verify that payment is not already captured before attempting execution."""
        if payment.status == PaymentStatus.CAPTURED:
            msg = (
                f"Payment '{payment.payment_id}' is CAPTURED. "
                "Further recovery execution is strictly prohibited."
            )
            raise CaptureRaceDetectedError(msg)

    def evaluate_loop_bounds(
        self,
        case: RecoveryCase,
        payment: Payment,
        history: list[ActionHistoryRecord] | tuple[ActionHistoryRecord, ...],
        cycle_number: int,
    ) -> tuple[bool, LoopTerminationReason | None]:
        """Check whether the recovery loop must terminate based on bounded safety
        limits.

        Returns:
            (can_continue, termination_reason)
        """
        # Hard cycle ceiling
        if cycle_number > self.hard_cycle_ceiling:
            msg = (
                f"RecoveryCase '{case.case_id}' exceeded hard cycle ceiling "
                f"({cycle_number} > {self.hard_cycle_ceiling})."
            )
            raise UnboundedLoopError(msg)

        # 1. Payment already captured
        if payment.status == PaymentStatus.CAPTURED:
            return False, LoopTerminationReason.RECOVERY_CONFIRMED

        # 2. Case already in terminal state
        if case.status in _TERMINAL_CASE_STATUSES:
            if case.status == RecoveryCaseStatus.RECOVERED:
                return False, LoopTerminationReason.RECOVERY_CONFIRMED
            if case.status == RecoveryCaseStatus.ESCALATED:
                return False, LoopTerminationReason.HUMAN_ESCALATION_REQUIRED
            return False, LoopTerminationReason.EXPLICIT_STOP

        # 3. Attempt count limits
        attempt_count = len([h for h in history if h.execution_id is not None])
        if (
            attempt_count >= self.max_attempts
            or case.current_attempt_count >= self.max_attempts
        ):
            return False, LoopTerminationReason.ATTEMPT_LIMIT_EXCEEDED

        # 4. Total interventions limit
        intervention_count = len(
            [
                h
                for h in history
                if h.action_type
                in (
                    RecoveryActionType.RETRY,
                    RecoveryActionType.ALTERNATE_RECOVERY,
                    RecoveryActionType.OUTREACH,
                )
            ]
        )
        if intervention_count >= self.max_interventions:
            return False, LoopTerminationReason.INTERVENTION_LIMIT_EXCEEDED

        return True, None

    def check_same_action_repetition(
        self,
        proposed_action: RecoveryActionType,
        history: list[ActionHistoryRecord] | tuple[ActionHistoryRecord, ...],
    ) -> bool:
        """Check whether the proposed action violates same-action consecutive
        repetition limits.

        Returns True if repetition is allowed, False if prohibited.
        """
        if not history:
            return True

        # Count consecutive occurrences of proposed_action from the tail of history
        consecutive_count = 0
        for item in reversed(history):
            if item.action_type == proposed_action:
                consecutive_count += 1
            else:
                break

        return consecutive_count < self.max_same_action_consecutive
