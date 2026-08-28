"""Integration tests for concurrent operations and state update races."""

import asyncio
import os
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
from apro.domain.exceptions import InvalidStateTransitionError
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
async def test_concurrent_same_event_insertion_race(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Rework #6: Genuine concurrent event insertion race using asyncio.gather."""
    db_file = tmp_path / "test_concurrency_1.db"
    db_url = os.getenv("POSTGRES_TEST_URL", f"sqlite+aiosqlite:///{db_file}")

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    race_evt_id = f"evt_race_concurrent_{uuid.uuid4().hex[:8]}"

    async def worker(_worker_id: str):  # type: ignore[no-untyped-def]
        async with factory() as session:
            repo = RawEventRepository(session)
            raw_id = str(uuid.uuid4())
            await repo.save(
                raw_event_id=raw_id,
                provider="razorpay",
                provider_event_id=race_evt_id,
                event_type="payment.failed",
                received_at=now,
                raw_payload={"id": race_evt_id},
            )
            await session.commit()

    # Launch worker 1 and worker 2 concurrently
    results = await asyncio.gather(worker("w1"), worker("w2"), return_exceptions=True)

    # Verify exactly one succeeded and one raised IntegrityError
    successes = [r for r in results if not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], IntegrityError)

    # Verify only 1 event exists in database
    async with factory() as session:
        repo = RawEventRepository(session)
        event = await repo.find_by_provider_event_id("razorpay", race_evt_id)
        assert event is not None

    await engine.dispose()


@pytest.mark.asyncio
async def test_state_dependent_conditional_update_race(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Correction A: Genuine concurrent state-dependent update race with barrier."""
    db_file = tmp_path / "test_concurrency_2.db"
    db_url = os.getenv("POSTGRES_TEST_URL", f"sqlite+aiosqlite:///{db_file}")

    engine = create_async_engine(db_url, echo=False)
    if engine.dialect.name == "sqlite":
        await engine.dispose()
        pytest.skip("SQLite file locking does not support MVCC concurrency races")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())

    # Setup initial payment state
    async with factory() as session:
        c_repo = CustomerRepository(session)
        p_repo = PaymentRepository(session)
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
        await session.commit()

    start_event = asyncio.Event()

    async def worker_a():  # type: ignore[no-untyped-def]
        async with factory() as s1:
            p_repo1 = PaymentRepository(s1)
            pay1 = await p_repo1.get_by_id(p_id)
            assert pay1 is not None
            pay1.status = PaymentStatus.PENDING
            await start_event.wait()
            await p_repo1.update_status_conditional(
                pay1, expected_status=PaymentStatus.FAILED
            )
            await s1.commit()

    async def worker_b():  # type: ignore[no-untyped-def]
        async with factory() as s2:
            p_repo2 = PaymentRepository(s2)
            pay2 = await p_repo2.get_by_id(p_id)
            assert pay2 is not None
            pay2.status = PaymentStatus.CAPTURED
            await start_event.wait()
            await p_repo2.update_status_conditional(
                pay2, expected_status=PaymentStatus.FAILED
            )
            await s2.commit()

    task_a = asyncio.create_task(worker_a())
    task_b = asyncio.create_task(worker_b())

    await asyncio.sleep(0.05)
    start_event.set()

    results = await asyncio.gather(task_a, task_b, return_exceptions=True)

    successes = [r for r in results if not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], (InvalidStateTransitionError, Exception))

    await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_execution_idempotency_key_race(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Rework #6: Genuine concurrent execution idempotency key race."""
    db_file = tmp_path / "test_concurrency_3.db"
    db_url = os.getenv("POSTGRES_TEST_URL", f"sqlite+aiosqlite:///{db_file}")

    engine = create_async_engine(db_url, echo=False)
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
    race_idem_key = f"idempotency_key_race_{uuid.uuid4().hex[:8]}"

    async with factory() as session:
        c_repo = CustomerRepository(session)
        p_repo = PaymentRepository(session)
        case_repo = RecoveryCaseRepository(session)
        act_repo = RecoveryActionRepository(session)

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
        await session.commit()

    async def exec_worker(exec_id: str):  # type: ignore[no-untyped-def]
        async with factory() as session:
            exec_repo = ExecutionRepository(session)
            ex = Execution(
                execution_id=exec_id,
                action_id=act_id,
                case_id=case_id,
                execution_type="standard_retry",
                execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
                status=ExecutionStatus.PENDING,
                started_at=now,
            )
            await exec_repo.save(ex, idempotency_key=race_idem_key)
            await session.commit()

    exec_id1 = str(uuid.uuid4())
    exec_id2 = str(uuid.uuid4())

    # Launch two workers creating execution with identical idempotency key concurrently
    results = await asyncio.gather(
        exec_worker(exec_id1),
        exec_worker(exec_id2),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], IntegrityError)

    await engine.dispose()
