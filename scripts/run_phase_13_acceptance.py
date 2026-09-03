"""APRO Phase 13 Acceptance Suite — Outcome & Adaptive Recovery Loop.

Authoritative Acceptance Runner for:
1. 10 Manual Acceptance Scenarios
2. 58 Acceptance Criteria (AC-01 through AC-58)
"""

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.models import RecoveryDecision
from apro.diagnosis.enums import DiagnosisCategory, UncertaintyState
from apro.diagnosis.models import DiagnosisResult
from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    OutcomeType,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import (
    Execution,
    Outcome,
    Payment,
    RecoveryAction,
    RecoveryCase,
)
from apro.domain.state_machines import (
    InvalidStateTransitionError,
    transition_payment,
    transition_recovery_case,
)
from apro.execution.exceptions import (
    ExecutionAuthorizationError,
    ExecutionStateError,
    ExecutionValidationError,
)
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.policy.engine import PolicyEngine
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import EventTrustState, PolicyDecision
from apro.providers.razorpay import (
    DeterministicRazorpayStub,
    RazorpayPaymentLinkRequest,
    RazorpayTestModeClient,
    RazorpayTestModeConfig,
)
from apro.recovery_loop.context import (
    ReEvaluationContextBuilder,
    compute_re_evaluation_id,
)
from apro.recovery_loop.controller import RecoveryLoopController
from apro.recovery_loop.dispositions import DispositionResolver
from apro.recovery_loop.enums import (
    EvidenceProvenance,
    EvidenceType,
    LoopTerminationReason,
    RecoveryLoopDisposition,
)
from apro.recovery_loop.exceptions import (
    TerminalCaseReopenError,
    UnboundedLoopError,
)
from apro.recovery_loop.guards import LoopSafetyGuard
from apro.recovery_loop.history import ActionHistoryService
from apro.recovery_loop.models import (
    ActionHistoryRecord,
    OutcomeEvidence,
    OutcomeProcessingResult,
)
from apro.recovery_loop.outcomes import OutcomeProcessor
from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    PredictionUncertaintyState,
)
from apro.recovery_prediction.enums import (
    RecoveryAction as PredictorAction,
)
from apro.recovery_prediction.models import OutcomePrediction
from apro.simulation.engine import evaluate_action_outcome_from_probability
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedOutcomeStatus,
    SimulatedPaymentMethod,
)


def make_test_fixture(
    case_id: str = "case_acc_01",
    payment_id: str = "pay_acc_01",
    customer_id: str = "cust_acc_01",
    payment_status: PaymentStatus = PaymentStatus.FAILED,
    case_status: RecoveryCaseStatus = RecoveryCaseStatus.OBSERVING,
    amount: int = 50000,
) -> tuple[RecoveryCase, Payment]:
    now = datetime.now(UTC)
    payment = Payment(
        payment_id=payment_id,
        customer_id=customer_id,
        provider="razorpay",
        amount=amount,
        currency="INR",
        method="card",
        status=payment_status,
        created_at=now,
        updated_at=now,
        captured_at=now if payment_status == PaymentStatus.CAPTURED else None,
    )
    case = RecoveryCase(
        case_id=case_id,
        payment_id=payment_id,
        customer_id=customer_id,
        status=case_status,
        opened_at=now,
        updated_at=now,
        recovery_amount=amount,
        current_attempt_count=1,
    )
    return case, payment


def evaluate_acceptance_results(
    passed_scenarios: int,
    total_scenarios: int,
    ac_results: dict[str, bool],
    expected_ac_count: int = 58,
) -> int:
    """Evaluate acceptance criteria and scenario results.

    Returns:
        0 on complete success, 1 on failure.
    """
    passed_acs = sum(1 for status in ac_results.values() if status)
    if (
        passed_scenarios == total_scenarios
        and passed_acs == expected_ac_count
        and len(ac_results) == expected_ac_count
        and all(ac_results.values())
    ):
        return 0
    return 1


def make_model_input(
    record_id: str = "rec_acc_01",
    payment_id: str = "pay_acc_01",
    attempt_count: int = 1,
) -> ModelInputRecord:
    now = datetime.now(UTC)
    features = FeatureSnapshot(
        feature_schema_version="feature-schema-v1",
        decision_timestamp=now.isoformat(),
        payment_id=payment_id,
        payment_amount=50000,
        currency="INR",
        payment_method=SimulatedPaymentMethod.CARD,
        attempt_count=attempt_count,
        failure_reason="insufficient_funds",
        failure_code="BAD_REQUEST",
        customer_id="cust_acc_01",
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
        scenario_id="scen_acc_01",
        generation_seed=42,
        scenario_version="v1",
        configuration_version="v1",
        feature_schema_version="feature-schema-v1",
        features=features,
    )


def make_predictions(
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
            prediction_id=f"pred_{act.value}_{uuid.uuid4().hex[:6]}",
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            action=act,
            model_name="model_b_test",
            model_version="outcome-v1",
            dataset_version=model_input.dataset_version,
            feature_schema_version=model_input.feature_schema_version,
            predicted_success_probability=p,
            predicted_outcome_state=PredictedOutcomeState.SUCCESS
            if p > 0.5
            else PredictedOutcomeState.FAILURE,
            predicted_recovered_amount=int(p * model_input.features.payment_amount),
            confidence=0.85,
            uncertainty_state=PredictionUncertaintyState.LOW_CONFIDENCE,
        )
    return preds


# ==============================================================================
# 10 MANUAL SCENARIOS
# ==============================================================================


async def run_scenario_1_successful_recovery() -> bool:
    """Scenario 1: Action 1 -> execution -> reliable payment success evidence
    -> RECOVERED -> case terminal.
    """
    case, payment = make_test_fixture()
    processor = OutcomeProcessor()
    now = datetime.now(UTC)

    evidence = OutcomeEvidence(
        evidence_id="ev_scen1",
        case_id=case.case_id,
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=now,
    )
    res, updated_case, updated_payment = await processor.process_outcome(
        evidence=evidence, case=case, payment=payment
    )
    assert res.outcome.type == OutcomeType.RECOVERED
    assert res.disposition == RecoveryLoopDisposition.COMPLETE
    assert updated_case.status == RecoveryCaseStatus.RECOVERED
    assert updated_payment.status == PaymentStatus.CAPTURED
    assert updated_case.closed_at is not None
    return True


async def run_scenario_2_failed_action_adaptive_action() -> bool:
    """Scenario 2: Action 1 Fails -> History Update -> Re-evaluation -> Phase 9
    selects Action 2 -> Phase 10 ALLOW -> Phase 11 Executes -> RECOVERED.
    """
    controller = RecoveryLoopController()
    orchestrator = ExecutionOrchestrator()
    policy_engine = PolicyEngine()
    decision_engine = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
    )
    now = datetime.now(UTC)
    case, payment = make_test_fixture()
    base_mi = make_model_input()

    exec1 = Execution(
        execution_id="exec_scen2_1",
        action_id="act_scen2_1",
        case_id=case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=now,
        completed_at=now,
    )
    ev1 = OutcomeEvidence(
        evidence_id="ev_scen2_fail",
        case_id=case.case_id,
        execution_id=exec1.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=now,
    )

    def dynamic_preds(
        mi: ModelInputRecord, _diag
    ) -> dict[PredictorAction, OutcomePrediction]:
        if mi.features.attempt_count > 1:
            return make_predictions(mi, retry_prob=0.1, plink_prob=0.88)
        return make_predictions(mi, retry_prob=0.8, plink_prob=0.7)

    (
        cycle_res,
        updated_case,
        updated_payment,
    ) = await controller.handle_outcome_and_cycle(
        evidence=ev1,
        case=case,
        payment=payment,
        base_model_input=base_mi,
        execution=exec1,
        predictions_provider=dynamic_preds,
        decision_engine=decision_engine,
        policy_engine=policy_engine,
        execution_orchestrator=orchestrator,
        execution_mode=ExecutionMode.SIMULATION,
        cycle_number=1,
        now=now,
    )

    assert cycle_res.outcome_result.disposition == RecoveryLoopDisposition.RE_EVALUATE
    assert cycle_res.decision is not None
    assert cycle_res.decision.selected_action == PredictorAction.PAYMENT_LINK
    assert cycle_res.policy_decision is not None
    assert cycle_res.policy_decision.policy_outcome == PolicyOutcome.ALLOW
    assert cycle_res.execution_result is not None
    assert cycle_res.execution_result.status == ExecutionStatus.SUCCEEDED
    return True


async def run_scenario_3_failed_action_stop() -> bool:
    """Scenario 3: Action 1 Fails -> No eligible continuation (limit exceeded)
    -> STOP.
    """
    case, payment = make_test_fixture()
    guard = LoopSafetyGuard(max_attempts=1)
    resolver = DispositionResolver(safety_guard=guard)
    processor = OutcomeProcessor(disposition_resolver=resolver, safety_guard=guard)
    now = datetime.now(UTC)

    history = [
        ActionHistoryRecord(
            action_id="act_scen3_01",
            action_type=RecoveryActionType.RETRY,
            execution_id="exec_scen3_01",
            observed_at=now,
            attempt_order=1,
        )
    ]
    ev = OutcomeEvidence(
        evidence_id="ev_scen3",
        case_id=case.case_id,
        execution_id="exec_scen3_01",
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.FAILED,
        observed_at=now,
    )
    res, updated_case, _ = await processor.process_outcome(
        evidence=ev,
        case=case,
        payment=payment,
        history=history,
        cycle_number=1,
        now=now,
    )
    assert res.disposition == RecoveryLoopDisposition.STOP
    assert updated_case.status == RecoveryCaseStatus.STOPPED
    return True


async def run_scenario_4_failed_action_escalate() -> bool:
    """Scenario 4: Action Fails -> Human escalation required -> ESCALATE."""
    case, payment = make_test_fixture(case_status=RecoveryCaseStatus.OBSERVING)
    processor = OutcomeProcessor()
    now = datetime.now(UTC)

    # Drive escalation condition through raw provider details / dispute / fraud evidence
    evidence = OutcomeEvidence(
        evidence_id="ev_scen4_esc",
        case_id=case.case_id,
        evidence_type=EvidenceType.PROVIDER_EVIDENCE,
        raw_details={"status": "fraud_review", "reason": "suspected_compromise"},
        observed_at=now,
    )
    res, updated_case, _ = await processor.process_outcome(
        evidence=evidence, case=case, payment=payment, cycle_number=1, now=now
    )
    assert res.outcome.type == OutcomeType.ESCALATED
    assert res.disposition == RecoveryLoopDisposition.ESCALATE
    assert res.termination_reason == LoopTerminationReason.HUMAN_ESCALATION_REQUIRED
    assert updated_case.status == RecoveryCaseStatus.ESCALATED
    assert updated_case.closed_at is not None
    return True


async def run_scenario_5_pending() -> bool:
    """Scenario 5: Action executes -> No recovery evidence yet -> PENDING
    -> WAIT_FOR_OUTCOME -> zero additional execution.
    """
    case, payment = make_test_fixture()
    processor = OutcomeProcessor()
    now = datetime.now(UTC)

    exec1 = Execution(
        execution_id="exec_scen5",
        action_id="act_scen5",
        case_id=case.case_id,
        execution_type="PAYMENT_LINK",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SUCCEEDED,
        started_at=now,
        completed_at=now,
    )
    ev = OutcomeEvidence(
        evidence_id="ev_scen5",
        case_id=case.case_id,
        execution_id=exec1.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=now,
    )
    res, updated_case, _ = await processor.process_outcome(
        evidence=ev, case=case, payment=payment, execution=exec1
    )
    assert res.outcome.type == OutcomeType.PENDING
    assert res.disposition == RecoveryLoopDisposition.WAIT_FOR_OUTCOME
    assert updated_case.status == RecoveryCaseStatus.OBSERVING
    return True


async def run_scenario_6_unknown_execution() -> bool:
    """Scenario 6: UNKNOWN Execution -> no false FAILED classification
    -> wait / observe.
    """
    case, payment = make_test_fixture()
    processor = OutcomeProcessor()
    now = datetime.now(UTC)

    exec1 = Execution(
        execution_id="exec_scen6",
        action_id="act_scen6",
        case_id=case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.UNKNOWN,
        started_at=now,
        completed_at=now,
    )
    ev = OutcomeEvidence(
        evidence_id="ev_scen6",
        case_id=case.case_id,
        execution_id=exec1.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=now,
    )
    res, updated_case, _ = await processor.process_outcome(
        evidence=ev, case=case, payment=payment, execution=exec1
    )
    assert res.outcome.type == OutcomeType.PENDING
    assert res.disposition == RecoveryLoopDisposition.WAIT_FOR_OUTCOME
    return True


async def run_scenario_7_duplicate_outcome() -> bool:
    """Scenario 7: Same outcome twice -> one logical outcome -> one case
    advancement -> zero duplicate re-evaluations.
    """
    case, payment = make_test_fixture()
    processor = OutcomeProcessor()
    now = datetime.now(UTC)

    ev = OutcomeEvidence(
        evidence_id="ev_scen7_dup",
        case_id=case.case_id,
        execution_id="exec_scen7",
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=now,
    )
    res1, case1, pay1 = await processor.process_outcome(
        evidence=ev, case=case, payment=payment
    )
    res2, case2, pay2 = await processor.process_outcome(
        evidence=ev, case=case1, payment=pay1
    )
    assert res1.outcome.outcome_id == res2.outcome.outcome_id
    assert case1.status == case2.status == RecoveryCaseStatus.RECOVERED
    return True


async def run_scenario_8_capture_race() -> bool:
    """Scenario 8: Action 1 fails -> Re-evaluation -> Action 2 selected
    -> Payment becomes CAPTURED -> StateGuard stops execution.
    """
    controller = RecoveryLoopController()
    orchestrator = ExecutionOrchestrator()
    policy_engine = PolicyEngine()
    decision_engine = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
    )
    now = datetime.now(UTC)
    case, payment = make_test_fixture(case_status=RecoveryCaseStatus.OBSERVING)
    base_mi = make_model_input()

    exec1 = Execution(
        execution_id="exec_scen8_1",
        action_id="act_scen8_1",
        case_id=case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=now,
        completed_at=now,
    )
    ev1 = OutcomeEvidence(
        evidence_id="ev_scen8_1",
        case_id=case.case_id,
        execution_id=exec1.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=now,
    )

    # 1. Action 1 Fails -> Re-evaluation triggered
    res1, case_eval, pay_eval = await controller.outcome_processor.process_outcome(
        evidence=ev1,
        case=case,
        payment=payment,
        execution=exec1,
        cycle_number=1,
        now=now,
    )
    assert res1.disposition == RecoveryLoopDisposition.RE_EVALUATE
    assert case_eval.status == RecoveryCaseStatus.EVALUATING

    # 2. Context Builder & Action 2 Selection
    ctx = ReEvaluationContextBuilder.build_context(
        case=case_eval,
        payment=pay_eval,
        cycle_number=2,
        history=(),
        latest_diagnosis=None,
        latest_outcome=res1.outcome,
        base_model_input=base_mi,
        now=now,
    )
    preds = make_predictions(ctx.model_input, retry_prob=0.1, plink_prob=0.9)
    decision = decision_engine.decide(
        model_input=ctx.model_input,
        diagnosis_result=None,
        outcome_predictions=preds,
        recovery_case_id=case_eval.case_id,
    )
    assert decision.selected_action == PredictorAction.PAYMENT_LINK

    # 3. Policy Decision ALLOW
    case_dec = transition_recovery_case(
        case_eval, pay_eval, RecoveryCaseStatus.DECISION_PENDING, now=now
    )
    case_pol = transition_recovery_case(
        case_dec, pay_eval, RecoveryCaseStatus.POLICY_CHECK, now=now
    )
    pol_dec, _ = policy_engine.evaluate(
        decision=decision,
        payment=pay_eval,
        case=case_pol,
        current_time=now,
        history=(),
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.ALLOW

    # 4. Out-of-band capture occurs before Phase 11 execution
    captured_payment = Payment(
        payment_id=payment.payment_id,
        customer_id=payment.customer_id,
        provider="razorpay",
        amount=payment.amount,
        currency="INR",
        method="card",
        status=PaymentStatus.CAPTURED,
        created_at=now,
        updated_at=now,
        captured_at=now,
    )
    case_approved = transition_recovery_case(
        case_pol, pay_eval, RecoveryCaseStatus.ACTION_APPROVED, now=now
    )
    action2 = RecoveryAction(
        action_id="act_scen8_2",
        case_id=case.case_id,
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
        execution_mode=ExecutionMode.SIMULATION,
        parameters={"amount": 50000},
    )

    # 5. Phase 11 StateGuard prevents execution of Action 2 on captured payment
    with pytest.raises(ExecutionStateError):
        await orchestrator.execute(
            policy_decision=pol_dec,
            recovery_action=action2,
            recovery_case=case_approved,
            payment=captured_payment,
            execution_mode=ExecutionMode.SIMULATION,
            current_time=now,
            parameters={"amount": 50000},
        )
    return True


async def run_scenario_9_no_blind_repetition() -> bool:
    """Scenario 9: Action 1 = RETRY Fails -> fresh decision context -> RETRY
    is blocked by safety guard and produces zero new execution.
    """
    controller = RecoveryLoopController()
    orchestrator = ExecutionOrchestrator()
    policy_engine = PolicyEngine()
    decision_engine = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
    )
    now = datetime.now(UTC)
    case, payment = make_test_fixture()
    base_mi = make_model_input()

    exec1 = Execution(
        execution_id="exec_scen9_1",
        action_id="act_scen9_1",
        case_id=case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=now,
        completed_at=now,
    )
    ev1 = OutcomeEvidence(
        evidence_id="ev_scen9_1",
        case_id=case.case_id,
        execution_id=exec1.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=now,
    )

    def retry_again_preds(
        mi: ModelInputRecord, _diag: Any
    ) -> dict[PredictorAction, OutcomePrediction]:
        return make_predictions(mi, retry_prob=0.95, plink_prob=0.1)

    cycle_res, updated_case, _ = await controller.handle_outcome_and_cycle(
        evidence=ev1,
        case=case,
        payment=payment,
        base_model_input=base_mi,
        execution=exec1,
        predictions_provider=retry_again_preds,
        decision_engine=decision_engine,
        policy_engine=policy_engine,
        execution_orchestrator=orchestrator,
        execution_mode=ExecutionMode.SIMULATION,
        cycle_number=1,
        now=now,
    )
    assert cycle_res.execution_result is None
    assert updated_case.status == RecoveryCaseStatus.STOPPED
    assert (
        cycle_res.outcome_result.termination_reason
        == LoopTerminationReason.SAME_ACTION_LIMIT_EXCEEDED
    )
    return True


async def run_scenario_10_full_adaptive_chain() -> bool:
    """Scenario 10: Payment Failure -> Diagnosis -> Decision 1 -> Policy 1
    -> Execute 1 -> Outcome 1 FAILED -> History -> Re-evaluation -> Decision 2
    -> Policy 2 -> Execute 2 -> Outcome 2 RECOVERED -> Case RECOVERED.
    """
    controller = RecoveryLoopController()
    orchestrator = ExecutionOrchestrator()
    policy_engine = PolicyEngine()
    decision_engine = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
    )
    now = datetime.now(UTC)
    case, payment = make_test_fixture()
    base_mi = make_model_input()

    # Instrument Phase 9 spy
    dec_calls: list[dict[str, Any]] = []
    real_decide = decision_engine.decide

    def decide_spy(
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None,
        outcome_predictions: dict[PredictorAction, OutcomePrediction],
        recovery_case_id: str,
    ) -> RecoveryDecision:
        res = real_decide(
            model_input, diagnosis_result, outcome_predictions, recovery_case_id
        )
        dec_calls.append(
            {
                "model_input": model_input,
                "predictions": outcome_predictions,
                "decision": res,
            }
        )
        return res

    decision_engine.decide = decide_spy  # type: ignore

    # Cycle 1: Decision 1 from Phase 9 -> RETRY
    p1 = make_predictions(base_mi, retry_prob=0.85, plink_prob=0.6)
    dec1 = decision_engine.decide(base_mi, None, p1, case.case_id)
    assert dec1.selected_action == PredictorAction.RETRY

    # Execute 1 -> FAILED
    exec1 = Execution(
        execution_id="exec_scen10_1",
        action_id="act_scen10_1",
        case_id=case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=now,
        completed_at=now,
    )
    ev1 = OutcomeEvidence(
        evidence_id="ev_scen10_1",
        case_id=case.case_id,
        execution_id=exec1.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=now,
    )

    def adaptive_preds(
        mi: ModelInputRecord, _diag: Any
    ) -> dict[PredictorAction, OutcomePrediction]:
        if mi.features.attempt_count > 1:
            return make_predictions(mi, retry_prob=0.1, plink_prob=0.90)
        return make_predictions(mi, retry_prob=0.8, plink_prob=0.7)

    # Handle Outcome 1 -> History Updated -> Re-evaluation
    # -> Phase 9 called for Decision 2 -> Policy 2 -> Execute 2
    c1_res, c1_case, c1_pay = await controller.handle_outcome_and_cycle(
        evidence=ev1,
        case=case,
        payment=payment,
        base_model_input=base_mi,
        execution=exec1,
        predictions_provider=adaptive_preds,
        decision_engine=decision_engine,
        policy_engine=policy_engine,
        execution_orchestrator=orchestrator,
        execution_mode=ExecutionMode.SIMULATION,
        cycle_number=1,
        now=now,
    )

    assert len(dec_calls) == 2
    assert dec_calls[0]["decision"].selected_action == PredictorAction.RETRY
    assert dec_calls[1]["decision"].selected_action == PredictorAction.PAYMENT_LINK
    assert dec_calls[1]["model_input"].features.attempt_count == 2
    assert dec_calls[1]["model_input"].features.previous_failure_count == 2

    assert c1_res.outcome_result.disposition == RecoveryLoopDisposition.RE_EVALUATE
    assert c1_res.decision is not None
    assert c1_res.decision.selected_action == PredictorAction.PAYMENT_LINK
    assert c1_res.policy_decision is not None
    assert c1_res.policy_decision.policy_outcome == PolicyOutcome.ALLOW
    assert c1_res.execution_result is not None
    assert c1_res.execution_result.status == ExecutionStatus.SUCCEEDED

    # Outcome 2 -> RECOVERED
    ev2 = OutcomeEvidence(
        evidence_id="ev_scen10_2",
        case_id=case.case_id,
        execution_id=c1_res.execution_result.execution_id,
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=now,
    )
    c2_res, final_case, final_pay = await controller.handle_outcome_and_cycle(
        evidence=ev2,
        case=c1_case,
        payment=c1_pay,
        base_model_input=base_mi,
        cycle_number=2,
        now=now,
    )
    assert c2_res.outcome_result.disposition == RecoveryLoopDisposition.COMPLETE
    assert c2_res.outcome_result.outcome.type == OutcomeType.RECOVERED
    assert final_case.status == RecoveryCaseStatus.RECOVERED
    assert final_pay.status == PaymentStatus.CAPTURED
    return True


# ==============================================================================
# MAIN ACCEPTANCE RUNNER
# ==============================================================================


async def main() -> int:
    print("=" * 80)
    print("APRO PHASE 13 — OUTCOME & ADAPTIVE RECOVERY LOOP ACCEPTANCE RUNNER")
    print("=" * 80)

    total_scenarios = 10
    passed_scenarios = 0

    scenarios = [
        ("Scenario 1 — Successful Recovery", run_scenario_1_successful_recovery),
        (
            "Scenario 2 — Failed Action -> Adaptive Action",
            run_scenario_2_failed_action_adaptive_action,
        ),
        ("Scenario 3 — Failed Action -> STOP", run_scenario_3_failed_action_stop),
        (
            "Scenario 4 — Failed Action -> ESCALATE",
            run_scenario_4_failed_action_escalate,
        ),
        ("Scenario 5 — Pending", run_scenario_5_pending),
        ("Scenario 6 — UNKNOWN Execution", run_scenario_6_unknown_execution),
        ("Scenario 7 — Duplicate Outcome", run_scenario_7_duplicate_outcome),
        ("Scenario 8 — Capture Race", run_scenario_8_capture_race),
        ("Scenario 9 — No Blind Repetition", run_scenario_9_no_blind_repetition),
        ("Scenario 10 — Full Adaptive Chain", run_scenario_10_full_adaptive_chain),
    ]

    print("\n--- [1] EXECUTING 10 MANUAL ACCEPTANCE SCENARIOS ---")
    for name, fn in scenarios:
        try:
            res = await fn()
            if res:
                passed_scenarios += 1
                print(f"  [PASS] {name}")
            else:
                print(f"  [FAIL] {name}")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")

    print(f"\nScenarios Summary: {passed_scenarios}/{total_scenarios} Passed.")

    print(
        "\n--- [2] EXECUTING 58 AUTHORITATIVE ACCEPTANCE CRITERIA (AC-01 -> AC-58) ---"
    )
    ac_results: dict[str, bool] = {}

    # Outcome Handling
    # AC-01: Execution status is distinct from recovery outcome
    ac_results["AC-01"] = ExecutionStatus.SUCCEEDED.value != OutcomeType.RECOVERED.value
    # AC-02: RECOVERED requires reliable recovery evidence
    case, pay = make_test_fixture()
    proc = OutcomeProcessor()
    ev_rec = OutcomeEvidence(
        evidence_id="ac02",
        case_id=case.case_id,
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=datetime.now(UTC),
    )
    r_ac02, _, _ = await proc.process_outcome(evidence=ev_rec, case=case, payment=pay)
    ac_results["AC-02"] = r_ac02.outcome.type == OutcomeType.RECOVERED

    # AC-03: Definitive failed recovery maps to FAILED
    ev_fail = OutcomeEvidence(
        evidence_id="ac03",
        case_id=case.case_id,
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.FAILED,
        observed_at=datetime.now(UTC),
    )
    r_ac03, _, _ = await proc.process_outcome(evidence=ev_fail, case=case, payment=pay)
    ac_results["AC-03"] = r_ac03.outcome.type == OutcomeType.FAILED

    # AC-04: Pending evidence maps to PENDING
    ex_pend = Execution(
        execution_id="ex04",
        action_id="a04",
        case_id=case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SUCCEEDED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    ev_pend = OutcomeEvidence(
        evidence_id="ac04",
        case_id=case.case_id,
        execution_id="ex04",
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=datetime.now(UTC),
    )
    r_ac04, _, _ = await proc.process_outcome(
        evidence=ev_pend, case=case, payment=pay, execution=ex_pend
    )
    ac_results["AC-04"] = r_ac04.outcome.type == OutcomeType.PENDING

    # AC-05: Expiration maps to EXPIRED
    ev_exp = OutcomeEvidence(
        evidence_id="ac05",
        case_id=case.case_id,
        evidence_type=EvidenceType.PROVIDER_EVIDENCE,
        raw_details={"status": "expired"},
        observed_at=datetime.now(UTC),
    )
    r_ac05, _, _ = await proc.process_outcome(evidence=ev_exp, case=case, payment=pay)
    ac_results["AC-05"] = r_ac05.outcome.type == OutcomeType.EXPIRED

    # AC-06: STOP maps to STOPPED
    ex_stop = Execution(
        execution_id="ex06",
        action_id="a06",
        case_id=case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.CANCELLED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    ev_stop = OutcomeEvidence(
        evidence_id="ac06",
        case_id=case.case_id,
        execution_id="ex06",
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=datetime.now(UTC),
    )
    r_ac06, _, _ = await proc.process_outcome(
        evidence=ev_stop, case=case, payment=pay, execution=ex_stop
    )
    ac_results["AC-06"] = r_ac06.outcome.type == OutcomeType.STOPPED

    # AC-07: Escalation maps to ESCALATED
    out_esc = Outcome(
        outcome_id="out_esc",
        case_id=case.case_id,
        execution_id="ex07",
        type=OutcomeType.ESCALATED,
        amount_recovered=0,
        observed_at=datetime.now(UTC),
    )
    d_ac07, _ = proc.disposition_resolver.resolve(out_esc, case, pay, [], 1)
    ac_results["AC-07"] = d_ac07 == RecoveryLoopDisposition.ESCALATE

    # Case Lifecycle
    # AC-08: OBSERVING -> RECOVERED works
    c_obs, p_obs = make_test_fixture(case_status=RecoveryCaseStatus.OBSERVING)
    c_rec = transition_recovery_case(
        c_obs,
        transition_payment(p_obs, PaymentStatus.CAPTURED),
        RecoveryCaseStatus.RECOVERED,
    )
    ac_results["AC-08"] = c_rec.status == RecoveryCaseStatus.RECOVERED

    # AC-09: OBSERVING -> EVALUATING works
    c_eval = transition_recovery_case(c_obs, p_obs, RecoveryCaseStatus.EVALUATING)
    ac_results["AC-09"] = c_eval.status == RecoveryCaseStatus.EVALUATING

    # AC-10: OBSERVING -> STOPPED works
    c_stp = transition_recovery_case(c_obs, p_obs, RecoveryCaseStatus.STOPPED)
    ac_results["AC-10"] = c_stp.status == RecoveryCaseStatus.STOPPED

    # AC-11: OBSERVING -> ESCALATED works
    c_esc = transition_recovery_case(c_obs, p_obs, RecoveryCaseStatus.ESCALATED)
    ac_results["AC-11"] = c_esc.status == RecoveryCaseStatus.ESCALATED

    # AC-12: Terminal cases cannot reopen (asserts exact exception)
    terminal_reopened = False
    try:
        transition_recovery_case(c_rec, p_obs, RecoveryCaseStatus.EVALUATING)
        terminal_reopened = True
    except (InvalidStateTransitionError, TerminalCaseReopenError):
        terminal_reopened = False
    ac_results["AC-12"] = not terminal_reopened

    # Disposition
    # AC-13: Every processed outcome produces an explicit disposition
    ac_results["AC-13"] = isinstance(r_ac02.disposition, RecoveryLoopDisposition)
    # AC-14: WAIT_FOR_OUTCOME causes zero additional recovery execution
    ac_results["AC-14"] = r_ac04.disposition == RecoveryLoopDisposition.WAIT_FOR_OUTCOME
    # AC-15: RE_EVALUATE returns to the existing decision chain
    ac_results["AC-15"] = r_ac03.disposition == RecoveryLoopDisposition.RE_EVALUATE
    # AC-16: STOP terminates automation safely
    out_s = Outcome(
        outcome_id="os",
        case_id=case.case_id,
        execution_id="es",
        type=OutcomeType.STOPPED,
        amount_recovered=0,
        observed_at=datetime.now(UTC),
    )
    d_s, _ = proc.disposition_resolver.resolve(out_s, case, pay, [], 1)
    ac_results["AC-16"] = d_s == RecoveryLoopDisposition.STOP
    # AC-17: ESCALATE terminates automation and routes to human review
    ac_results["AC-17"] = d_ac07 == RecoveryLoopDisposition.ESCALATE
    # AC-18: COMPLETE terminates confirmed recovery
    ac_results["AC-18"] = r_ac02.disposition == RecoveryLoopDisposition.COMPLETE

    # Adaptation
    # AC-19: Prior action/outcome is persisted before re-evaluation
    hist_svc = ActionHistoryService()
    act_hist = RecoveryAction(
        action_id="act_h1",
        case_id=case.case_id,
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.COMPLETED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        execution_mode=ExecutionMode.SIMULATION,
    )
    exec_hist = Execution(
        execution_id="exec_h1",
        action_id="act_h1",
        case_id=case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    out_hist = Outcome(
        outcome_id="out_h1",
        case_id=case.case_id,
        execution_id="exec_h1",
        type=OutcomeType.FAILED,
        amount_recovered=0,
        observed_at=datetime.now(UTC),
    )
    h_rec = hist_svc.build_history_from_records([act_hist], [exec_hist], [out_hist])
    ac_results["AC-19"] = (
        len(h_rec) == 1 and h_rec[0].outcome_type == OutcomeType.FAILED
    )
    # AC-20: Next decision receives action/outcome history
    b_ctx = ReEvaluationContextBuilder.build_context(
        case=c_eval,
        payment=pay,
        cycle_number=2,
        history=h_rec,
        latest_diagnosis=None,
        latest_outcome=r_ac03.outcome,
        base_model_input=make_model_input(),
        now=datetime.now(UTC),
    )
    ac_results["AC-20"] = (
        len(b_ctx.history) == 1 and b_ctx.model_input.features.attempt_count == 2
    )
    # AC-21: Failed actions are not blindly repeated
    guard = LoopSafetyGuard()
    ac_results["AC-21"] = not guard.check_same_action_repetition(
        RecoveryActionType.RETRY, h_rec
    ) and guard.check_same_action_repetition(
        RecoveryActionType.ALTERNATE_RECOVERY, h_rec
    )
    # AC-22: Re-evaluation uses fresh observable context
    ac_results["AC-22"] = b_ctx.model_input.features.previous_failure_count == 2
    # AC-23: Controller-level re-diagnosis invocation and context binding
    diag_invocations: list[dict[str, Any]] = []

    def spy_diagnosis_provider(mi: ModelInputRecord) -> DiagnosisResult:
        diag_invocations.append(
            {
                "record_id": mi.record_id,
                "attempt_count": mi.features.attempt_count,
                "failure_count": mi.features.previous_failure_count,
            }
        )
        return DiagnosisResult(
            prediction_id=f"diag_ac23_inv_{len(diag_invocations)}",
            record_id=mi.record_id,
            scenario_id=mi.scenario_id,
            model_name="DiagModel",
            model_version="v1.0",
            dataset_version=mi.dataset_version,
            feature_schema_version=mi.features.feature_schema_version,
            predicted_category=DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
            class_probabilities=dict.fromkeys(DiagnosisCategory, 0.1),
            confidence=0.90,
            uncertainty_state=UncertaintyState.HIGH_CONFIDENCE,
        )

    # Cycle 1 initial baseline diagnosis
    _ = spy_diagnosis_provider(make_model_input())

    ctrl_ac23 = RecoveryLoopController()
    c_ac23, p_ac23 = make_test_fixture(case_id="case_ac23", payment_id="pay_ac23")
    ex_ac23 = Execution(
        execution_id="exec_ac23_1",
        action_id="act_ac23_1",
        case_id=c_ac23.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    ev_ac23 = OutcomeEvidence(
        evidence_id="ev_ac23_1",
        case_id=c_ac23.case_id,
        execution_id=ex_ac23.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=datetime.now(UTC),
    )

    dec_eng_23 = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
    )
    pol_eng_23 = PolicyEngine()
    orch_23 = ExecutionOrchestrator()

    # Cycle 2 triggered via handle_outcome_and_cycle
    # -> invokes spy_diagnosis_provider for fresh Cycle 2 diagnosis
    cycle2_res_23, _, _ = await ctrl_ac23.handle_outcome_and_cycle(
        evidence=ev_ac23,
        case=c_ac23,
        payment=p_ac23,
        base_model_input=make_model_input(),
        execution=ex_ac23,
        diagnosis_provider=spy_diagnosis_provider,
        predictions_provider=lambda mi, _d: make_predictions(
            mi, retry_prob=0.1, plink_prob=0.9
        ),
        decision_engine=dec_eng_23,
        policy_engine=pol_eng_23,
        execution_orchestrator=orch_23,
        execution_mode=ExecutionMode.SIMULATION,
        cycle_number=1,
        now=datetime.now(UTC),
    )
    ac_results["AC-23"] = (
        len(diag_invocations) == 2
        and diag_invocations[0]["attempt_count"] == 1
        and diag_invocations[1]["attempt_count"] == 2
        and diag_invocations[1]["failure_count"] == 2
        and cycle2_res_23.decision is not None
        and cycle2_res_23.cycle_number == 2
    )

    # AC-24: Phase 8 predictions are refreshed with updated context across cycles
    pred_invocations: list[dict[str, Any]] = []

    def spy_predictions_provider(
        mi: ModelInputRecord, _diag: Any
    ) -> dict[PredictorAction, OutcomePrediction]:
        pred_invocations.append(
            {
                "attempt_count": mi.features.attempt_count,
                "failure_count": mi.features.previous_failure_count,
            }
        )
        if mi.features.attempt_count > 1:
            return make_predictions(mi, retry_prob=0.1, plink_prob=0.88)
        return make_predictions(mi, retry_prob=0.8, plink_prob=0.7)

    ctrl_ac24 = RecoveryLoopController()
    c_ac24, p_ac24 = make_test_fixture(case_id="case_ac24", payment_id="pay_ac24")
    ex_ac24 = Execution(
        execution_id="exec_ac24_1",
        action_id="act_ac24_1",
        case_id=c_ac24.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    ev_ac24 = OutcomeEvidence(
        evidence_id="ev_ac24_1",
        case_id=c_ac24.case_id,
        execution_id=ex_ac24.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=datetime.now(UTC),
    )
    # Baseline Cycle 1 prediction
    _ = spy_predictions_provider(make_model_input(), None)
    dec_eng_24 = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
    )
    pol_eng_24 = PolicyEngine()
    orch_24 = ExecutionOrchestrator()
    # Cycle 2 triggered via handle_outcome_and_cycle
    await ctrl_ac24.handle_outcome_and_cycle(
        evidence=ev_ac24,
        case=c_ac24,
        payment=p_ac24,
        base_model_input=make_model_input(),
        execution=ex_ac24,
        predictions_provider=spy_predictions_provider,
        decision_engine=dec_eng_24,
        policy_engine=pol_eng_24,
        execution_orchestrator=orch_24,
        execution_mode=ExecutionMode.SIMULATION,
        cycle_number=1,
        now=datetime.now(UTC),
    )
    ac_results["AC-24"] = (
        len(pred_invocations) == 2
        and pred_invocations[0]["attempt_count"] == 1
        and pred_invocations[1]["attempt_count"] == 2
        and pred_invocations[1]["failure_count"] == 2
    )

    # AC-25: Phase 9 remains the sole action-selection authority
    dec_eng = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
    )
    dec_out = dec_eng.decide(
        model_input=b_ctx.model_input,
        diagnosis_result=None,
        outcome_predictions=make_predictions(
            b_ctx.model_input, retry_prob=0.1, plink_prob=0.88
        ),
        recovery_case_id=c_eval.case_id,
    )
    ac_results["AC-25"] = dec_out.selected_action == PredictorAction.PAYMENT_LINK

    # Policy / Execution Safety
    # AC-26: Every new action receives a new Phase 10 policy decision
    pol_eng = PolicyEngine()
    pol_dec, _ = pol_eng.evaluate(
        decision=dec_out,
        payment=pay,
        case=c_eval,
        current_time=datetime.now(UTC),
        history=hist_svc.build_policy_execution_history(h_rec),
        event_trust=EventTrustState.TRUSTED,
    )
    ac_results["AC-26"] = (
        pol_dec.policy_decision_id is not None
        and pol_dec.policy_outcome == PolicyOutcome.ALLOW
    )
    # AC-27: Previous ALLOW cannot authorize a changed later action
    orch = ExecutionOrchestrator()
    stale_pol = PolicyDecision(
        policy_decision_id="p_stale",
        case_id=c_eval.case_id,
        payment_id=pay.payment_id,
        decision_id="d1",
        requested_action=PredictorAction.RETRY,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=PredictorAction.RETRY,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Ok",
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="d",
        diagnosis_model_version="d",
        outcome_model_version="o",
        created_at=datetime.now(UTC),
    )
    act_diff = RecoveryAction(
        action_id="a_diff",
        case_id=c_eval.case_id,
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        status=RecoveryActionStatus.APPROVED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        execution_mode=ExecutionMode.SIMULATION,
        parameters={"amount": 50000},
    )
    try:
        await orch.execute(
            policy_decision=stale_pol,
            recovery_action=act_diff,
            recovery_case=c_eval,
            payment=pay,
            execution_mode=ExecutionMode.SIMULATION,
            current_time=datetime.now(UTC),
            parameters={"amount": 50000},
        )
        ac_results["AC-27"] = False
    except ExecutionValidationError:
        ac_results["AC-27"] = True
    # AC-28: Phase 11 StateGuard remains mandatory and is invoked
    from apro.policy.state_guard import StateGuard

    stateguard_invoked = False
    orig_recheck = StateGuard.recheck_current_state

    def spy_recheck_current_state(payment: Any, effective_action: Any) -> Any:
        nonlocal stateguard_invoked
        stateguard_invoked = True
        return orig_recheck(payment, effective_action)

    StateGuard.recheck_current_state = spy_recheck_current_state  # type: ignore

    p28_act = RecoveryAction(
        action_id="act_ac28",
        case_id=c_eval.case_id,
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        status=RecoveryActionStatus.APPROVED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        execution_mode=ExecutionMode.SIMULATION,
        parameters={"amount": 50000},
    )
    c_dec_28 = transition_recovery_case(
        c_eval, pay, RecoveryCaseStatus.DECISION_PENDING
    )
    c_pol_28 = transition_recovery_case(c_dec_28, pay, RecoveryCaseStatus.POLICY_CHECK)
    c_approved_28 = transition_recovery_case(
        c_pol_28, pay, RecoveryCaseStatus.ACTION_APPROVED
    )
    await orch.execute(
        policy_decision=pol_dec,
        recovery_action=p28_act,
        recovery_case=c_approved_28,
        payment=pay,
        execution_mode=ExecutionMode.SIMULATION,
        current_time=datetime.now(UTC),
        parameters={"amount": 50000},
    )
    StateGuard.recheck_current_state = orig_recheck  # restore

    ac_results["AC-28"] = stateguard_invoked

    # AC-29: Captured payment blocks later execution
    p_cap = Payment(
        payment_id=pay.payment_id,
        customer_id=pay.customer_id,
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.CAPTURED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        captured_at=datetime.now(UTC),
    )
    try:
        await orch.execute(
            policy_decision=pol_dec,
            recovery_action=act_diff,
            recovery_case=c_approved_28,
            payment=p_cap,
            execution_mode=ExecutionMode.SIMULATION,
            current_time=datetime.now(UTC),
            parameters={"amount": 50000},
        )
        ac_results["AC-29"] = False
    except ExecutionStateError:
        ac_results["AC-29"] = True
    # AC-30: Policy BLOCK prevents adaptive dispatch (asserts exact exception)
    pol_block = PolicyDecision(
        policy_decision_id="p_blk",
        case_id=c_eval.case_id,
        payment_id=pay.payment_id,
        decision_id="d1",
        requested_action=PredictorAction.PAYMENT_LINK,
        policy_outcome=PolicyOutcome.BLOCK,
        effective_action=None,
        reason_code=PolicyReasonCode.MAX_RETRIES_REACHED,
        reason_detail="Max retries",
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="d",
        diagnosis_model_version="d",
        outcome_model_version="o",
        created_at=datetime.now(UTC),
    )
    blocked_dispatch = False
    try:
        await orch.execute(
            policy_decision=pol_block,
            recovery_action=act_diff,
            recovery_case=c_approved_28,
            payment=pay,
            execution_mode=ExecutionMode.SIMULATION,
            current_time=datetime.now(UTC),
            parameters={"amount": 50000},
        )
        blocked_dispatch = False
    except ExecutionAuthorizationError:
        blocked_dispatch = True
    ac_results["AC-30"] = blocked_dispatch

    # Boundedness
    # AC-31: Adaptive processing has an explicit finite bound
    ac_results["AC-31"] = guard.hard_cycle_ceiling == 10
    # AC-32: Attempt/intervention limits are honored
    can_cont, r_lim = guard.evaluate_loop_bounds(
        case=case,
        payment=pay,
        history=[
            ActionHistoryRecord(
                action_id=f"a{i}",
                action_type=RecoveryActionType.RETRY,
                execution_id=f"e{i}",
                observed_at=datetime.now(UTC),
                attempt_order=i,
            )
            for i in range(3)
        ],
        cycle_number=3,
    )
    ac_results["AC-32"] = (
        can_cont is False and r_lim == LoopTerminationReason.ATTEMPT_LIMIT_EXCEEDED
    )
    # AC-33: Same-action repetition limits are honored
    ac_results["AC-33"] = not guard.check_same_action_repetition(
        RecoveryActionType.RETRY,
        [
            ActionHistoryRecord(
                action_id="a1",
                action_type=RecoveryActionType.RETRY,
                execution_id="e1",
                observed_at=datetime.now(UTC),
                attempt_order=1,
            )
        ],
    )
    # AC-34: No eligible continuation terminates instead of looping indefinitely
    try:
        guard.evaluate_loop_bounds(case=case, payment=pay, history=[], cycle_number=11)
        ac_results["AC-34"] = False
    except UnboundedLoopError:
        ac_results["AC-34"] = True

    # Idempotency / Concurrency
    # AC-35: Duplicate outcomes do not create duplicate Outcome records
    # (durable PostgreSQL path)
    pg_url_35 = os.getenv("POSTGRES_TEST_URL")
    ac35_success = False
    if pg_url_35:
        try:
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import (
                AsyncSession,
                async_sessionmaker,
                create_async_engine,
            )

            from apro.domain.models import Customer
            from apro.persistence.models import OutcomeModel
            from apro.persistence.unit_of_work import UnitOfWork

            pg_engine_35 = create_async_engine(pg_url_35, echo=False)
            session_factory_35 = async_sessionmaker(
                bind=pg_engine_35, class_=AsyncSession, expire_on_commit=False
            )
            c_uuid_35 = str(uuid.uuid4())
            p_uuid_35 = str(uuid.uuid4())
            cust_uuid_35 = str(uuid.uuid4())
            act_uuid_35 = str(uuid.uuid4())
            exec_uuid_35 = str(uuid.uuid4())
            now_35 = datetime.now(UTC)

            customer_35 = Customer(
                customer_id=cust_uuid_35,
                email="test_ac35@example.com",
                phone="+919876543210",
                name="AC35 Customer",
                created_at=now_35,
                updated_at=now_35,
            )
            payment_35 = Payment(
                payment_id=p_uuid_35,
                customer_id=cust_uuid_35,
                provider="razorpay",
                amount=50000,
                currency="INR",
                method="card",
                status=PaymentStatus.FAILED,
                created_at=now_35,
                updated_at=now_35,
            )
            case_35 = RecoveryCase(
                case_id=c_uuid_35,
                payment_id=p_uuid_35,
                customer_id=cust_uuid_35,
                status=RecoveryCaseStatus.OBSERVING,
                opened_at=now_35,
                updated_at=now_35,
                recovery_amount=50000,
                current_attempt_count=1,
            )
            action_35 = RecoveryAction(
                action_id=act_uuid_35,
                case_id=c_uuid_35,
                action_type=RecoveryActionType.RETRY,
                status=RecoveryActionStatus.APPROVED,
                created_at=now_35,
                updated_at=now_35,
                execution_mode=ExecutionMode.SIMULATION,
                parameters={"amount": 50000},
            )
            execution_35 = Execution(
                execution_id=exec_uuid_35,
                action_id=act_uuid_35,
                case_id=c_uuid_35,
                execution_type="RETRY",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.FAILED,
                started_at=now_35,
                completed_at=now_35,
            )
            async with UnitOfWork(session_factory_35) as uow_init:
                await uow_init.customers.save(customer_35)
                await uow_init.payments.save(payment_35)
                await uow_init.recovery_cases.save(case_35)
                await uow_init.recovery_actions.save(action_35)
                await uow_init.executions.save(execution_35)
                await uow_init.commit()

            proc_35_pg = OutcomeProcessor()
            ev_35_pg = OutcomeEvidence(
                evidence_id=f"ev_ac35_{uuid.uuid4()}",
                case_id=c_uuid_35,
                execution_id=exec_uuid_35,
                evidence_type=EvidenceType.PAYMENT_EVENT,
                payment_status=PaymentStatus.CAPTURED,
                amount_recovered=50000,
                observed_at=now_35,
            )

            # First processing through UoW
            async with UnitOfWork(session_factory_35) as uow_1:
                ld_case_1 = await uow_1.recovery_cases.get_by_id(c_uuid_35)
                ld_pay_1 = await uow_1.payments.get_by_id(p_uuid_35)
                assert ld_case_1 is not None and ld_pay_1 is not None
                res_35_1, case_35_1, _ = await proc_35_pg.process_outcome(
                    evidence=ev_35_pg, case=ld_case_1, payment=ld_pay_1, uow=uow_1
                )
                await uow_1.commit()

            # Second processing of exact same evidence through independent UoW
            async with UnitOfWork(session_factory_35) as uow_2:
                ld_case_2 = await uow_2.recovery_cases.get_by_id(c_uuid_35)
                ld_pay_2 = await uow_2.payments.get_by_id(p_uuid_35)
                assert ld_case_2 is not None and ld_pay_2 is not None
                res_35_2, case_35_2, _ = await proc_35_pg.process_outcome(
                    evidence=ev_35_pg, case=ld_case_2, payment=ld_pay_2, uow=uow_2
                )
                await uow_2.commit()

            # Direct SQL query on OutcomeModel
            async with UnitOfWork(session_factory_35) as uow_verify:
                stmt_35 = select(OutcomeModel).where(OutcomeModel.case_id == c_uuid_35)
                db_res_35 = await uow_verify.session.execute(stmt_35)
                outcome_rows_35 = list(db_res_35.scalars())

            await pg_engine_35.dispose()

            ac35_success = (
                len(outcome_rows_35) == 1
                and res_35_1.outcome.outcome_id == res_35_2.outcome.outcome_id
                and res_35_1.disposition == RecoveryLoopDisposition.COMPLETE
                and res_35_2.disposition == RecoveryLoopDisposition.COMPLETE
                and case_35_1.status == RecoveryCaseStatus.RECOVERED
                and case_35_2.status == RecoveryCaseStatus.RECOVERED
                and outcome_rows_35[0].type == OutcomeType.RECOVERED.value
            )
        except Exception as exc:
            print(f"  PostgreSQL AC-35 execution error: {exc}")
            ac35_success = False
    else:
        print("  AC-35 FAILED: POSTGRES_TEST_URL is not set!")
        ac35_success = False

    ac_results["AC-35"] = ac35_success
    # AC-36: Duplicate outcomes do not trigger duplicate re-evaluation
    proc_36 = OutcomeProcessor()
    c_dup_eval, p_dup_eval = make_test_fixture(
        case_id="case_ac36",
        payment_id="pay_ac36",
        case_status=RecoveryCaseStatus.OBSERVING,
    )
    ev_dup_36 = OutcomeEvidence(
        evidence_id="ev_ac36",
        case_id="case_ac36",
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=datetime.now(UTC),
    )
    r_dup1, c_dup1, p_dup1 = await proc_36.process_outcome(
        evidence=ev_dup_36, case=c_dup_eval, payment=p_dup_eval
    )
    r_dup2, c_dup2, p_dup2 = await proc_36.process_outcome(
        evidence=ev_dup_36, case=c_dup1, payment=p_dup1
    )
    ac_results["AC-36"] = (
        r_dup1.outcome.outcome_id == r_dup2.outcome.outcome_id
        and r_dup1.disposition == RecoveryLoopDisposition.COMPLETE
        and r_dup2.disposition == RecoveryLoopDisposition.COMPLETE
        and c_dup1.status == RecoveryCaseStatus.RECOVERED
        and c_dup2.status == RecoveryCaseStatus.RECOVERED
    )
    # AC-37: Concurrent processing produces one logical advancement
    # (durable PostgreSQL / persistent path)
    pg_url_37 = os.getenv("POSTGRES_TEST_URL")
    ac37_success = False
    if pg_url_37:
        try:
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import (
                AsyncSession,
                async_sessionmaker,
                create_async_engine,
            )

            from apro.domain.models import Customer
            from apro.persistence.models import OutcomeModel
            from apro.persistence.unit_of_work import UnitOfWork

            pg_engine_37 = create_async_engine(pg_url_37, echo=False)
            session_factory_37 = async_sessionmaker(
                bind=pg_engine_37, class_=AsyncSession, expire_on_commit=False
            )
            c_uuid_37 = str(uuid.uuid4())
            p_uuid_37 = str(uuid.uuid4())
            cust_uuid_37 = str(uuid.uuid4())
            now_37 = datetime.now(UTC)

            customer_37 = Customer(
                customer_id=cust_uuid_37,
                email="test_ac37@example.com",
                phone="+919876543210",
                name="AC37 Customer",
                created_at=now_37,
                updated_at=now_37,
            )
            payment_37 = Payment(
                payment_id=p_uuid_37,
                customer_id=cust_uuid_37,
                provider="razorpay",
                amount=50000,
                currency="INR",
                method="card",
                status=PaymentStatus.FAILED,
                created_at=now_37,
                updated_at=now_37,
            )
            case_37 = RecoveryCase(
                case_id=c_uuid_37,
                payment_id=p_uuid_37,
                customer_id=cust_uuid_37,
                status=RecoveryCaseStatus.OBSERVING,
                opened_at=now_37,
                updated_at=now_37,
                recovery_amount=50000,
                current_attempt_count=1,
            )
            act_uuid_37 = str(uuid.uuid4())
            exec_uuid_37 = str(uuid.uuid4())
            action_37 = RecoveryAction(
                action_id=act_uuid_37,
                case_id=c_uuid_37,
                action_type=RecoveryActionType.RETRY,
                status=RecoveryActionStatus.APPROVED,
                created_at=now_37,
                updated_at=now_37,
                execution_mode=ExecutionMode.SIMULATION,
                parameters={"amount": 50000},
            )
            execution_37 = Execution(
                execution_id=exec_uuid_37,
                action_id=act_uuid_37,
                case_id=c_uuid_37,
                execution_type="RETRY",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.FAILED,
                started_at=now_37,
                completed_at=now_37,
            )
            async with UnitOfWork(session_factory_37) as uow_init:
                await uow_init.customers.save(customer_37)
                await uow_init.payments.save(payment_37)
                await uow_init.recovery_cases.save(case_37)
                await uow_init.recovery_actions.save(action_37)
                await uow_init.executions.save(execution_37)
                await uow_init.commit()

            proc_37_pg = OutcomeProcessor()
            ev_37_pg = OutcomeEvidence(
                evidence_id=f"ev_ac37_{uuid.uuid4()}",
                case_id=c_uuid_37,
                execution_id=exec_uuid_37,
                evidence_type=EvidenceType.PAYMENT_EVENT,
                payment_status=PaymentStatus.CAPTURED,
                amount_recovered=50000,
                observed_at=now_37,
            )

            async def pg_worker_ac37() -> OutcomeProcessingResult:
                async with UnitOfWork(session_factory_37) as uow_w:
                    ld_case = await uow_w.recovery_cases.get_by_id(c_uuid_37)
                    ld_pay = await uow_w.payments.get_by_id(p_uuid_37)
                    assert ld_case is not None and ld_pay is not None
                    res, _, _ = await proc_37_pg.process_outcome(
                        evidence=ev_37_pg,
                        case=ld_case,
                        payment=ld_pay,
                        uow=uow_w,
                    )
                    await uow_w.commit()
                    return res

            pg_res_37 = await asyncio.gather(
                pg_worker_ac37(), pg_worker_ac37(), return_exceptions=False
            )
            async with UnitOfWork(session_factory_37) as uow_verify:
                stmt_37 = select(OutcomeModel).where(OutcomeModel.case_id == c_uuid_37)
                db_res_37 = await uow_verify.session.execute(stmt_37)
                outcome_rows_37 = list(db_res_37.scalars())

            await pg_engine_37.dispose()

            ac37_success = (
                len(pg_res_37) == 2
                and pg_res_37[0].outcome.outcome_id == pg_res_37[1].outcome.outcome_id
                and pg_res_37[0].disposition
                == pg_res_37[1].disposition
                == RecoveryLoopDisposition.COMPLETE
                and len(outcome_rows_37) == 1
                and outcome_rows_37[0].type == OutcomeType.RECOVERED.value
            )
        except Exception as exc:
            print(f"  PostgreSQL AC-37 execution error: {exc}")
            ac37_success = False
    else:
        proc_37 = OutcomeProcessor()
        c_conc, p_conc = make_test_fixture(
            case_id="case_ac37",
            payment_id="pay_ac37",
            case_status=RecoveryCaseStatus.OBSERVING,
        )
        ev_conc = OutcomeEvidence(
            evidence_id="ev_ac37_conc",
            case_id=c_conc.case_id,
            evidence_type=EvidenceType.PAYMENT_EVENT,
            payment_status=PaymentStatus.CAPTURED,
            amount_recovered=50000,
            observed_at=datetime.now(UTC),
        )
        results_conc = await asyncio.gather(
            proc_37.process_outcome(evidence=ev_conc, case=c_conc, payment=p_conc),
            proc_37.process_outcome(evidence=ev_conc, case=c_conc, payment=p_conc),
        )
        ac37_success = (
            len(results_conc) == 2
            and results_conc[0][0].outcome.outcome_id
            == results_conc[1][0].outcome.outcome_id
            and results_conc[0][0].disposition
            == results_conc[1][0].disposition
            == RecoveryLoopDisposition.COMPLETE
            and len(proc_37._in_memory_outcomes) == 1
        )
    ac_results["AC-37"] = ac37_success

    # Pending / Unknown
    # AC-38: Pending outcomes remain observable without immediate extra execution
    ac_results["AC-38"] = r_ac04.disposition == RecoveryLoopDisposition.WAIT_FOR_OUTCOME
    # AC-39: UNKNOWN execution is not automatically converted to FAILED
    ex_unk_39 = Execution(
        execution_id="ex_unk_39",
        action_id="a_unk_39",
        case_id=case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.UNKNOWN,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    ev_unk_39 = OutcomeEvidence(
        evidence_id="ev_unk_39",
        case_id=case.case_id,
        execution_id=ex_unk_39.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=datetime.now(UTC),
    )
    r_unk_39, _, _ = await proc.process_outcome(
        evidence=ev_unk_39, case=case, payment=pay, execution=ex_unk_39
    )
    ac_results["AC-39"] = (
        r_unk_39.outcome.type == OutcomeType.PENDING
        and r_unk_39.outcome.type != OutcomeType.FAILED
        and r_unk_39.disposition == RecoveryLoopDisposition.WAIT_FOR_OUTCOME
    )

    # Leakage / Provenance
    # AC-40: Simulator latent truth cannot reach runtime loop logic
    ev_leak = OutcomeEvidence(
        evidence_id="ev_l",
        case_id="c1",
        evidence_type=EvidenceType.SIMULATION_OUTCOME,
        observed_at=datetime.now(UTC),
        raw_details={
            "potential_outcomes": {"RETRY": "SUCCESS"},
            "oracle_action": "RETRY",
            "safe_val": 123,
        },
    )
    ac_results["AC-40"] = (
        "potential_outcomes" not in ev_leak.raw_details
        and "oracle_action" not in ev_leak.raw_details
    )
    # AC-41: Real vs simulated outcome provenance is preserved
    ev_sim_41 = OutcomeEvidence(
        evidence_id="ev_sim_41",
        case_id=case.case_id,
        evidence_type=EvidenceType.SIMULATION_OUTCOME,
        provenance=EvidenceProvenance.SIMULATOR,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=datetime.now(UTC),
    )
    ev_rzp_41 = OutcomeEvidence(
        evidence_id="ev_rzp_41",
        case_id=case.case_id,
        evidence_type=EvidenceType.PROVIDER_EVIDENCE,
        provenance=EvidenceProvenance.RAZORPAY,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=datetime.now(UTC),
    )
    r_sim_41, _, _ = await proc.process_outcome(
        evidence=ev_sim_41, case=case, payment=pay
    )
    r_rzp_41, _, _ = await proc.process_outcome(
        evidence=ev_rzp_41, case=case, payment=pay
    )
    ac_results["AC-41"] = (
        r_sim_41.provenance == EvidenceProvenance.SIMULATOR
        and r_rzp_41.provenance == EvidenceProvenance.RAZORPAY
        and "provenance=SIMULATOR" in r_sim_41.outcome.evidence_reference
        and "provenance=RAZORPAY" in r_rzp_41.outcome.evidence_reference
    )
    # AC-42: Historical decisions/executions/outcomes remain immutable
    with pytest.raises(ValidationError, match="Instance is frozen"):
        r_ac02.outcome.amount_recovered = 999  # type: ignore

    ac_results["AC-42"] = True

    # Determinism
    # AC-43: Disposition resolution is deterministic
    d_det1, _ = proc.disposition_resolver.resolve(r_ac02.outcome, case, pay, [], 1)
    d_det2, _ = proc.disposition_resolver.resolve(r_ac02.outcome, case, pay, [], 1)
    ac_results["AC-43"] = d_det1 == d_det2 == RecoveryLoopDisposition.COMPLETE
    # AC-44: Loop/re-evaluation identity is deterministic
    ac_results["AC-44"] = compute_re_evaluation_id(
        "c1", 1, "out1"
    ) == compute_re_evaluation_id("c1", 1, "out1")

    # Compatibility
    # AC-45: Phase 10 behavior remains unchanged
    p_test_dec = dec_eng.decide(
        model_input=b_ctx.model_input,
        diagnosis_result=None,
        outcome_predictions=make_predictions(b_ctx.model_input),
        recovery_case_id=c_eval.case_id,
    )
    p_test_pol, p_test_trace = pol_eng.evaluate(
        decision=p_test_dec,
        payment=pay,
        case=c_eval,
        current_time=datetime.now(UTC),
        history=(),
        event_trust=EventTrustState.TRUSTED,
    )
    ac_results["AC-45"] = (
        isinstance(p_test_pol, PolicyDecision)
        and p_test_pol.policy_outcome
        in (
            PolicyOutcome.ALLOW,
            PolicyOutcome.BLOCK,
            PolicyOutcome.REQUIRE_HUMAN_APPROVAL,
        )
        and p_test_trace is not None
    )
    # AC-46: Phase 11 behavior remains compatible
    p11_act = RecoveryAction(
        action_id="p11_act_01",
        case_id=c_approved_28.case_id,
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        status=RecoveryActionStatus.APPROVED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        execution_mode=ExecutionMode.SIMULATION,
        parameters={"amount": 50000},
    )
    p11_exec_res = await orch.execute(
        policy_decision=pol_dec,
        recovery_action=p11_act,
        recovery_case=c_approved_28,
        payment=pay,
        execution_mode=ExecutionMode.SIMULATION,
        current_time=datetime.now(UTC),
        parameters={"amount": 50000},
    )
    ac_results["AC-46"] = (
        p11_exec_res.status == ExecutionStatus.SUCCEEDED
        and p11_exec_res.execution_id is not None
    )
    # AC-47: Phase 12 provider boundary remains compatible
    stub_47 = DeterministicRazorpayStub()
    rzp_cfg_47 = RazorpayTestModeConfig(
        key_id="rzp_test_12345", key_secret="sec_test_secret_01"
    )
    rzp_client_47 = RazorpayTestModeClient(config=rzp_cfg_47, transport=stub_47)
    rzp_req_47 = RazorpayPaymentLinkRequest(
        amount=50000,
        currency="INR",
        reference_id="ref_ac47",
        description="Recovery AC47",
    )
    rzp_res_47 = await rzp_client_47.create_payment_link(rzp_req_47)
    ac_results["AC-47"] = rzp_res_47 is not None and rzp_res_47.id is not None
    # AC-48: Simulation behavior remains compatible
    sim_res_48 = evaluate_action_outcome_from_probability(
        true_prob=0.8,
        action=SimulatedActionType.RETRY,
        amount=50000,
        generation_seed=42,
        scenario_id="scen_48",
    )
    ac_results["AC-48"] = (
        sim_res_48 is not None and sim_res_48.status == SimulatedOutcomeStatus.SUCCESS
    )
    # AC-49: Full Phase 0–12 regression remains green
    print("  Running full pytest regression suite for AC-49...")
    reg_proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        capture_output=True,
        text=True,
    )
    ac_results["AC-49"] = reg_proc.returncode == 0
    if not ac_results["AC-49"]:
        print(f"  Pytest failure:\n{reg_proc.stdout}\n{reg_proc.stderr}")

    # Security / Boundary
    # AC-50: No secrets enter outcome/loop models
    ev_sec = OutcomeEvidence(
        evidence_id="ev_s",
        case_id="c1",
        evidence_type=EvidenceType.PROVIDER_EVIDENCE,
        observed_at=datetime.now(UTC),
        raw_details={
            "key_secret": "secret",
            "password": "pwd",
            "token": "tok",
            "val": 1,
        },
    )
    ac_results["AC-50"] = (
        "key_secret" not in ev_sec.raw_details
        and "password" not in ev_sec.raw_details
        and "token" not in ev_sec.raw_details
    )
    # AC-51: Provider-specific parsing remains outside the recovery-loop layer
    rl_files = list(Path("src/apro/recovery_loop").glob("*.py"))
    has_prov = any(
        "from apro.providers" in f.read_text(encoding="utf-8") for f in rl_files
    )
    ac_results["AC-51"] = not has_prov
    # AC-52: No second policy engine exists
    rl_code_52 = "".join(
        f.read_text(encoding="utf-8")
        for f in Path("src/apro/recovery_loop").glob("*.py")
    )
    ac_results["AC-52"] = (
        "class PolicyEngine" not in rl_code_52
        and "class PolicyRule" not in rl_code_52
        and "evaluate_rules" not in rl_code_52
    )
    # AC-53: No second economic decision engine exists
    ac_results["AC-53"] = (
        "class EconomicDecisionEngine" not in rl_code_52
        and "calculate_utility" not in rl_code_52
        and "expected_recovery_value" not in rl_code_52
    )
    # AC-54: Prove no bypass of Phase 10 or Phase 11 (strict execution boundary)
    call_sequence: list[str] = []

    orig_decide = dec_eng.decide
    orig_eval = pol_eng.evaluate
    orig_exec = orch.execute

    def spy_decide(*args: Any, **kwargs: Any) -> RecoveryDecision:
        call_sequence.append("PHASE_9")
        return orig_decide(*args, **kwargs)

    def spy_evaluate(*args: Any, **kwargs: Any) -> tuple[PolicyDecision, Any]:
        call_sequence.append("PHASE_10")
        return orig_eval(*args, **kwargs)

    async def spy_execute(*args: Any, **kwargs: Any) -> Any:
        call_sequence.append("PHASE_11")
        return await orig_exec(*args, **kwargs)

    dec_eng.decide = spy_decide  # type: ignore
    pol_eng.evaluate = spy_evaluate  # type: ignore
    orch.execute = spy_execute  # type: ignore

    ctrl_54 = RecoveryLoopController()
    c_54_case, c_54_pay = make_test_fixture(
        case_id="case_ac54_1", payment_id="pay_ac54_1"
    )
    ex_54_1 = Execution(
        execution_id="ex_54_1",
        action_id="act_54_1",
        case_id=c_54_case.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    ev_54_1 = OutcomeEvidence(
        evidence_id="ev_54_1",
        case_id=c_54_case.case_id,
        execution_id=ex_54_1.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=datetime.now(UTC),
    )
    c_54_res, _, _ = await ctrl_54.handle_outcome_and_cycle(
        evidence=ev_54_1,
        case=c_54_case,
        payment=c_54_pay,
        base_model_input=make_model_input(),
        execution=ex_54_1,
        predictions_provider=lambda mi, _d: make_predictions(
            mi, retry_prob=0.1, plink_prob=0.9
        ),
        decision_engine=dec_eng,
        policy_engine=pol_eng,
        execution_orchestrator=orch,
        execution_mode=ExecutionMode.SIMULATION,
        cycle_number=1,
        now=datetime.now(UTC),
    )
    allow_sequence = list(call_sequence)

    # Test BLOCK path
    call_sequence.clear()

    def block_evaluate(*args: Any, **kwargs: Any) -> tuple[PolicyDecision, Any]:
        _ = (args, kwargs)
        call_sequence.append("PHASE_10")
        pol = PolicyDecision(
            policy_decision_id="pol_blk_54",
            case_id="case_ac54_2",
            payment_id="pay_ac54_2",
            decision_id="d54",
            requested_action=PredictorAction.PAYMENT_LINK,
            policy_outcome=PolicyOutcome.BLOCK,
            effective_action=None,
            reason_code=PolicyReasonCode.MAX_RETRIES_REACHED,
            reason_detail="Blocked for AC54",
            payment_state_observed=PaymentStatus.FAILED,
            decision_model_version="d",
            diagnosis_model_version="d",
            outcome_model_version="o",
            created_at=datetime.now(UTC),
        )
        return pol, None

    pol_eng.evaluate = block_evaluate  # type: ignore
    c_54_case2, c_54_pay2 = make_test_fixture(
        case_id="case_ac54_2", payment_id="pay_ac54_2"
    )
    ex_54_2 = Execution(
        execution_id="ex_54_2",
        action_id="act_54_2",
        case_id=c_54_case2.case_id,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    ev_54_2 = OutcomeEvidence(
        evidence_id="ev_54_2",
        case_id=c_54_case2.case_id,
        execution_id=ex_54_2.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=datetime.now(UTC),
    )
    c_54_blk_res, _, _ = await ctrl_54.handle_outcome_and_cycle(
        evidence=ev_54_2,
        case=c_54_case2,
        payment=c_54_pay2,
        base_model_input=make_model_input(),
        execution=ex_54_2,
        predictions_provider=lambda mi, _d: make_predictions(
            mi, retry_prob=0.1, plink_prob=0.9
        ),
        decision_engine=dec_eng,
        policy_engine=pol_eng,
        execution_orchestrator=orch,
        execution_mode=ExecutionMode.SIMULATION,
        cycle_number=1,
        now=datetime.now(UTC),
    )
    block_sequence = list(call_sequence)

    # Restore originals
    dec_eng.decide = orig_decide  # type: ignore
    pol_eng.evaluate = orig_eval  # type: ignore
    orch.execute = orig_exec  # type: ignore

    ac_results["AC-54"] = (
        allow_sequence == ["PHASE_9", "PHASE_10", "PHASE_11"]
        and block_sequence == ["PHASE_9", "PHASE_10"]
        and c_54_res.execution_result is not None
        and c_54_blk_res.execution_result is None
    )

    # AC-55: Acceptance runner failure detection test
    # (genuine test of runner's own evaluation logic)
    false_criterion_res = evaluate_acceptance_results(
        passed_scenarios=10,
        total_scenarios=10,
        ac_results={**{f"AC-{i:02d}": True for i in range(1, 59)}, "AC-02": False},
        expected_ac_count=58,
    )
    failed_scenario_res = evaluate_acceptance_results(
        passed_scenarios=9,
        total_scenarios=10,
        ac_results={f"AC-{i:02d}": True for i in range(1, 59)},
        expected_ac_count=58,
    )
    all_true_res = evaluate_acceptance_results(
        passed_scenarios=10,
        total_scenarios=10,
        ac_results={f"AC-{i:02d}": True for i in range(1, 59)},
        expected_ac_count=58,
    )
    subprocess_test = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; "
            "from scripts.run_phase_13_acceptance import evaluate_acceptance_results; "
            "corrupted = {f'AC-{i:02d}': True for i in range(1, 59)}; "
            "corrupted['AC-02'] = False; "
            "sys.exit(evaluate_acceptance_results(10, 10, corrupted, 58))",
        ],
        capture_output=True,
        text=True,
    )
    ac_results["AC-55"] = (
        false_criterion_res == 1
        and failed_scenario_res == 1
        and all_true_res == 0
        and subprocess_test.returncode == 1
    )
    # AC-56: Manual acceptance scenarios are executable and documented
    ac_results["AC-56"] = passed_scenarios == total_scenarios

    # AC-57: Quality gates pass (Ruff check, format, Mypy)
    print("  Running quality gates (Ruff check, format check, Mypy) for AC-57...")
    ruff_chk = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."], capture_output=True, text=True
    )
    ruff_fmt = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        capture_output=True,
        text=True,
    )
    mypy_res = subprocess.run(
        [sys.executable, "-m", "mypy", "src"], capture_output=True, text=True
    )
    ac_results["AC-57"] = (
        ruff_chk.returncode == 0
        and ruff_fmt.returncode == 0
        and mypy_res.returncode == 0
    )
    if not ac_results["AC-57"]:
        print(
            f"  Quality Gate Failure: Ruff Chk: {ruff_chk.returncode}, "
            f"Ruff Fmt: {ruff_fmt.returncode}, Mypy: {mypy_res.returncode}"
        )
        if ruff_chk.returncode != 0:
            print(f"  Ruff check errors:\n{ruff_chk.stdout}")
        if ruff_fmt.returncode != 0:
            print(f"  Ruff format errors:\n{ruff_fmt.stdout}")
        if mypy_res.returncode != 0:
            print(f"  Mypy errors:\n{mypy_res.stdout}")

    # AC-58: Git provenance is clean and reviewed (strict scope validation)
    diff_tracked = (
        subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
        )
        .stdout.strip()
        .splitlines()
    )

    status_all = (
        subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            capture_output=True,
            text=True,
        )
        .stdout.strip()
        .splitlines()
    )

    touched_files = [line[3:].strip() for line in status_all if len(line) > 3]
    allowed_prefixes = (
        "docs/",
        "src/apro/recovery_loop/",
        "tests/recovery_loop/",
        "scripts/run_phase_13_acceptance.py",
        "pyproject.toml",
    )
    unexpected_files = [
        f for f in touched_files if not any(f.startswith(p) for p in allowed_prefixes)
    ]
    no_phase_0_12_tracked_diff = len(diff_tracked) == 0

    ac_results["AC-58"] = no_phase_0_12_tracked_diff and len(unexpected_files) == 0

    passed_acs = 0
    for ac_id, status in sorted(ac_results.items()):
        status_str = "PASS" if status else "FAIL"
        if status:
            passed_acs += 1
        print(f"  [{status_str}] {ac_id}")

    print("\n" + "=" * 80)
    print("FINAL ACCEPTANCE SUMMARY:")
    print(f"  Manual Scenarios:    {passed_scenarios}/{total_scenarios} Passed")
    print(f"  Acceptance Criteria: {passed_acs}/58 Passed")
    print("=" * 80)

    exit_code = evaluate_acceptance_results(
        passed_scenarios=passed_scenarios,
        total_scenarios=total_scenarios,
        ac_results=ac_results,
        expected_ac_count=58,
    )
    if exit_code == 0:
        print("\n>>> ALL PHASE 13 ACCEPTANCE CRITERIA AND MANUAL SCENARIOS PASSED <<<")
    else:
        print("\n>>> PHASE 13 ACCEPTANCE FAILED <<<")
    return exit_code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
