"""Unit and Integration Tests for RecoveryCaseOrchestrator and Placeholders."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apro.domain.enums import (
    FailureCategory,
    PaymentStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.exceptions import (
    CapturedPaymentRecoveryError,
    InvalidStateTransitionError,
)
from apro.domain.models import Customer, Payment, PaymentEvent
from apro.persistence.repositories import AuditEventRepository, RecoveryCaseRepository
from apro.persistence.unit_of_work import UnitOfWork
from apro.recovery.orchestrator import RecoveryCaseOrchestrator
from apro.recovery.placeholders import (
    PlaceholderDiagnosisProvider,
    PlaceholderEvaluationProvider,
)


@pytest.mark.asyncio
async def test_case_creation_and_fields() -> None:
    """Test qualifying payment failure creates RecoveryCase(status=NEW)
    with correct fields.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    from apro.persistence.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())

    async with UnitOfWork(factory) as uow:
        await uow.customers.save(
            Customer(customer_id=c_id, created_at=now, updated_at=now)
        )
        payment = await uow.payments.save(
            Payment(
                payment_id=p_id,
                customer_id=c_id,
                provider="razorpay",
                amount=75000,
                currency="INR",
                method="card",
                status=PaymentStatus.FAILED,
                created_at=now,
                updated_at=now,
            )
        )
        evt = PaymentEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            provider="razorpay",
            event_type="payment.failed",
            payment_id=p_id,
            amount=75000,
            currency="INR",
            method="card",
            status=PaymentStatus.FAILED,
            event_timestamp=now,
            received_at=now,
        )

        orchestrator = RecoveryCaseOrchestrator()
        case = await orchestrator.handle_payment_failed(uow, payment, evt)

        assert case is not None
        assert case.status == RecoveryCaseStatus.NEW
        assert case.payment_id == p_id
        assert case.customer_id == c_id
        assert case.recovery_amount == 75000
        assert case.current_attempt_count == 0
        assert case.closed_at is None
        assert case.stop_reason is None
        assert case.escalation_reason is None

        # Verify audit event emitted
        audits = await uow.audit_events.find_by_case_id(case.case_id)
        assert len(audits) == 1
        assert audits[0].event_type == "RECOVERY_CASE_CREATED"
        assert audits[0].payload["initial_status"] == "NEW"

        await uow.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_active_case_reuse() -> None:
    """Test repeated qualifying event reuses active RecoveryCase
    without creating a duplicate.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    from apro.persistence.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())

    async with UnitOfWork(factory) as uow:
        await uow.customers.save(
            Customer(customer_id=c_id, created_at=now, updated_at=now)
        )
        payment = await uow.payments.save(
            Payment(
                payment_id=p_id,
                customer_id=c_id,
                provider="razorpay",
                amount=50000,
                currency="INR",
                method="card",
                status=PaymentStatus.FAILED,
                created_at=now,
                updated_at=now,
            )
        )
        evt1 = PaymentEvent(
            event_id="evt_first_1",
            provider="razorpay",
            event_type="payment.failed",
            payment_id=p_id,
            amount=50000,
            currency="INR",
            method="card",
            status=PaymentStatus.FAILED,
            event_timestamp=now,
            received_at=now,
        )

        orchestrator = RecoveryCaseOrchestrator()
        case1 = await orchestrator.handle_payment_failed(uow, payment, evt1)

        evt2 = PaymentEvent(
            event_id="evt_second_2",
            provider="razorpay",
            event_type="payment.failed",
            payment_id=p_id,
            amount=50000,
            currency="INR",
            method="card",
            status=PaymentStatus.FAILED,
            event_timestamp=now,
            received_at=now,
        )
        case2 = await orchestrator.handle_payment_failed(uow, payment, evt2)

        # Must return the SAME active case
        assert case1.case_id == case2.case_id

        # Total cases in DB for this payment must equal 1
        all_cases = await uow.recovery_cases.find_by_payment_id(p_id)
        assert len(all_cases) == 1

        # Audit events must record creation and reuse
        audits = await uow.audit_events.find_by_case_id(case1.case_id)
        assert len(audits) == 2
        types = [a.event_type for a in audits]
        assert "RECOVERY_CASE_CREATED" in types
        assert "RECOVERY_CASE_REUSED" in types

        await uow.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_captured_payment_safety_prevents_case_creation() -> None:
    """Test CAPTURED payment cannot open a RecoveryCase."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    from apro.persistence.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())

    async with UnitOfWork(factory) as uow:
        await uow.customers.save(
            Customer(customer_id=c_id, created_at=now, updated_at=now)
        )
        captured_payment = await uow.payments.save(
            Payment(
                payment_id=p_id,
                customer_id=c_id,
                provider="razorpay",
                amount=50000,
                currency="INR",
                method="card",
                status=PaymentStatus.CAPTURED,
                created_at=now,
                updated_at=now,
                captured_at=now,
            )
        )
        evt = PaymentEvent(
            event_id="evt_late_failed",
            provider="razorpay",
            event_type="payment.failed",
            payment_id=p_id,
            amount=50000,
            currency="INR",
            method="card",
            status=PaymentStatus.FAILED,
            event_timestamp=now,
            received_at=now,
        )

        orchestrator = RecoveryCaseOrchestrator()
        with pytest.raises(CapturedPaymentRecoveryError):
            await orchestrator.handle_payment_failed(uow, captured_payment, evt)

        # No case created
        cases = await uow.recovery_cases.find_by_payment_id(p_id)
        assert len(cases) == 0

        await uow.rollback()

    await engine.dispose()


@pytest.mark.asyncio
async def test_captured_payment_safely_terminates_active_case() -> None:
    """Test payment capture safely terminates an active RecoveryCase."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    from apro.persistence.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())

    async with UnitOfWork(factory) as uow:
        await uow.customers.save(
            Customer(customer_id=c_id, created_at=now, updated_at=now)
        )
        payment = await uow.payments.save(
            Payment(
                payment_id=p_id,
                customer_id=c_id,
                provider="razorpay",
                amount=50000,
                currency="INR",
                method="card",
                status=PaymentStatus.FAILED,
                created_at=now,
                updated_at=now,
            )
        )
        evt_fail = PaymentEvent(
            event_id="evt_fail_1",
            provider="razorpay",
            event_type="payment.failed",
            payment_id=p_id,
            amount=50000,
            currency="INR",
            method="card",
            status=PaymentStatus.FAILED,
            event_timestamp=now,
            received_at=now,
        )

        orchestrator = RecoveryCaseOrchestrator()
        case = await orchestrator.handle_payment_failed(uow, payment, evt_fail)
        assert case.status == RecoveryCaseStatus.NEW

        # Update payment to CAPTURED
        captured_payment = payment.model_copy(
            update={"status": PaymentStatus.CAPTURED, "captured_at": now}
        )
        await uow.payments.save(captured_payment)

        evt_cap = PaymentEvent(
            event_id="evt_cap_2",
            provider="razorpay",
            event_type="payment.captured",
            payment_id=p_id,
            amount=50000,
            currency="INR",
            method="card",
            status=PaymentStatus.CAPTURED,
            event_timestamp=now,
            received_at=now,
        )

        terminated_case = await orchestrator.handle_payment_captured(
            uow, captured_payment, evt_cap
        )
        assert terminated_case is not None
        assert terminated_case.status == RecoveryCaseStatus.STOPPED
        assert terminated_case.closed_at is not None
        assert terminated_case.stop_reason is not None

        # Verify audit record
        audits = await uow.audit_events.find_by_case_id(case.case_id)
        types = [a.event_type for a in audits]
        assert "RECOVERY_CASE_STOPPED" in types

        await uow.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_new_recovery_episode_after_terminal_case() -> None:
    """Test new qualifying failure creates a new RecoveryCase after
    previous case is terminal.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    from apro.persistence.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())

    async with UnitOfWork(factory) as uow:
        await uow.customers.save(
            Customer(customer_id=c_id, created_at=now, updated_at=now)
        )
        payment = await uow.payments.save(
            Payment(
                payment_id=p_id,
                customer_id=c_id,
                provider="razorpay",
                amount=50000,
                currency="INR",
                method="card",
                status=PaymentStatus.FAILED,
                created_at=now,
                updated_at=now,
            )
        )
        evt1 = PaymentEvent(
            event_id="evt_episode_1",
            provider="razorpay",
            event_type="payment.failed",
            payment_id=p_id,
            amount=50000,
            currency="INR",
            method="card",
            status=PaymentStatus.FAILED,
            event_timestamp=now,
            received_at=now,
        )

        orchestrator = RecoveryCaseOrchestrator()
        case1 = await orchestrator.handle_payment_failed(uow, payment, evt1)

        # Transition case1 to terminal STOPPED
        case1_stopped = await orchestrator.transition_case(
            uow, case1.case_id, RecoveryCaseStatus.STOPPED, reason="Manual termination"
        )
        assert case1_stopped.status == RecoveryCaseStatus.STOPPED

        # Subsequent failure event for same payment (payment remains FAILED)
        evt2 = PaymentEvent(
            event_id="evt_episode_2",
            provider="razorpay",
            event_type="payment.failed",
            payment_id=p_id,
            amount=50000,
            currency="INR",
            method="card",
            status=PaymentStatus.FAILED,
            event_timestamp=now,
            received_at=now,
        )
        case2 = await orchestrator.handle_payment_failed(uow, payment, evt2)

        # Must create a NEW distinct case (case_id != case1.case_id)
        assert case2.case_id != case1.case_id
        assert case2.status == RecoveryCaseStatus.NEW

        # Total cases in DB for payment = 2 (1 terminal, 1 active)
        all_cases = await uow.recovery_cases.find_by_payment_id(p_id)
        assert len(all_cases) == 2

        await uow.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_controlled_lifecycle_transitions_and_invalid_transition_rejection() -> (
    None
):
    """Test valid case transitions succeed and invalid transitions are rejected."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    from apro.persistence.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())

    async with UnitOfWork(factory) as uow:
        await uow.customers.save(
            Customer(customer_id=c_id, created_at=now, updated_at=now)
        )
        payment = await uow.payments.save(
            Payment(
                payment_id=p_id,
                customer_id=c_id,
                provider="razorpay",
                amount=50000,
                currency="INR",
                method="card",
                status=PaymentStatus.FAILED,
                created_at=now,
                updated_at=now,
            )
        )
        orchestrator = RecoveryCaseOrchestrator()
        evt = PaymentEvent(
            event_id="evt_trans_1",
            provider="razorpay",
            event_type="payment.failed",
            payment_id=p_id,
            amount=50000,
            currency="INR",
            method="card",
            status=PaymentStatus.FAILED,
            event_timestamp=now,
            received_at=now,
        )
        case = await orchestrator.handle_payment_failed(uow, payment, evt)

        # NEW -> DIAGNOSING
        c2 = await orchestrator.transition_case(
            uow, case.case_id, RecoveryCaseStatus.DIAGNOSING
        )
        assert c2.status == RecoveryCaseStatus.DIAGNOSING

        # DIAGNOSING -> EVALUATING
        c3 = await orchestrator.transition_case(
            uow, case.case_id, RecoveryCaseStatus.EVALUATING
        )
        assert c3.status == RecoveryCaseStatus.EVALUATING

        # Illegal transition: EVALUATING cannot transition directly to EXECUTING
        with pytest.raises(InvalidStateTransitionError):
            await orchestrator.transition_case(
                uow, case.case_id, RecoveryCaseStatus.EXECUTING
            )

        await uow.commit()

    await engine.dispose()


def test_placeholder_providers() -> None:
    """Test PlaceholderDiagnosisProvider and PlaceholderEvaluationProvider
    are deterministic and AI-free.
    """
    diag_provider = PlaceholderDiagnosisProvider()
    diag = diag_provider.get_diagnosis("case_123")

    assert diag.category == FailureCategory.UNKNOWN
    assert diag.confidence == 0.0
    assert diag.model_name == "PHASE4_PLACEHOLDER"
    assert diag.model_version == "1.0"
    assert "PHASE4_PLACEHOLDER" in diag.evidence

    eval_provider = PlaceholderEvaluationProvider()
    evaluation = eval_provider.get_evaluation("case_123")

    assert evaluation.action_type == RecoveryActionType.RETRY
    assert evaluation.success_probability == 0.0
    assert evaluation.recoverable_amount == 0
    assert evaluation.action_cost == 0
    assert evaluation.expected_recovery_value == 0
    assert evaluation.model_name == "PHASE4_PLACEHOLDER"
    assert evaluation.model_version == "1.0"


@pytest.mark.asyncio
async def test_orchestration_failure_rolls_back_case_and_audit_mutations() -> None:
    """Test failure originating after real audit append execution rolls back
    case & audit.

    Proves:
    - RecoveryCase created and flushed to DB session inside handle_payment_failed
    - Real AuditEvent append executes and adds AuditEvent to DB session
    - Unexpected failure injected immediately after real audit append execution
    - UnitOfWork exception handling rolls back the entire transaction
    - Fresh independent session confirms BOTH RecoveryCase and AuditEvent are absent
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    from apro.persistence.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    actual_case_id_holder: list[str] = []

    with pytest.raises(RuntimeError, match="Simulated failure after audit append"):
        async with UnitOfWork(factory) as uow:
            await uow.customers.save(
                Customer(customer_id=c_id, created_at=now, updated_at=now)
            )
            payment = await uow.payments.save(
                Payment(
                    payment_id=p_id,
                    customer_id=c_id,
                    provider="razorpay",
                    amount=50000,
                    currency="INR",
                    method="card",
                    status=PaymentStatus.FAILED,
                    created_at=now,
                    updated_at=now,
                )
            )
            evt = PaymentEvent(
                event_id="evt_rollback_1",
                provider="razorpay",
                event_type="payment.failed",
                payment_id=p_id,
                amount=50000,
                currency="INR",
                method="card",
                status=PaymentStatus.FAILED,
                event_timestamp=now,
                received_at=now,
            )

            # Capture original audit_events.append method
            original_append = uow.audit_events.append

            # Wrap original_append to execute real repository append first, then fail
            async def failing_append(audit: Any) -> Any:
                result = await original_append(audit)
                actual_case_id_holder.append(audit.case_id)
                # Prove BOTH case and audit event are present in current
                # uncommitted session
                cases_in_session = await uow.recovery_cases.find_by_payment_id(p_id)
                assert len(cases_in_session) == 1
                audits_in_session = await uow.audit_events.find_by_case_id(
                    audit.case_id
                )
                assert len(audits_in_session) == 1
                raise RuntimeError("Simulated failure after audit append")
                return result

            uow.audit_events.append = failing_append  # type: ignore[assignment]

            orchestrator = RecoveryCaseOrchestrator()
            # handle_payment_failed executes: saves case ->
            # appends real audit event -> fails
            await orchestrator.handle_payment_failed(uow, payment, evt)

    # Verify from a FRESH database session that BOTH case and audit
    # mutations were rolled back
    assert len(actual_case_id_holder) == 1
    actual_case_id = actual_case_id_holder[0]

    async with factory() as fresh_session:
        case_repo = RecoveryCaseRepository(fresh_session)
        audit_repo = AuditEventRepository(fresh_session)

        rolled_back_case = await case_repo.get_by_id(actual_case_id)
        assert rolled_back_case is None  # Case mutation rolled back!

        rolled_back_audits = await audit_repo.find_by_case_id(actual_case_id)
        assert len(rolled_back_audits) == 0  # AuditEvent mutation rolled back!

    await engine.dispose()
