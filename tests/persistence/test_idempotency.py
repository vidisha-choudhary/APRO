"""Integration tests for database-backed event and execution idempotency primitives."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
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
from apro.persistence.base import Base
from apro.persistence.repositories import (
    CustomerRepository,
    ExecutionRepository,
    PaymentRepository,
    RawEventRepository,
    RecoveryActionRepository,
    RecoveryCaseRepository,
)


@pytest.mark.asyncio
async def test_raw_provider_event_idempotency_uniqueness() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    raw_id1 = str(uuid.uuid4())
    raw_id2 = str(uuid.uuid4())

    # Insert first event
    async with factory() as session:
        raw_repo = RawEventRepository(session)
        await raw_repo.save(
            raw_event_id=raw_id1,
            provider="razorpay",
            provider_event_id="evt_duplicate_test_100",
            event_type="payment.failed",
            received_at=now,
            raw_payload={"id": "evt_duplicate_test_100"},
        )
        await session.commit()

    # Attempt second insertion with same (provider, provider_event_id)
    with pytest.raises(IntegrityError):
        async with factory() as session:
            raw_repo = RawEventRepository(session)
            await raw_repo.save(
                raw_event_id=raw_id2,
                provider="razorpay",
                provider_event_id="evt_duplicate_test_100",
                event_type="payment.failed",
                received_at=now,
                raw_payload={"id": "evt_duplicate_test_100"},
            )
            await session.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_execution_idempotency_key_uniqueness() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    act_id = str(uuid.uuid4())
    exec_id1 = str(uuid.uuid4())
    exec_id2 = str(uuid.uuid4())

    async with factory() as session:
        c_repo = CustomerRepository(session)
        p_repo = PaymentRepository(session)
        case_repo = RecoveryCaseRepository(session)
        act_repo = RecoveryActionRepository(session)
        exec_repo = ExecutionRepository(session)

        await c_repo.save(Customer(customer_id=c_id, created_at=now, updated_at=now))
        await p_repo.save(
            Payment(
                payment_id=p_id,
                customer_id=c_id,
                provider="razorpay",
                amount=5000,
                currency="INR",
                method="upi",
                status=PaymentStatus.FAILED,
                created_at=now,
                updated_at=now,
            )
        )
        await case_repo.save(
            RecoveryCase(
                case_id=case_id,
                payment_id=p_id,
                customer_id=c_id,
                status=RecoveryCaseStatus.NEW,
                opened_at=now,
                updated_at=now,
            )
        )
        await act_repo.save(
            RecoveryAction(
                action_id=act_id,
                case_id=case_id,
                action_type=RecoveryActionType.RETRY,
                status=RecoveryActionStatus.APPROVED,
                created_at=now,
                updated_at=now,
            )
        )

        ex1 = Execution(
            execution_id=exec_id1,
            action_id=act_id,
            case_id=case_id,
            execution_type="standard_retry",
            execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
            status=ExecutionStatus.PENDING,
            started_at=now,
        )
        await exec_repo.save(ex1, idempotency_key="idempotency_key_unique_999")
        await session.commit()

    # Attempt second execution with same idempotency key
    with pytest.raises(IntegrityError):
        async with factory() as session:
            exec_repo = ExecutionRepository(session)
            ex2 = Execution(
                execution_id=exec_id2,
                action_id=act_id,
                case_id=case_id,
                execution_type="standard_retry",
                execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
                status=ExecutionStatus.PENDING,
                started_at=now,
            )
            await exec_repo.save(ex2, idempotency_key="idempotency_key_unique_999")
            await session.commit()

    await engine.dispose()
