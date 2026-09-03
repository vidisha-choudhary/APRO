"""Integration tests for RecoveryLoopController orchestrating the multi-cycle
adaptive recovery loop.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.models import RecoveryDecision
from apro.diagnosis.models import DiagnosisResult
from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    OutcomeType,
    PaymentStatus,
    RecoveryCaseStatus,
)
from apro.domain.models import Execution, Payment, RecoveryCase
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.policy.engine import PolicyEngine
from apro.policy.enums import PolicyOutcome
from apro.recovery_loop.controller import RecoveryLoopController
from apro.recovery_loop.enums import EvidenceType, RecoveryLoopDisposition
from apro.recovery_loop.models import OutcomeEvidence
from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    PredictionUncertaintyState,
)
from apro.recovery_prediction.enums import (
    RecoveryAction as PredictorAction,
)
from apro.recovery_prediction.models import OutcomePrediction
from apro.simulation.enums import SimulatedActionType, SimulatedPaymentMethod


def _create_model_input(
    record_id: str = "rec_adapt_01", attempt_count: int = 1
) -> ModelInputRecord:
    now = datetime.now(UTC)
    features = FeatureSnapshot(
        feature_schema_version="feature-schema-v1",
        decision_timestamp=now.isoformat(),
        payment_id="pay_adapt_01",
        payment_amount=50000,
        currency="INR",
        payment_method=SimulatedPaymentMethod.CARD,
        attempt_count=attempt_count,
        failure_reason="insufficient_funds",
        failure_code="BAD_REQUEST",
        customer_id="cust_adapt_01",
        previous_payment_count=5,
        previous_success_count=4,
        previous_failure_count=attempt_count,
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
        record_id=record_id,
        dataset_type=DatasetType.BENCHMARK,
        dataset_version="dataset-v1",
        scenario_id="scen_adapt_01",
        generation_seed=42,
        scenario_version="v1",
        configuration_version="v1",
        feature_schema_version="feature-schema-v1",
        features=features,
    )


def _sample_predictions(
    model_input: ModelInputRecord,
    retry_prob: float = 0.8,
    plink_prob: float = 0.7,
) -> dict[PredictorAction, OutcomePrediction]:
    probs = {
        PredictorAction.RETRY: retry_prob,
        PredictorAction.PAYMENT_LINK: plink_prob,
        PredictorAction.OUTREACH: 0.5,
        PredictorAction.ESCALATE: 0.1,
        PredictorAction.STOP: 0.0,
    }
    preds: dict[PredictorAction, OutcomePrediction] = {}
    for act, p in probs.items():
        preds[act] = OutcomePrediction(
            prediction_id=f"pred_{act.value}",
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            action=act,
            model_name="model_b_test",
            model_version="outcome-v1",
            dataset_version=model_input.dataset_version,
            feature_schema_version=model_input.feature_schema_version,
            predicted_success_probability=p,
            predicted_outcome_state=(
                PredictedOutcomeState.SUCCESS
                if p > 0.5
                else PredictedOutcomeState.FAILURE
            ),
            predicted_recovered_amount=int(p * model_input.features.payment_amount),
            confidence=0.85,
            uncertainty_state=PredictionUncertaintyState.LOW_CONFIDENCE,
        )
    return preds


@pytest.mark.asyncio
async def test_full_adaptive_chain_and_phase_9_action_selection() -> None:
    """Primary E2E adaptive test:
    Action 1 (RETRY) Fails -> History Updated -> Re-evaluation -> Phase 9 called
    -> Phase 9 selects Action 2 (PAYMENT_LINK) -> Policy 2 ALLOWs -> Phase 11 Executes
    -> RECOVERED.
    """
    controller = RecoveryLoopController()
    orchestrator = ExecutionOrchestrator()
    policy_engine = PolicyEngine()
    decision_engine = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
    )

    now = datetime.now(UTC)
    payment = Payment(
        payment_id="pay_adapt_01",
        customer_id="cust_adapt_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_adapt_01",
        payment_id="pay_adapt_01",
        customer_id="cust_adapt_01",
        status=RecoveryCaseStatus.OBSERVING,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )
    base_model_input = _create_model_input("rec_adapt_01", attempt_count=1)

    # Spy to monitor Phase 9 decision engine invocations
    decision_calls: list[dict[str, Any]] = []
    real_decide = decision_engine.decide

    def decide_spy(
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None,
        outcome_predictions: dict[PredictorAction, OutcomePrediction],
        recovery_case_id: str,
    ) -> RecoveryDecision:
        res = real_decide(
            model_input=model_input,
            diagnosis_result=diagnosis_result,
            outcome_predictions=outcome_predictions,
            recovery_case_id=recovery_case_id,
        )
        decision_calls.append(
            {
                "model_input": model_input,
                "predictions": outcome_predictions,
                "decision": res,
            }
        )
        return res

    decision_engine.decide = decide_spy  # type: ignore

    # Step 1: Decision 1 from Phase 9 produces Action 1 (RETRY)
    preds1 = _sample_predictions(base_model_input, retry_prob=0.8, plink_prob=0.7)
    dec1 = decision_engine.decide(
        model_input=base_model_input,
        diagnosis_result=None,
        outcome_predictions=preds1,
        recovery_case_id=case.case_id,
    )
    assert dec1.selected_action == PredictorAction.RETRY

    # 1. Action 1 Execution Record
    exec1 = Execution(
        execution_id="exec_cycle_1",
        action_id="act_cycle_1",
        case_id="case_adapt_01",
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=now,
        completed_at=now,
    )

    # 2. Outcome 1 Evidence: FAILED
    ev1 = OutcomeEvidence(
        evidence_id="ev_cycle_1_fail",
        case_id="case_adapt_01",
        execution_id="exec_cycle_1",
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=now,
    )

    # Prediction provider that adjusts probabilities dynamically for Cycle 2
    def dynamic_predictions(
        mi: ModelInputRecord, _diag
    ) -> dict[PredictorAction, OutcomePrediction]:
        if mi.features.attempt_count > 1:
            return _sample_predictions(mi, retry_prob=0.1, plink_prob=0.85)
        return _sample_predictions(mi, retry_prob=0.8, plink_prob=0.7)

    # Execute Cycle 1 Outcome Processing & Trigger Adaptive Re-evaluation for Cycle 2
    (
        cycle_res,
        updated_case,
        updated_payment,
    ) = await controller.handle_outcome_and_cycle(
        evidence=ev1,
        case=case,
        payment=payment,
        base_model_input=base_model_input,
        execution=exec1,
        predictions_provider=dynamic_predictions,
        decision_engine=decision_engine,
        policy_engine=policy_engine,
        execution_orchestrator=orchestrator,
        execution_mode=ExecutionMode.SIMULATION,
        cycle_number=1,
        now=now,
    )

    # Verify Cycle 1 produced RE_EVALUATE disposition and invoked Phase 9
    assert cycle_res.outcome_result.disposition == RecoveryLoopDisposition.RE_EVALUATE
    # Verify Phase 9 was called at least twice, first with Action 1,
    # second with Action 2
    assert len(decision_calls) == 2
    assert decision_calls[0]["decision"].selected_action == PredictorAction.RETRY
    assert decision_calls[1]["decision"].selected_action == PredictorAction.PAYMENT_LINK

    # Verify second decision received fresh context containing prior failure
    assert decision_calls[1]["model_input"].features.attempt_count == 2
    assert decision_calls[1]["model_input"].features.previous_failure_count == 2

    # Verify Phase 9 produced Decision 2 for PAYMENT_LINK
    assert cycle_res.decision is not None
    assert cycle_res.decision.selected_action == PredictorAction.PAYMENT_LINK

    # Verify Phase 10 authorized Decision 2
    assert cycle_res.policy_decision is not None
    assert cycle_res.policy_decision.policy_outcome == PolicyOutcome.ALLOW

    # Verify Phase 11 executed Action 2
    assert cycle_res.execution_result is not None
    assert cycle_res.execution_result.status == ExecutionStatus.SUCCEEDED

    # 3. Outcome 2 Evidence: RECOVERED for Cycle 2 Execution
    ev2 = OutcomeEvidence(
        evidence_id="ev_cycle_2_rec",
        case_id="case_adapt_01",
        execution_id=cycle_res.execution_result.execution_id,
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=now,
    )

    cycle2_res, final_case, final_payment = await controller.handle_outcome_and_cycle(
        evidence=ev2,
        case=updated_case,
        payment=updated_payment,
        base_model_input=base_model_input,
        cycle_number=2,
        now=now,
    )

    # Verify Final Case is RECOVERED and terminal
    assert cycle2_res.outcome_result.disposition == RecoveryLoopDisposition.COMPLETE
    assert cycle2_res.outcome_result.outcome.type == OutcomeType.RECOVERED
    assert final_case.status == RecoveryCaseStatus.RECOVERED
    assert final_payment.status == PaymentStatus.CAPTURED
    assert final_case.closed_at is not None
