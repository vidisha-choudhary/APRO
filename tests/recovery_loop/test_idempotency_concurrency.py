"""Tests proving outcome idempotency and concurrency in Phase 13."""

import asyncio
import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

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
    Customer,
    Execution,
    Payment,
    RecoveryAction,
    RecoveryCase,
)
from apro.persistence.models import OutcomeModel
from apro.persistence.unit_of_work import UnitOfWork
from apro.recovery_loop.enums import EvidenceType, RecoveryLoopDisposition
from apro.recovery_loop.models import OutcomeEvidence
from apro.recovery_loop.outcomes import OutcomeProcessor


def get_pg_url() -> str | None:
    return os.getenv("POSTGRES_TEST_URL")


async def check_pg(url: str) -> bool:
    try:
        engine = create_async_engine(url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


@pytest.mark.asyncio
async def test_duplicate_outcome_processing_is_idempotent_in_memory() -> None:
    """Duplicate outcome evidence produces identical result and 0 duplicate
    state mutations.
    """
    processor = OutcomeProcessor()
    now = datetime.now(UTC)

    payment = Payment(
        payment_id="pay_idem_01",
        customer_id="cust_idem_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_idem_01",
        payment_id="pay_idem_01",
        customer_id="cust_idem_01",
        status=RecoveryCaseStatus.OBSERVING,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )
    evidence = OutcomeEvidence(
        evidence_id="ev_idem_01",
        case_id="case_idem_01",
        execution_id="exec_idem_01",
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=now,
    )

    # First call
    res1, case1, pay1 = await processor.process_outcome(
        evidence=evidence,
        case=case,
        payment=payment,
    )
    assert res1.outcome.type == OutcomeType.RECOVERED
    assert res1.disposition == RecoveryLoopDisposition.COMPLETE
    assert case1.status == RecoveryCaseStatus.RECOVERED

    # Duplicate call with same evidence
    res2, case2, pay2 = await processor.process_outcome(
        evidence=evidence,
        case=case1,
        payment=pay1,
    )
    assert res2.outcome.outcome_id == res1.outcome.outcome_id
    assert res2.outcome.type == OutcomeType.RECOVERED
    assert res2.disposition == RecoveryLoopDisposition.COMPLETE
    assert case2.status == RecoveryCaseStatus.RECOVERED


@pytest.mark.asyncio
async def test_duplicate_and_concurrent_outcome_processing_postgres() -> None:
    """Guardrail 4: Verify duplicate and concurrent outcome processing on real
    PostgreSQL path.
    """
    pg_url = get_pg_url()
    if not pg_url or not await check_pg(pg_url):
        pytest.skip("PostgreSQL test database not available.")

    engine = create_async_engine(pg_url, echo=False)
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    case_uuid = str(uuid.uuid4())
    pay_uuid = str(uuid.uuid4())
    cust_uuid = str(uuid.uuid4())
    act_uuid = str(uuid.uuid4())
    exec_uuid = str(uuid.uuid4())
    now = datetime.now(UTC)

    customer = Customer(
        customer_id=cust_uuid,
        email="test_idem@example.com",
        phone="+919876543210",
        name="Idem Customer",
        created_at=now,
        updated_at=now,
    )
    payment = Payment(
        payment_id=pay_uuid,
        customer_id=cust_uuid,
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id=case_uuid,
        payment_id=pay_uuid,
        customer_id=cust_uuid,
        status=RecoveryCaseStatus.OBSERVING,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )
    action = RecoveryAction(
        action_id=act_uuid,
        case_id=case_uuid,
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
        execution_mode=ExecutionMode.SIMULATION,
        parameters={"amount": 50000},
    )
    execution = Execution(
        execution_id=exec_uuid,
        action_id=act_uuid,
        case_id=case_uuid,
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.FAILED,
        started_at=now,
        completed_at=now,
    )

    # Insert baseline entities
    async with UnitOfWork(session_factory) as uow:
        await uow.customers.save(customer)
        await uow.payments.save(payment)
        await uow.recovery_cases.save(case)
        await uow.recovery_actions.save(action)
        await uow.executions.save(execution)
        await uow.commit()

    processor = OutcomeProcessor()
    evidence = OutcomeEvidence(
        evidence_id=f"ev_db_{uuid.uuid4()}",
        case_id=case_uuid,
        execution_id=exec_uuid,
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=now,
    )

    # Concurrently process the same outcome using two separate UoW contexts
    async def worker():
        async with UnitOfWork(session_factory) as uow:
            loaded_case = await uow.recovery_cases.get_by_id(case_uuid)
            loaded_payment = await uow.payments.get_by_id(pay_uuid)
            assert loaded_case is not None and loaded_payment is not None
            res, _, _ = await processor.process_outcome(
                evidence=evidence,
                case=loaded_case,
                payment=loaded_payment,
                execution=execution,
                uow=uow,
            )
            await uow.commit()
            return res

    results = await asyncio.gather(worker(), worker(), return_exceptions=False)

    # Both workers must succeed without error and return identical outcome ID
    assert len(results) == 2
    res_a, res_b = results[0], results[1]
    assert res_a.outcome.outcome_id == res_b.outcome.outcome_id
    assert res_a.outcome.type == OutcomeType.RECOVERED
    assert res_b.outcome.type == OutcomeType.RECOVERED
    assert res_a.disposition == RecoveryLoopDisposition.COMPLETE
    assert res_b.disposition == RecoveryLoopDisposition.COMPLETE

    # Verify exactly 1 Outcome row exists in PostgreSQL
    async with UnitOfWork(session_factory) as uow:
        stmt = select(OutcomeModel).where(OutcomeModel.case_id == case_uuid)
        db_res = await uow.session.execute(stmt)
        outcome_rows = list(db_res.scalars())
        assert len(outcome_rows) == 1
        assert outcome_rows[0].type == OutcomeType.RECOVERED.value

    await engine.dispose()
