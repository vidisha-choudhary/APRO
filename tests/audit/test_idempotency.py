"""Tests for idempotent audit event handling."""

import os
import uuid
from datetime import UTC, datetime

import pytest

from apro.audit.enums import AuditEventType
from apro.audit.service import AuditService
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Customer, Payment, RecoveryCase
from apro.persistence.database import get_async_engine, get_session_factory
from apro.persistence.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_in_memory_idempotency() -> None:
    """AuditService suppresses in-memory duplicate event deliveries."""
    service = AuditService()
    ev1 = await service.record_event(
        case_id="case_idem_1",
        event_type=AuditEventType.DECISION_CREATED,
        source_id="dec_123",
        sequence=1,
        payload={"action": "RETRY"},
    )
    ev2 = await service.record_event(
        case_id="case_idem_1",
        event_type=AuditEventType.DECISION_CREATED,
        source_id="dec_123",
        sequence=1,
        payload={"action": "RETRY"},
    )
    assert ev1.audit_event_id == ev2.audit_event_id
    assert len(service.get_in_memory_events("case_idem_1")) == 1


@pytest.mark.asyncio
async def test_postgres_idempotency() -> None:
    """AuditService persists exactly one durable event in PostgreSQL."""
    postgres_url = os.environ.get("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set; skipping database idempotency test")

    engine = get_async_engine(postgres_url)
    session_factory = get_session_factory(engine)

    cid = str(uuid.uuid4())
    pid = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
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
                amount=15000,
                currency="INR",
                method="card",
                status=PaymentStatus.FAILED,
                created_at=now,
                updated_at=now,
            )
        )
        await uow.recovery_cases.save(
            RecoveryCase(
                case_id=case_id,
                payment_id=pid,
                customer_id=cid,
                status=RecoveryCaseStatus.NEW,
                opened_at=now,
                updated_at=now,
                recovery_amount=15000,
            )
        )
        await uow.commit()

    service = AuditService()

    # Delivery 1
    async with UnitOfWork(session_factory) as uow:
        ev1 = await service.record_event(
            case_id=case_id,
            event_type=AuditEventType.DECISION_CREATED,
            source_id="dec_999",
            sequence=1,
            payload={"attempt": 1},
            uow=uow,
        )
        await uow.commit()

    # Delivery 2 (same logical event)
    async with UnitOfWork(session_factory) as uow:
        ev2 = await service.record_event(
            case_id=case_id,
            event_type=AuditEventType.DECISION_CREATED,
            source_id="dec_999",
            sequence=1,
            payload={"attempt": 1},
            uow=uow,
        )
        await uow.commit()

    assert ev1.audit_event_id == ev2.audit_event_id

    # Verify only 1 row in DB
    async with UnitOfWork(session_factory) as uow:
        rows = await uow.audit_events.find_by_case_id(case_id)
        assert len(rows) == 1

    await engine.dispose()
