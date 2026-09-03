"""Unit tests for ActionHistoryService in Phase 13."""

from datetime import UTC, datetime

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    OutcomeType,
    RecoveryActionStatus,
    RecoveryActionType,
)
from apro.domain.models import Execution, Outcome, RecoveryAction
from apro.recovery_loop.history import ActionHistoryService
from apro.recovery_prediction.enums import RecoveryAction as PolicyRecoveryAction


def test_history_extraction_and_policy_container_mapping() -> None:
    service = ActionHistoryService()
    now = datetime.now(UTC)

    actions = [
        RecoveryAction(
            action_id="act_01",
            case_id="case_hist_01",
            action_type=RecoveryActionType.RETRY,
            status=RecoveryActionStatus.COMPLETED,
            created_at=now,
            updated_at=now,
            execution_mode=ExecutionMode.SIMULATION,
        ),
        RecoveryAction(
            action_id="act_02",
            case_id="case_hist_01",
            action_type=RecoveryActionType.ALTERNATE_RECOVERY,
            status=RecoveryActionStatus.COMPLETED,
            created_at=now,
            updated_at=now,
            execution_mode=ExecutionMode.SIMULATION,
        ),
    ]

    executions = [
        Execution(
            execution_id="exec_01",
            action_id="act_01",
            case_id="case_hist_01",
            execution_type="RETRY",
            execution_mode=ExecutionMode.SIMULATION,
            status=ExecutionStatus.FAILED,
            started_at=now,
            completed_at=now,
        ),
        Execution(
            execution_id="exec_02",
            action_id="act_02",
            case_id="case_hist_01",
            execution_type="ALTERNATE_RECOVERY",
            execution_mode=ExecutionMode.SIMULATION,
            status=ExecutionStatus.SUCCEEDED,
            started_at=now,
            completed_at=now,
        ),
    ]

    outcomes = [
        Outcome(
            outcome_id="out_01",
            case_id="case_hist_01",
            execution_id="exec_01",
            type=OutcomeType.FAILED,
            amount_recovered=0,
            observed_at=now,
        ),
        Outcome(
            outcome_id="out_02",
            case_id="case_hist_01",
            execution_id="exec_02",
            type=OutcomeType.RECOVERED,
            amount_recovered=50000,
            observed_at=now,
        ),
    ]

    history = service.build_history_from_records(actions, executions, outcomes)
    assert len(history) == 2
    assert history[0].action_type == RecoveryActionType.RETRY
    assert history[0].outcome_type == OutcomeType.FAILED
    assert history[1].action_type == RecoveryActionType.ALTERNATE_RECOVERY
    assert history[1].outcome_type == OutcomeType.RECOVERED

    # Test failed action extraction
    failed_actions = service.get_failed_action_types(history)
    assert RecoveryActionType.RETRY in failed_actions
    assert RecoveryActionType.ALTERNATE_RECOVERY not in failed_actions

    # Test policy history mapping
    pol_history = service.build_policy_execution_history(history)
    assert pol_history.retry_count == 1
    assert pol_history.payment_link_count == 1
    assert pol_history.total_interventions == 2
    assert pol_history.last_action == PolicyRecoveryAction.PAYMENT_LINK
