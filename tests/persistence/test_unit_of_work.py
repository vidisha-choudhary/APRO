"""Integration tests for Unit of Work transaction manager."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Customer, Payment, RecoveryCase
from apro.persistence.base import Base
from apro.persistence.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_unit_of_work_commit_and_rollback() -> None:
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
    c_rollback_id = str(uuid.uuid4())

    # 1. Successful commit
    async with UnitOfWork(factory) as uow:
        await uow.customers.save(
            Customer(customer_id=c_id, created_at=now, updated_at=now)
        )
        await uow.payments.save(
            Payment(
                payment_id=p_id,
                customer_id=c_id,
                provider="razorpay",
                amount=2500,
                currency="INR",
                method="upi",
                status=PaymentStatus.FAILED,
                created_at=now,
                updated_at=now,
            )
        )
        await uow.recovery_cases.save(
            RecoveryCase(
                case_id=case_id,
                payment_id=p_id,
                customer_id=c_id,
                status=RecoveryCaseStatus.NEW,
                opened_at=now,
                updated_at=now,
            )
        )
        await uow.commit()

    # Verify atomic multi-write committed
    async with UnitOfWork(factory) as uow:
        retrieved_pay = await uow.payments.get_by_id(p_id)
        assert retrieved_pay is not None
        retrieved_case = await uow.recovery_cases.get_by_id(case_id)
        assert retrieved_case is not None

    # 2. Failed transaction rollback
    try:
        async with UnitOfWork(factory) as uow:
            await uow.customers.save(
                Customer(customer_id=c_rollback_id, created_at=now, updated_at=now)
            )
            # Raise artificial exception before commit
            raise RuntimeError("Artificial transaction failure")
    except RuntimeError:
        pass

    # Verify rollback succeeded and customer does not exist
    async with UnitOfWork(factory) as uow:
        rolled_back_cust = await uow.customers.get_by_id(c_rollback_id)
        assert rolled_back_cust is None

    await engine.dispose()
