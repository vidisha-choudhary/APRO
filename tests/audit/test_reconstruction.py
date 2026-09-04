"""Tests for CaseReconstructionService completeness and validation."""

import os
import uuid
from datetime import UTC, datetime

import pytest

from apro.audit.enums import AuditCompleteness, AuditEventType
from apro.audit.reconstruction import CaseReconstructionService
from apro.domain.enums import (
    AuditActor,
    ExecutionMode,
    ExecutionStatus,
    FailureCategory,
    OutcomeType,
    PaymentStatus,
    PolicyDecisionResult,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import (
    AuditEvent,
    Customer,
    Decision,
    Diagnosis,
    Execution,
    Outcome,
    Payment,
    PolicyDecision,
    RecoveryAction,
    RecoveryCase,
)
from apro.persistence.database import get_async_engine, get_session_factory
from apro.persistence.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_reconstruct_from_case_id_only_postgres() -> None:
    """Full lifecycle case is reconstructable from case_id only in PostgreSQL."""
    postgres_url = os.environ.get("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set; skipping database reconstruction test")

    engine = get_async_engine(postgres_url)
    session_factory = get_session_factory(engine)

    cid = str(uuid.uuid4())
    pid = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    act_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    out_id = str(uuid.uuid4())
    dec_id = str(uuid.uuid4())
    pol_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    async with UnitOfWork(session_factory) as uow:
        await uow.customers.save(
            Customer(customer_id=cid, created_at=now, updated_at=now)
        )
        await uow.payments.save(
            Payment(
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
        )
        case = RecoveryCase(
            case_id=case_id,
            payment_id=pid,
            customer_id=cid,
            status=RecoveryCaseStatus.RECOVERED,
            opened_at=now,
            updated_at=now,
            recovery_amount=50000,
        )
        await uow.recovery_cases.save(case)

        # Seed Domain Records
        await uow.diagnoses.append(
            Diagnosis(
                diagnosis_id=str(uuid.uuid4()),
                case_id=case_id,
                category=FailureCategory.CUSTOMER_SIDE,
                confidence=0.9,
                model_name="diag_v1",
                model_version="1.0.0",
                created_at=now,
            )
        )
        await uow.decisions.append(
            Decision(
                decision_id=dec_id,
                case_id=case_id,
                recommended_action=RecoveryActionType.ALTERNATE_RECOVERY,
                confidence=0.95,
                expected_recovery_value=45000,
                reason="Optimal ERV action",
                model_name="dec_v1",
                model_version="1.0.0",
                created_at=now,
            )
        )
        await uow.policy_decisions.append(
            PolicyDecision(
                policy_decision_id=pol_id,
                decision_id=dec_id,
                case_id=case_id,
                result=PolicyDecisionResult.ALLOW,
                reason="H1_MAX_ATTEMPTS: Allowed",
                policy_version="policy-v1",
                created_at=now,
            )
        )
        await uow.recovery_actions.save(
            RecoveryAction(
                action_id=act_id,
                case_id=case_id,
                action_type=RecoveryActionType.ALTERNATE_RECOVERY,
                status=RecoveryActionStatus.APPROVED,
                created_at=now,
                updated_at=now,
                execution_mode=ExecutionMode.SIMULATION,
            )
        )
        await uow.executions.save(
            Execution(
                execution_id=exec_id,
                action_id=act_id,
                case_id=case_id,
                execution_type="payment_link_executor",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.SUCCEEDED,
                started_at=now,
                completed_at=now,
            )
        )
        await uow.outcomes.append(
            Outcome(
                outcome_id=out_id,
                case_id=case_id,
                execution_id=exec_id,
                type=OutcomeType.RECOVERED,
                amount_recovered=50000,
                evidence_reference="captured",
                observed_at=now,
            )
        )

        # Seed Audit Events
        ev1 = AuditEvent(
            audit_event_id=str(uuid.uuid4()),
            case_id=case_id,
            event_type=AuditEventType.CASE_CREATED,
            actor=AuditActor.SYSTEM,
            timestamp=now,
        )
        ev_diag = AuditEvent(
            audit_event_id=str(uuid.uuid4()),
            case_id=case_id,
            event_type=AuditEventType.DIAGNOSIS_CREATED,
            actor=AuditActor.MODEL,
            timestamp=now,
        )
        ev_dec = AuditEvent(
            audit_event_id=str(uuid.uuid4()),
            case_id=case_id,
            event_type=AuditEventType.DECISION_CREATED,
            actor=AuditActor.MODEL,
            timestamp=now,
        )
        ev_pol = AuditEvent(
            audit_event_id=str(uuid.uuid4()),
            case_id=case_id,
            event_type=AuditEventType.POLICY_DECISION_CREATED,
            actor=AuditActor.POLICY,
            timestamp=now,
        )
        ev2 = AuditEvent(
            audit_event_id=str(uuid.uuid4()),
            case_id=case_id,
            event_type=AuditEventType.EXECUTION_STARTED,
            actor=AuditActor.EXECUTOR,
            timestamp=now,
        )
        ev_out = AuditEvent(
            audit_event_id=str(uuid.uuid4()),
            case_id=case_id,
            event_type=AuditEventType.OUTCOME_PROCESSED,
            actor=AuditActor.SYSTEM,
            timestamp=now,
        )
        await uow.audit_events.append(ev1)
        await uow.audit_events.append(ev_diag)
        await uow.audit_events.append(ev_dec)
        await uow.audit_events.append(ev_pol)
        await uow.audit_events.append(ev2)
        await uow.audit_events.append(ev_out)
        await uow.commit()

    # Reconstruct from case_id only
    async with UnitOfWork(session_factory) as uow:
        trace = await CaseReconstructionService.reconstruct_case(
            case_id=case_id, uow=uow
        )

    assert trace.case_id == case_id
    assert trace.final_case_status == "RECOVERED"
    assert trace.total_amount_recovered == 50000
    assert trace.completeness == AuditCompleteness.COMPLETE
    assert trace.integrity_valid is True

    await engine.dispose()


@pytest.mark.asyncio
async def test_missing_lifecycle_artifacts_produce_incomplete() -> None:
    """Removing any mandatory lifecycle stage yields AUDIT_INCOMPLETE."""
    now = datetime.now(UTC)
    base_case = RecoveryCase(
        case_id="case_inc",
        payment_id="pay_inc",
        customer_id="cust_inc",
        status=RecoveryCaseStatus.RECOVERED,
        opened_at=now,
        updated_at=now,
    )
    base_diag = Diagnosis(
        diagnosis_id="diag_inc",
        case_id="case_inc",
        category=FailureCategory.CUSTOMER_SIDE,
        confidence=0.8,
        model_name="diag_v1",
        model_version="1.0.0",
        created_at=now,
    )
    base_dec = Decision(
        decision_id="dec_inc",
        case_id="case_inc",
        recommended_action=RecoveryActionType.RETRY,
        confidence=0.8,
        expected_recovery_value=1000,
        reason="Retry",
        model_name="m1",
        model_version="1.0.0",
        created_at=now,
    )
    base_pol = PolicyDecision(
        policy_decision_id="pol_inc",
        decision_id="dec_inc",
        case_id="case_inc",
        result=PolicyDecisionResult.ALLOW,
        reason="H1: ALLOW",
        policy_version="1.0.0",
        created_at=now,
    )
    base_exec = Execution(
        execution_id="exec_inc",
        action_id="act_inc",
        case_id="case_inc",
        execution_type="retry",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SUCCEEDED,
        started_at=now,
        completed_at=now,
    )
    base_out = Outcome(
        outcome_id="out_inc",
        case_id="case_inc",
        execution_id="exec_inc",
        type=OutcomeType.RECOVERED,
        amount_recovered=1000,
        observed_at=now,
    )

    # 1. Missing Decision -> INCOMPLETE
    t_no_dec = await CaseReconstructionService.reconstruct_case(
        case_id="case_inc",
        case=base_case,
        diagnosis=base_diag,
        decisions=[],
        policy_decisions=[base_pol],
        executions=[base_exec],
        outcomes=[base_out],
    )
    assert t_no_dec.completeness == AuditCompleteness.INCOMPLETE

    # 2. Missing Policy -> INCOMPLETE
    t_no_pol = await CaseReconstructionService.reconstruct_case(
        case_id="case_inc",
        case=base_case,
        diagnosis=base_diag,
        decisions=[base_dec],
        policy_decisions=[],
        executions=[base_exec],
        outcomes=[base_out],
    )
    assert t_no_pol.completeness == AuditCompleteness.INCOMPLETE

    # 3. Missing Execution -> INCOMPLETE
    t_no_exec = await CaseReconstructionService.reconstruct_case(
        case_id="case_inc",
        case=base_case,
        diagnosis=base_diag,
        decisions=[base_dec],
        policy_decisions=[base_pol],
        executions=[],
        outcomes=[base_out],
    )
    assert t_no_exec.completeness == AuditCompleteness.INCOMPLETE

    # 4. Missing Outcome -> INCOMPLETE
    t_no_out = await CaseReconstructionService.reconstruct_case(
        case_id="case_inc",
        case=base_case,
        diagnosis=base_diag,
        decisions=[base_dec],
        policy_decisions=[base_pol],
        executions=[base_exec],
        outcomes=[],
    )
    assert t_no_out.completeness == AuditCompleteness.INCOMPLETE
