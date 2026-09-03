"""Action and outcome history service for APRO Phase 13 Recovery Loop."""

from datetime import datetime

from apro.domain.enums import (
    ExecutionStatus,
    OutcomeType,
    RecoveryActionType,
)
from apro.domain.models import Execution, Outcome, RecoveryAction
from apro.persistence.unit_of_work import UnitOfWork
from apro.policy.models import ActionExecutionHistory
from apro.recovery_loop.models import ActionHistoryRecord
from apro.recovery_prediction.enums import RecoveryAction as PolicyRecoveryAction


class ActionHistoryService:
    """Provides history extraction and policy-compatible history containers."""

    @staticmethod
    def build_history_from_records(
        actions: list[RecoveryAction],
        executions: list[Execution],
        outcomes: list[Outcome],
    ) -> tuple[ActionHistoryRecord, ...]:
        """Aggregate existing domain action, execution, and outcome records
        into history.
        """
        # Index executions by action_id
        exec_by_action: dict[str, Execution] = {e.action_id: e for e in executions}
        # Index outcomes by execution_id
        outcome_by_exec: dict[str, Outcome] = {o.execution_id: o for o in outcomes}

        # Sort actions by created_at
        sorted_actions = sorted(actions, key=lambda a: a.created_at)

        history_items: list[ActionHistoryRecord] = []
        for idx, act in enumerate(sorted_actions, start=1):
            execution = exec_by_action.get(act.action_id)
            outcome = outcome_by_exec.get(execution.execution_id) if execution else None

            rec = ActionHistoryRecord(
                action_id=act.action_id,
                action_type=act.action_type,
                execution_id=execution.execution_id if execution else None,
                execution_status=execution.status if execution else None,
                outcome_type=outcome.type if outcome else None,
                amount_recovered=outcome.amount_recovered if outcome else 0,
                observed_at=outcome.observed_at
                if outcome
                else (
                    execution.completed_at
                    if execution and execution.completed_at
                    else act.updated_at
                ),
                attempt_order=idx,
                provider_reference=execution.provider_reference
                if execution
                else act.provider_reference,
            )
            history_items.append(rec)

        return tuple(history_items)

    async def get_case_history(
        self, case_id: str, uow: UnitOfWork
    ) -> tuple[ActionHistoryRecord, ...]:
        """Query existing domain persistence records to construct authoritative
        history.
        """
        actions = await uow.recovery_actions.find_by_case_id(case_id)
        executions = await uow.executions.find_by_case_id(case_id)
        outcomes = await uow.outcomes.find_by_case_id(case_id)
        return self.build_history_from_records(actions, executions, outcomes)

    @staticmethod
    def build_policy_execution_history(
        history: tuple[ActionHistoryRecord, ...] | list[ActionHistoryRecord],
    ) -> ActionExecutionHistory:
        """Convert history into Phase 10 ActionExecutionHistory container."""
        retry_count = 0
        payment_link_count = 0
        total_interventions = 0
        last_retry_at: datetime | None = None
        last_action: PolicyRecoveryAction | None = None
        same_action_count = 0

        for item in history:
            # Map domain action type to policy recovery action
            if item.action_type == RecoveryActionType.ALTERNATE_RECOVERY:
                pol_action = PolicyRecoveryAction.PAYMENT_LINK
            else:
                try:
                    pol_action = PolicyRecoveryAction(item.action_type.value)
                except ValueError:
                    pol_action = None

            if item.action_type == RecoveryActionType.RETRY:
                retry_count += 1
                last_retry_at = item.observed_at
                total_interventions += 1
            elif item.action_type == RecoveryActionType.ALTERNATE_RECOVERY:
                payment_link_count += 1
                total_interventions += 1
            elif item.action_type == RecoveryActionType.OUTREACH:
                total_interventions += 1

            if pol_action is not None:
                if last_action == pol_action:
                    same_action_count += 1
                else:
                    same_action_count = 1
                last_action = pol_action

        return ActionExecutionHistory(
            retry_count=retry_count,
            last_retry_at=last_retry_at,
            same_action_count=same_action_count,
            last_action=last_action,
            total_interventions=total_interventions,
            payment_link_count=payment_link_count,
        )

    @staticmethod
    def get_failed_action_types(
        history: tuple[ActionHistoryRecord, ...] | list[ActionHistoryRecord],
    ) -> set[RecoveryActionType]:
        """Return the set of action types that resulted in FAILED outcome."""
        failed = set()
        for item in history:
            if (
                item.outcome_type == OutcomeType.FAILED
                or item.execution_status == ExecutionStatus.FAILED
            ):
                failed.add(item.action_type)
        return failed
