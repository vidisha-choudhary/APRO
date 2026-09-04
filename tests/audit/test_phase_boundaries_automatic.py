"""Unit & integration tests verifying automatic audit emission
at Phase 7-10 boundaries.
"""

import os
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from apro.audit.enums import AuditCompleteness, AuditEventType
from apro.audit.reconstruction import CaseReconstructionService
from apro.audit.service import AuditService
from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.decision.engine import EconomicDecisionEngine
from apro.diagnosis.consumer import DiagnosisArtifactConsumer
from apro.diagnosis.enums import DiagnosisCategory, UncertaintyState
from apro.diagnosis.models import DiagnosisResult
from apro.domain.enums import (
    ExecutionMode,
    FailureCategory,
    PaymentStatus,
    PolicyDecisionResult,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import (
    Customer,
    Decision,
    Diagnosis,
    Payment,
    RecoveryAction,
    RecoveryCase,
)
from apro.domain.models import (
    PolicyDecision as DomainPolicyDecision,
)
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.persistence.database import get_async_engine, get_session_factory
from apro.persistence.unit_of_work import UnitOfWork
from apro.policy.engine import PolicyEngine
from apro.policy.models import EventTrustState
from apro.recovery_loop.controller import RecoveryLoopController
from apro.recovery_loop.enums import EvidenceType
from apro.recovery_loop.models import OutcomeEvidence
from apro.recovery_loop.outcomes import OutcomeProcessor
from apro.recovery_prediction.consumer import PredictionArtifactConsumer
from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    PredictionUncertaintyState,
)
from apro.recovery_prediction.enums import (
    RecoveryAction as PredictorAction,
)
from apro.recovery_prediction.models import OutcomePrediction
from apro.simulation.enums import SimulatedActionType, SimulatedPaymentMethod


def _make_model_input(record_id: str, payment_id: str) -> ModelInputRecord:
    now = datetime.now(UTC)
    features = FeatureSnapshot(
        feature_schema_version="feature-schema-v1",
        decision_timestamp=now.isoformat(),
        payment_id=payment_id,
        payment_amount=50000,
        currency="INR",
        payment_method=SimulatedPaymentMethod.CARD,
        attempt_count=1,
        failure_reason="insufficient_funds",
        failure_code="BAD_REQUEST",
        customer_id="cust_test_auto",
        previous_payment_count=2,
        previous_success_count=1,
        previous_failure_count=1,
        previous_recovery_count=0,
        previous_retry_success=0,
        previous_payment_link_success=0,
        hour_of_day=10,
        day_of_week=2,
        is_weekend=False,
        candidate_actions=[
            SimulatedActionType.RETRY,
            SimulatedActionType.PAYMENT_LINK,
        ],
    )
    return ModelInputRecord(
        record_id=record_id,
        dataset_type=DatasetType.BENCHMARK,
        dataset_version="dataset-v1",
        scenario_id="scen_test_auto",
        generation_seed=42,
        scenario_version="v1",
        configuration_version="v1",
        feature_schema_version="feature-schema-v1",
        features=features,
    )


def _make_predictions(
    model_input: ModelInputRecord,
) -> dict[PredictorAction, OutcomePrediction]:
    preds: dict[PredictorAction, OutcomePrediction] = {}
    for act, p in [
        (PredictorAction.RETRY, 0.3),
        (PredictorAction.PAYMENT_LINK, 0.9),
        (PredictorAction.OUTREACH, 0.4),
        (PredictorAction.ESCALATE, 0.1),
        (PredictorAction.STOP, 0.0),
    ]:
        preds[act] = OutcomePrediction(
            prediction_id=f"pred_{act.value}_{uuid.uuid4().hex[:6]}",
            record_id=model_input.record_id,
            scenario_id=model_input.scenario_id,
            action=act,
            model_name="model_outcome_v1",
            model_version="1.0.0",
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
async def test_phase7_diagnosis_automatic_audit_hook() -> None:
    """Verify DiagnosisArtifactConsumer emits DIAGNOSIS_CREATED
    when audit_service is present.
    """
    service = AuditService()
    consumer = DiagnosisArtifactConsumer(audit_service=service)
    diag = DiagnosisResult(
        prediction_id="diag_auto_01",
        record_id="rec_01",
        scenario_id="scen_01",
        model_name="diagnosis_engine",
        model_version="1.0.0",
        dataset_version="dataset-v1",
        feature_schema_version="feature-schema-v1",
        predicted_category=DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
        class_probabilities={DiagnosisCategory.CUSTOMER_SIDE_FAILURE: 0.9},
        confidence=0.9,
        uncertainty_state=UncertaintyState.HIGH_CONFIDENCE,
    )
    res_diag, audit_ev = await consumer.consume_diagnosis(
        diagnosis=diag, case_id="case_p7_test", cycle_number=1
    )
    assert res_diag is diag
    assert audit_ev is not None
    assert audit_ev.event_type == AuditEventType.DIAGNOSIS_CREATED.value

    # When disabled
    disabled_consumer = DiagnosisArtifactConsumer(audit_service=None)
    _, no_audit = await disabled_consumer.consume_diagnosis(
        diagnosis=diag, case_id="case_p7_test", cycle_number=1
    )
    assert no_audit is None


@pytest.mark.asyncio
async def test_phase8_prediction_automatic_audit_hook() -> None:
    """Verify PredictionArtifactConsumer emits PREDICTION_CREATED
    when audit_service is present.
    """
    service = AuditService()
    consumer = PredictionArtifactConsumer(audit_service=service)
    mi = _make_model_input("rec_p8", "pay_p8")
    preds = _make_predictions(mi)

    res_preds, audit_ev = await consumer.consume_predictions(
        predictions=preds, case_id="case_p8_test", cycle_number=1
    )
    assert res_preds is preds
    assert audit_ev is not None
    assert audit_ev.event_type == AuditEventType.PREDICTION_CREATED.value

    # When disabled
    disabled_consumer = PredictionArtifactConsumer(audit_service=None)
    _, no_audit = await disabled_consumer.consume_predictions(
        predictions=preds, case_id="case_p8_test", cycle_number=1
    )
    assert no_audit is None


@pytest.mark.asyncio
async def test_phase9_decision_automatic_audit_hook() -> None:
    """Verify EconomicDecisionEngine.decide automatically emits DECISION_CREATED."""
    service = AuditService()
    engine = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
        audit_service=service,
    )
    mi = _make_model_input("rec_p9", "pay_p9")
    preds = _make_predictions(mi)

    decision = engine.decide(
        model_input=mi,
        diagnosis_result=None,
        outcome_predictions=preds,
        recovery_case_id="case_p9_test",
    )
    assert decision is not None
    events = [
        e
        for e in service._in_memory_events
        if e.event_type == AuditEventType.DECISION_CREATED.value
    ]
    assert len(events) == 1
    assert events[0].payload["selected_action"] == decision.selected_action.value

    # When disabled
    disabled_engine = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
        audit_service=None,
    )
    dec_disabled = disabled_engine.decide(
        model_input=mi,
        diagnosis_result=None,
        outcome_predictions=preds,
        recovery_case_id="case_p9_test",
    )
    assert dec_disabled is not None
    assert len(service._in_memory_events) == 1


@pytest.mark.asyncio
async def test_phase10_policy_automatic_audit_hook() -> None:
    """Verify PolicyEngine.evaluate automatically emits POLICY_DECISION_CREATED."""
    service = AuditService()
    pol_engine = PolicyEngine(audit_service=service)
    dec_engine = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
    )
    mi = _make_model_input("rec_p10", "pay_p10")
    preds = _make_predictions(mi)
    decision = dec_engine.decide(
        model_input=mi,
        diagnosis_result=None,
        outcome_predictions=preds,
        recovery_case_id="case_p10_test",
    )
    now = datetime.now(UTC)
    payment = Payment(
        payment_id="pay_p10",
        customer_id="cust_p10",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_p10_test",
        payment_id="pay_p10",
        customer_id="cust_p10",
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
    )

    pol_dec, _trace = pol_engine.evaluate(
        decision=decision,
        payment=payment,
        case=case,
        current_time=now,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec is not None
    events = [
        e
        for e in service._in_memory_events
        if e.event_type == AuditEventType.POLICY_DECISION_CREATED.value
    ]
    assert len(events) == 1
    assert events[0].payload["result"] == pol_dec.policy_outcome.value

    # When disabled
    disabled_pol = PolicyEngine(audit_service=None)
    disabled_dec, _ = disabled_pol.evaluate(
        decision=decision,
        payment=payment,
        case=case,
        current_time=now,
        event_trust=EventTrustState.TRUSTED,
    )
    assert disabled_dec is not None
    assert len(service._in_memory_events) == 1


@pytest.mark.asyncio
async def test_missing_phase7_10_hook_produces_incomplete_reconstruction_postgres() -> (
    None
):
    """Disabling ONE actual authoritative audit hook (Phase 9 decision) produces
    an INCOMPLETE reconstruction when queried strictly by case_id from PostgreSQL.
    """
    postgres_url = os.environ.get("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set; skipping database test")

    engine = get_async_engine(postgres_url)
    session_factory = get_session_factory(engine)
    audit_service = AuditService()

    cid = str(uuid.uuid4())
    pid = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    payment = Payment(
        payment_id=pid,
        customer_id=cid,
        provider="razorpay",
        amount=75000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id=case_id,
        payment_id=pid,
        customer_id=cid,
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
        recovery_amount=75000,
    )
    mi = _make_model_input(f"rec_{case_id[:8]}", pid)
    preds = _make_predictions(mi)
    diag_res = DiagnosisResult(
        prediction_id=str(uuid.uuid4()),
        record_id=mi.record_id,
        scenario_id=mi.scenario_id,
        model_name="diagnosis_classifier_v1",
        model_version="1.2.0",
        dataset_version="dataset-v1",
        feature_schema_version="feature-schema-v1",
        predicted_category=DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
        class_probabilities={DiagnosisCategory.CUSTOMER_SIDE_FAILURE: 0.95},
        confidence=0.95,
        uncertainty_state=UncertaintyState.HIGH_CONFIDENCE,
    )

    # Instantiate phase boundary components with Decision Engine audit hook DISABLED
    diag_consumer = DiagnosisArtifactConsumer(audit_service=audit_service)
    pred_consumer = PredictionArtifactConsumer(audit_service=audit_service)
    dec_engine_disabled = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
        audit_service=None,  # REAL DISABLED HOOK
    )
    pol_engine = PolicyEngine(audit_service=audit_service)
    exec_orchestrator = ExecutionOrchestrator(audit_service=audit_service)
    outcome_processor = OutcomeProcessor(audit_service=audit_service)

    async with UnitOfWork(session_factory) as uow:
        # Step 0: Save entities & emit case_created
        await uow.customers.save(
            Customer(customer_id=cid, created_at=now, updated_at=now)
        )
        await uow.payments.save(payment)
        await uow.recovery_cases.save(case)
        await audit_service.record_case_created(case=case, uow=uow)

        # Step 1: Phase 7 Diagnosis hook
        await diag_consumer.consume_diagnosis(
            diagnosis=diag_res, case_id=case_id, cycle_number=1, uow=uow
        )
        domain_diag = Diagnosis(
            diagnosis_id=str(uuid.uuid4()),
            case_id=case_id,
            category=FailureCategory.CUSTOMER_SIDE,
            confidence=0.95,
            model_name="diagnosis_classifier_v1",
            model_version="1.2.0",
            created_at=now,
        )
        await uow.diagnoses.append(domain_diag)

        # Step 2: Phase 8 Prediction hook
        await pred_consumer.consume_predictions(
            predictions=list(preds.values()), case_id=case_id, cycle_number=1, uow=uow
        )

        # Step 3: Phase 9 Decision - executes real calculation but hook is disabled
        decision = dec_engine_disabled.decide(
            model_input=mi,
            diagnosis_result=diag_res,
            outcome_predictions=preds,
            recovery_case_id=case_id,
        )

        domain_dec = Decision(
            decision_id=str(uuid.uuid4()),
            case_id=case_id,
            recommended_action=RecoveryActionType.RETRY,
            confidence=decision.decision_confidence,
            expected_recovery_value=decision.expected_recovery_value or 50000,
            reason=decision.rationale,
            model_name="economic_decision_engine",
            model_version=decision.decision_model_version,
            created_at=now,
        )
        await uow.decisions.append(domain_dec)

        # Step 4: Phase 10 Policy hook
        pol_dec, _trace = pol_engine.evaluate(
            decision=decision,
            payment=payment,
            case=case,
            current_time=now,
            event_trust=EventTrustState.TRUSTED,
        )
        await pol_engine.record_audit(
            policy_decision=pol_dec,
            cycle_number=1,
            uow=uow,
        )
        domain_pol = DomainPolicyDecision(
            policy_decision_id=str(uuid.uuid4()),
            decision_id=domain_dec.decision_id,
            case_id=case_id,
            result=PolicyDecisionResult.ALLOW,
            reason="Policy allowed",
            policy_version=pol_dec.policy_version,
            created_at=now,
        )
        await uow.policy_decisions.append(domain_pol)

        # Step 5: Phase 11/12 Execution hook
        approved_case = case.model_copy(
            update={"status": RecoveryCaseStatus.ACTION_APPROVED, "updated_at": now}
        )
        await uow.recovery_cases.save(approved_case)
        domain_act_type = (
            RecoveryActionType.ALTERNATE_RECOVERY
            if pol_dec.effective_action
            and pol_dec.effective_action.value in ("PAYMENT_LINK", "ALTERNATE_RECOVERY")
            else RecoveryActionType.RETRY
        )
        act = RecoveryAction(
            action_id=str(uuid.uuid4()),
            case_id=case_id,
            action_type=domain_act_type,
            status=RecoveryActionStatus.APPROVED,
            created_at=now,
            updated_at=now,
            execution_mode=ExecutionMode.SIMULATION,
            parameters={"amount": payment.amount},
        )
        await uow.recovery_actions.save(act)
        exec_res = await exec_orchestrator.execute(
            policy_decision=pol_dec,
            recovery_action=act,
            recovery_case=approved_case,
            payment=payment,
            execution_mode=ExecutionMode.SIMULATION,
            current_time=now,
            parameters={"amount": payment.amount},
            unit_of_work=uow,
        )

        # Step 6: Phase 13 Outcome hook
        exec_entity = await uow.executions.get_by_id(exec_res.execution_id)
        current_case = (await uow.recovery_cases.get_by_id(case_id)) or approved_case
        current_payment = (await uow.payments.get_by_id(pid)) or payment
        evidence = OutcomeEvidence(
            evidence_id=str(uuid.uuid4()),
            case_id=case_id,
            execution_id=exec_res.execution_id,
            evidence_type=EvidenceType.PAYMENT_EVENT,
            payment_status=PaymentStatus.CAPTURED,
            amount_recovered=payment.amount,
            observed_at=now,
        )
        await outcome_processor.process_outcome(
            evidence=evidence,
            case=current_case,
            payment=current_payment,
            execution=exec_entity,
            cycle_number=1,
            now=now,
            uow=uow,
        )
        await uow.commit()

    # Reconstruct from PostgreSQL strictly using case_id
    async with UnitOfWork(session_factory) as uow:
        trace = await CaseReconstructionService.reconstruct_case(
            case_id=case_id, uow=uow
        )

    # Verification: because Phase 9 decision hook was disabled,
    # reconstruction is INCOMPLETE
    assert trace.completeness == AuditCompleteness.INCOMPLETE
    event_types = {e.event_type for e in trace.events}
    assert AuditEventType.DECISION_CREATED.value not in event_types
    assert AuditEventType.DIAGNOSIS_CREATED.value in event_types
    assert AuditEventType.PREDICTION_CREATED.value in event_types
    assert AuditEventType.POLICY_DECISION_CREATED.value in event_types
    assert AuditEventType.EXECUTION_STARTED.value in event_types
    assert AuditEventType.OUTCOME_PROCESSED.value in event_types

    await engine.dispose()


@pytest.mark.asyncio
async def test_no_duplicate_phase9_10_audit_events_multi_cycle_postgres() -> None:
    """Verify that throughout Cycle 1 and Cycle 2 adaptive execution,
    exactly ONE DECISION_CREATED event is emitted per Decision artifact, and
    exactly ONE POLICY_DECISION_CREATED event is emitted per PolicyDecision artifact,
    with zero duplicate semantic events.
    """
    postgres_url = os.environ.get("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set; skipping database test")

    engine = get_async_engine(postgres_url)
    session_factory = get_session_factory(engine)
    audit_service = AuditService()

    cid = str(uuid.uuid4())
    pid = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    customer = Customer(customer_id=cid, created_at=now, updated_at=now)
    payment = Payment(
        payment_id=pid,
        customer_id=cid,
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id=case_id,
        payment_id=pid,
        customer_id=cid,
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
    )
    base_mi = _make_model_input(f"rec_{case_id[:8]}", pid)
    preds1 = _make_predictions(base_mi)

    # Initialize authoritative components with AuditService
    dec_engine = EconomicDecisionEngine(
        feature_schema_version="feature-schema-v1",
        prediction_feature_schema_version="feature-schema-v1",
        audit_service=audit_service,
    )
    pol_engine = PolicyEngine(audit_service=audit_service)
    exec_orchestrator = ExecutionOrchestrator(audit_service=audit_service)
    outcome_processor = OutcomeProcessor(audit_service=audit_service)
    controller = RecoveryLoopController(
        outcome_processor=outcome_processor,
        audit_service=audit_service,
    )

    # === CYCLE 1 ===
    async with UnitOfWork(session_factory) as uow:
        await uow.customers.save(customer)
        await uow.payments.save(payment)
        await uow.recovery_cases.save(case)
        await audit_service.record_case_created(case, uow=uow)

        # Authoritative Phase 9 decide (emits DECISION_CREATED for Cycle 1)
        dec1 = dec_engine.decide(
            model_input=base_mi,
            diagnosis_result=None,
            outcome_predictions=preds1,
            recovery_case_id=case_id,
        )

        approved_case = case.model_copy(
            update={"status": RecoveryCaseStatus.ACTION_APPROVED, "updated_at": now}
        )
        await uow.recovery_cases.save(approved_case)

        # Authoritative Phase 10 evaluate (emits POLICY_DECISION_CREATED for Cycle 1)
        pol1, _trace1 = pol_engine.evaluate(
            decision=dec1,
            payment=payment,
            case=approved_case,
            current_time=now,
            event_trust=EventTrustState.TRUSTED,
        )

        domain_act1_type = (
            RecoveryActionType.ALTERNATE_RECOVERY
            if pol1.effective_action
            and pol1.effective_action.value in ("PAYMENT_LINK", "ALTERNATE_RECOVERY")
            else RecoveryActionType.RETRY
        )
        act1_id = str(uuid.uuid4())
        act1 = RecoveryAction(
            action_id=act1_id,
            case_id=case_id,
            action_type=domain_act1_type,
            status=RecoveryActionStatus.APPROVED,
            created_at=now,
            updated_at=now,
            execution_mode=ExecutionMode.SIMULATION,
            parameters={"amount": 50000},
        )
        await uow.recovery_actions.save(act1)

        exec1_res = await exec_orchestrator.execute(
            policy_decision=pol1,
            recovery_action=act1,
            recovery_case=approved_case,
            payment=payment,
            execution_mode=ExecutionMode.SIMULATION,
            current_time=now,
            parameters={"amount": 50000},
            unit_of_work=uow,
        )
        await uow.commit()

    # Verify Cycle 1 in database
    async with UnitOfWork(session_factory) as uow:
        cycle1_events = await uow.audit_events.find_by_case_id(case_id)

    c1_dec_events = [
        e
        for e in cycle1_events
        if e.event_type == AuditEventType.DECISION_CREATED.value
    ]
    c1_pol_events = [
        e
        for e in cycle1_events
        if e.event_type == AuditEventType.POLICY_DECISION_CREATED.value
    ]
    assert len(c1_dec_events) == 1, (
        f"Expected 1 DECISION_CREATED, found {len(c1_dec_events)}"
    )
    assert c1_dec_events[0].payload["decision_id"] == dec1.decision_id
    assert len(c1_pol_events) == 1, (
        f"Expected 1 POLICY_DECISION_CREATED, found {len(c1_pol_events)}"
    )
    assert c1_pol_events[0].payload["policy_decision_id"] == pol1.policy_decision_id

    # === CYCLE 2 (Adaptive re-evaluation through Controller) ===
    ev1 = OutcomeEvidence(
        evidence_id=str(uuid.uuid4()),
        case_id=case_id,
        execution_id=exec1_res.execution_id,
        evidence_type=EvidenceType.EXECUTION_RESULT,
        raw_details={"status": "failed"},
        observed_at=now,
    )

    def adaptive_preds_provider(
        mi: ModelInputRecord, _diag: Any
    ) -> dict[PredictorAction, OutcomePrediction]:
        preds = _make_predictions(mi)
        preds[PredictorAction.PAYMENT_LINK] = OutcomePrediction(
            prediction_id=f"pred_plink_{uuid.uuid4().hex[:6]}",
            record_id=mi.record_id,
            scenario_id=mi.scenario_id,
            action=PredictorAction.PAYMENT_LINK,
            model_name="model_outcome_v1",
            model_version="1.0.0",
            dataset_version=mi.dataset_version,
            feature_schema_version=mi.feature_schema_version,
            predicted_success_probability=0.99,
            predicted_outcome_state=PredictedOutcomeState.SUCCESS,
            predicted_recovered_amount=50000,
            confidence=0.95,
            uncertainty_state=PredictionUncertaintyState.HIGH_CONFIDENCE,
        )
        return preds

    async with UnitOfWork(session_factory) as uow:
        exec_case = (await uow.recovery_cases.get_by_id(case_id)) or approved_case
        exec_pmt = (await uow.payments.get_by_id(pid)) or payment
        exec1_entity = await uow.executions.get_by_id(exec1_res.execution_id)

        (
            cycle2_res,
            updated_case_c2,
            updated_payment_c2,
        ) = await controller.handle_outcome_and_cycle(
            evidence=ev1,
            case=exec_case,
            payment=exec_pmt,
            base_model_input=base_mi,
            execution=exec1_entity,
            predictions_provider=adaptive_preds_provider,
            decision_engine=dec_engine,
            policy_engine=pol_engine,
            execution_orchestrator=exec_orchestrator,
            execution_mode=ExecutionMode.SIMULATION,
            cycle_number=1,
            now=now,
            uow=uow,
        )
        await uow.commit()

    assert cycle2_res.decision is not None
    assert cycle2_res.policy_decision is not None
    dec2 = cycle2_res.decision
    pol2 = cycle2_res.policy_decision

    # Query PostgreSQL directly for all audit events of this case
    async with UnitOfWork(session_factory) as uow:
        all_events = await uow.audit_events.find_by_case_id(case_id)

    dec_events = [
        e for e in all_events if e.event_type == AuditEventType.DECISION_CREATED.value
    ]
    pol_events = [
        e
        for e in all_events
        if e.event_type == AuditEventType.POLICY_DECISION_CREATED.value
    ]

    # Verify DECISION_CREATED counts per artifact
    dec1_matches = [
        e for e in dec_events if e.payload.get("decision_id") == dec1.decision_id
    ]
    dec2_matches = [
        e for e in dec_events if e.payload.get("decision_id") == dec2.decision_id
    ]
    assert len(dec1_matches) == 1, (
        f"Expected exactly 1 event for Decision 1, got {len(dec1_matches)}"
    )
    assert len(dec2_matches) == 1, (
        f"Expected exactly 1 event for Decision 2, got {len(dec2_matches)}"
    )
    assert len(dec_events) == 2, (
        f"Expected total 2 DECISION_CREATED events, got {len(dec_events)}"
    )

    # Verify POLICY_DECISION_CREATED counts per artifact
    pol1_matches = [
        e
        for e in pol_events
        if e.payload.get("policy_decision_id") == pol1.policy_decision_id
    ]
    pol2_matches = [
        e
        for e in pol_events
        if e.payload.get("policy_decision_id") == pol2.policy_decision_id
    ]
    assert len(pol1_matches) == 1, (
        f"Expected exactly 1 event for PolicyDecision 1, got {len(pol1_matches)}"
    )
    assert len(pol2_matches) == 1, (
        f"Expected exactly 1 event for PolicyDecision 2, got {len(pol2_matches)}"
    )
    assert len(pol_events) == 2, (
        f"Expected total 2 POLICY_DECISION_CREATED events, got {len(pol_events)}"
    )

    await engine.dispose()
