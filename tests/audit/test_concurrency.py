"""Tests for PostgreSQL concurrent audit writes."""

import asyncio
import os
import uuid
from datetime import UTC, datetime

import pytest

from apro.audit.enums import AuditEventType
from apro.domain.enums import AuditActor, PaymentStatus, RecoveryCaseStatus
from apro.domain.models import AuditEvent, Customer, Payment, RecoveryCase
from apro.persistence.database import get_async_engine, get_session_factory
from apro.persistence.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_concurrent_audit_writes_postgres() -> None:
    """Concurrent workers writing audit events succeed concurrently."""
    postgres_url = os.environ.get("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set; skipping database concurrency test")

    engine = get_async_engine(postgres_url)
    session_factory = get_session_factory(engine)

    case_ids = [str(uuid.uuid4()) for _ in range(5)]
    now = datetime.now(UTC)

    # Seed cases first
    async with UnitOfWork(session_factory) as uow:
        for cid_item in case_ids:
            cust_id = str(uuid.uuid4())
            pay_id = str(uuid.uuid4())
            await uow.customers.save(
                Customer(customer_id=cust_id, created_at=now, updated_at=now)
            )
            await uow.payments.save(
                Payment(
                    payment_id=pay_id,
                    customer_id=cust_id,
                    provider="razorpay",
                    amount=10000,
                    currency="INR",
                    method="card",
                    status=PaymentStatus.FAILED,
                    created_at=now,
                    updated_at=now,
                )
            )
            await uow.recovery_cases.save(
                RecoveryCase(
                    case_id=cid_item,
                    payment_id=pay_id,
                    customer_id=cust_id,
                    status=RecoveryCaseStatus.NEW,
                    opened_at=now,
                    updated_at=now,
                    recovery_amount=10000,
                )
            )
        await uow.commit()

    async def emit_audit(case_id_val: str, worker_idx: int) -> None:
        async with UnitOfWork(session_factory) as uow:
            aud = AuditEvent(
                audit_event_id=str(uuid.uuid4()),
                case_id=case_id_val,
                event_type=AuditEventType.DECISION_CREATED,
                actor=AuditActor.MODEL,
                timestamp=datetime.now(UTC),
                payload={"worker": worker_idx},
            )
            await uow.audit_events.append(aud)
            await uow.commit()

    tasks = [emit_audit(cid, i) for i, cid in enumerate(case_ids)]
    await asyncio.gather(*tasks)

    # Verify all 5 written
    async with UnitOfWork(session_factory) as uow:
        for cid in case_ids:
            events = await uow.audit_events.find_by_case_id(cid)
            assert len(events) == 1

    await engine.dispose()
