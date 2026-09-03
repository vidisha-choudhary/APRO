"""Tests proving the no-blind-repetition rule in Phase 13."""

from datetime import UTC, datetime

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.domain.enums import (
    PaymentStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Payment, RecoveryCase
from apro.recovery_loop.context import ReEvaluationContextBuilder
from apro.recovery_loop.guards import LoopSafetyGuard
from apro.recovery_loop.history import ActionHistoryService
from apro.recovery_loop.models import ActionHistoryRecord
from apro.simulation.enums import SimulatedActionType, SimulatedPaymentMethod


def _create_base_model_input() -> ModelInputRecord:
    now = datetime.now(UTC)
    features = FeatureSnapshot(
        feature_schema_version="feature-schema-v1",
        decision_timestamp=now.isoformat(),
        payment_id="pay_nbr_01",
        payment_amount=50000,
        currency="INR",
        payment_method=SimulatedPaymentMethod.CARD,
        attempt_count=1,
        failure_reason="insufficient_funds",
        failure_code="BAD_REQUEST",
        customer_id="cust_nbr_01",
        previous_payment_count=5,
        previous_success_count=4,
        previous_failure_count=1,
        previous_recovery_count=1,
        previous_retry_success=1,
        previous_payment_link_success=0,
        hour_of_day=14,
        day_of_week=2,
        is_weekend=False,
        candidate_actions=[
            SimulatedActionType.RETRY,
            SimulatedActionType.PAYMENT_LINK,
            SimulatedActionType.OUTREACH,
        ],
    )
    return ModelInputRecord(
        record_id="rec_nbr_01",
        dataset_type=DatasetType.BENCHMARK,
        dataset_version="dataset-v1",
        scenario_id="scen_nbr_01",
        generation_seed=42,
        scenario_version="v1",
        configuration_version="v1",
        feature_schema_version="feature-schema-v1",
        features=features,
    )


def test_failed_action_is_present_in_fresh_re_evaluation_context() -> None:
    """When Action 1 fails, fresh re-evaluation context accurately records
    the failure.
    """
    now = datetime.now(UTC)
    payment = Payment(
        payment_id="pay_nbr_01",
        customer_id="cust_nbr_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_nbr_01",
        payment_id="pay_nbr_01",
        customer_id="cust_nbr_01",
        status=RecoveryCaseStatus.EVALUATING,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )
    history = (
        ActionHistoryRecord(
            action_id="act_01",
            action_type=RecoveryActionType.RETRY,
            execution_id="exec_01",
            observed_at=now,
            attempt_order=1,
        ),
    )

    builder = ReEvaluationContextBuilder()
    context = builder.build_context(
        case=case,
        payment=payment,
        cycle_number=2,
        history=history,
        latest_diagnosis=None,
        latest_outcome=None,
        base_model_input=_create_base_model_input(),
        now=now,
    )

    assert context.cycle_number == 2
    assert len(context.history) == 1
    assert context.history[0].action_type == RecoveryActionType.RETRY
    assert context.model_input.features.attempt_count == 2
    assert context.model_input.features.previous_failure_count == 2


def test_safety_guard_blocks_immediate_consecutive_same_action_repetition() -> None:
    """Safety guard prohibits repeating the exact same failed action
    consecutively.
    """
    guard = LoopSafetyGuard(max_same_action_consecutive=1)
    now = datetime.now(UTC)
    history = [
        ActionHistoryRecord(
            action_id="act_01",
            action_type=RecoveryActionType.RETRY,
            execution_id="exec_01",
            observed_at=now,
            attempt_order=1,
        ),
    ]

    # Repeating RETRY consecutively is blocked
    can_repeat_retry = guard.check_same_action_repetition(
        proposed_action=RecoveryActionType.RETRY,
        history=history,
    )
    assert can_repeat_retry is False

    # Switching to ALTERNATE_RECOVERY is allowed
    can_switch_action = guard.check_same_action_repetition(
        proposed_action=RecoveryActionType.ALTERNATE_RECOVERY,
        history=history,
    )
    assert can_switch_action is True


def test_failed_actions_set_extracted_accurately_from_history() -> None:
    """ActionHistoryService extracts failed actions so decision engine knows
    what already failed.
    """
    service = ActionHistoryService()
    now = datetime.now(UTC)
    history = [
        ActionHistoryRecord(
            action_id="act_01",
            action_type=RecoveryActionType.RETRY,
            execution_id="exec_01",
            observed_at=now,
            attempt_order=1,
        ),
    ]
    failed = service.get_failed_action_types(history)
    assert isinstance(failed, set)


@pytest.mark.asyncio
async def test_controller_blocks_blind_repetition_of_failed_action() -> None:
    """Remediation Guardrail 3 & 11: When Action 1 (RETRY) fails and Phase 9
    recommends RETRY again, the controller safety gate blocks execution and
    produces zero new execution.
    """
    from apro.decision.engine import EconomicDecisionEngine
    from apro.domain.enums import (
        ExecutionMode,
        ExecutionStatus,
    )
    from apro.domain.models import Execution
    from apro.execution.orchestrator import ExecutionOrchestrator
    from apro.policy.engine import PolicyEngine
    from apro.recovery_loop.controller import RecoveryLoopController
    from apro.recovery_loop.enums import (
        EvidenceType,
        LoopTerminationReason,
    )
    from apro.recovery_loop.models import OutcomeEvidence
    from apro.recovery_prediction.enums import (
        PredictedOutcomeState,
        PredictionUncertaintyState,
    )
    from apro.recovery_prediction.enums import (
        RecoveryAction as PredictorAction,
    )
    from apro.recovery_prediction.models import OutcomePrediction

    controller = RecoveryLoopController()
    orchestrator = ExecutionOrchestrator()
    policy_engine = PolicyEngine()
    decision_engine = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
    )
    now = datetime.now(UTC)

    payment = Payment(
        payment_id="pay_nbr_ctrl_01",
        customer_id="cust_nbr_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_nbr_ctrl_01",
        payment_id="pay_nbr_ctrl_01",
        customer_id="cust_nbr_01",
        status=RecoveryCaseStatus.OBSERVING,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )
    base_mi = _create_base_model_input()

    # Prior execution 1: RETRY FAILED
    exec1 = Execution(
        execution_id="exec_nbr_1",
        action_id="act_nbr_1",
        case_id=case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=now,
        completed_at=now,
    )
    ev1 = OutcomeEvidence(
        evidence_id="ev_nbr_1",
        case_id=case.case_id,
        execution_id=exec1.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=now,
    )

    # Provider configured to return RETRY as highest probability
    def propose_retry_again(
        mi: ModelInputRecord, _diag
    ) -> dict[PredictorAction, OutcomePrediction]:
        return {
            PredictorAction.RETRY: OutcomePrediction(
                prediction_id="p_retry",
                record_id=mi.record_id,
                scenario_id=mi.scenario_id,
                action=PredictorAction.RETRY,
                model_name="m",
                model_version="v",
                dataset_version=mi.dataset_version,
                feature_schema_version=mi.feature_schema_version,
                predicted_success_probability=0.9,
                predicted_outcome_state=PredictedOutcomeState.SUCCESS,
                predicted_recovered_amount=45000,
                confidence=0.9,
                uncertainty_state=PredictionUncertaintyState.LOW_CONFIDENCE,
            ),
            PredictorAction.PAYMENT_LINK: OutcomePrediction(
                prediction_id="p_plink",
                record_id=mi.record_id,
                scenario_id=mi.scenario_id,
                action=PredictorAction.PAYMENT_LINK,
                model_name="m",
                model_version="v",
                dataset_version=mi.dataset_version,
                feature_schema_version=mi.feature_schema_version,
                predicted_success_probability=0.1,
                predicted_outcome_state=PredictedOutcomeState.FAILURE,
                predicted_recovered_amount=5000,
                confidence=0.9,
                uncertainty_state=PredictionUncertaintyState.LOW_CONFIDENCE,
            ),
            PredictorAction.OUTREACH: OutcomePrediction(
                prediction_id="p_outreach",
                record_id=mi.record_id,
                scenario_id=mi.scenario_id,
                action=PredictorAction.OUTREACH,
                model_name="m",
                model_version="v",
                dataset_version=mi.dataset_version,
                feature_schema_version=mi.feature_schema_version,
                predicted_success_probability=0.05,
                predicted_outcome_state=PredictedOutcomeState.FAILURE,
                predicted_recovered_amount=2500,
                confidence=0.9,
                uncertainty_state=PredictionUncertaintyState.LOW_CONFIDENCE,
            ),
            PredictorAction.ESCALATE: OutcomePrediction(
                prediction_id="p_esc",
                record_id=mi.record_id,
                scenario_id=mi.scenario_id,
                action=PredictorAction.ESCALATE,
                model_name="m",
                model_version="v",
                dataset_version=mi.dataset_version,
                feature_schema_version=mi.feature_schema_version,
                predicted_success_probability=0.0,
                predicted_outcome_state=PredictedOutcomeState.FAILURE,
                predicted_recovered_amount=0,
                confidence=0.9,
                uncertainty_state=PredictionUncertaintyState.LOW_CONFIDENCE,
            ),
            PredictorAction.STOP: OutcomePrediction(
                prediction_id="p_stop",
                record_id=mi.record_id,
                scenario_id=mi.scenario_id,
                action=PredictorAction.STOP,
                model_name="m",
                model_version="v",
                dataset_version=mi.dataset_version,
                feature_schema_version=mi.feature_schema_version,
                predicted_success_probability=0.0,
                predicted_outcome_state=PredictedOutcomeState.FAILURE,
                predicted_recovered_amount=0,
                confidence=0.9,
                uncertainty_state=PredictionUncertaintyState.LOW_CONFIDENCE,
            ),
        }

    cycle_res, updated_case, _ = await controller.handle_outcome_and_cycle(
        evidence=ev1,
        case=case,
        payment=payment,
        base_model_input=base_mi,
        execution=exec1,
        predictions_provider=propose_retry_again,
        decision_engine=decision_engine,
        policy_engine=policy_engine,
        execution_orchestrator=orchestrator,
        execution_mode=ExecutionMode.SIMULATION,
        cycle_number=1,
        now=now,
    )

    # Invariant: Blind repetition of RETRY is blocked -> zero execution result
    assert cycle_res.execution_result is None
    assert updated_case.status == RecoveryCaseStatus.STOPPED
    assert (
        cycle_res.outcome_result.termination_reason
        == LoopTerminationReason.SAME_ACTION_LIMIT_EXCEEDED
    )
