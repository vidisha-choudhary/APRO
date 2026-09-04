"""Tests for audit record immutability at domain, ORM, and database levels."""

import os
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, InternalError, ProgrammingError

from apro.audit.enums import AuditEventType
from apro.audit.exceptions import AuditImmutabilityError
from apro.domain.enums import AuditActor, PaymentStatus, RecoveryCaseStatus
from apro.domain.models import AuditEvent, Customer, Payment, RecoveryCase
from apro.persistence.database import get_async_engine, get_session_factory
from apro.persistence.models import AuditEventModel
from apro.persistence.unit_of_work import UnitOfWork


def test_domain_audit_event_immutability() -> None:
    """AuditEvent Pydantic instance is frozen and cannot be mutated."""
    ev = AuditEvent(
        audit_event_id="aud_immut",
        case_id="case_immut",
        event_type=AuditEventType.CASE_CREATED,
        actor=AuditActor.SYSTEM,
        timestamp=datetime.now(UTC),
        payload={"immutable": True},
    )
    with pytest.raises(ValidationError, match="Instance is frozen"):
        ev.payload = {"immutable": False}  # type: ignore[misc]


@pytest.mark.asyncio
async def test_persistence_audit_event_immutability() -> None:
    """Persisted AuditEventModel rejects UPDATE and DELETE operations via ORM."""
    postgres_url = os.environ.get("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set; skipping database immutability test")

    engine = get_async_engine(postgres_url)
    session_factory = get_session_factory(engine)

    cid = str(uuid.uuid4())
    pid = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    aud_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    async with UnitOfWork(session_factory) as uow:
        # Seed parent records
        customer = Customer(
            customer_id=cid,
            created_at=now,
            updated_at=now,
        )
        await uow.customers.save(customer)

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
        await uow.payments.save(payment)

        case = RecoveryCase(
            case_id=case_id,
            payment_id=pid,
            customer_id=cid,
            status=RecoveryCaseStatus.NEW,
            opened_at=now,
            updated_at=now,
            recovery_amount=50000,
        )
        await uow.recovery_cases.save(case)

        audit_ev = AuditEvent(
            audit_event_id=aud_id,
            case_id=case_id,
            event_type=AuditEventType.CASE_CREATED,
            actor=AuditActor.SYSTEM,
            timestamp=now,
            payload={"initial": True},
        )
        await uow.audit_events.append(audit_ev)
        await uow.commit()

    # Attempt mutation through ORM
    async with UnitOfWork(session_factory) as uow:
        assert uow.session is not None
        orm = await uow.session.get(AuditEventModel, aud_id)
        assert orm is not None
        orm.event_type = "MUTATED_TYPE"

        with pytest.raises(
            AuditImmutabilityError, match="is immutable and cannot be updated"
        ):
            await uow.commit()

    # Attempt deletion through ORM
    async with UnitOfWork(session_factory) as uow:
        assert uow.session is not None
        orm = await uow.session.get(AuditEventModel, aud_id)
        assert orm is not None
        await uow.session.delete(orm)

        with pytest.raises(
            AuditImmutabilityError, match="is immutable and cannot be deleted"
        ):
            await uow.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_direct_sql_audit_event_immutability_postgres() -> None:
    """PostgreSQL database trigger strictly rejects raw SQL UPDATE and DELETE."""
    postgres_url = os.environ.get("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set; skipping database immutability test")

    engine = get_async_engine(postgres_url)
    session_factory = get_session_factory(engine)

    cid = str(uuid.uuid4())
    pid = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    aud_id = str(uuid.uuid4())
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
        await uow.recovery_cases.save(
            RecoveryCase(
                case_id=case_id,
                payment_id=pid,
                customer_id=cid,
                status=RecoveryCaseStatus.NEW,
                opened_at=now,
                updated_at=now,
                recovery_amount=50000,
            )
        )
        # INSERT succeeds
        audit_ev = AuditEvent(
            audit_event_id=aud_id,
            case_id=case_id,
            event_type=AuditEventType.CASE_CREATED,
            actor=AuditActor.SYSTEM,
            timestamp=now,
            payload={"initial": True},
        )
        await uow.audit_events.append(audit_ev)
        await uow.commit()

    # Direct raw SQL UPDATE must be rejected by PostgreSQL trigger
    async with UnitOfWork(session_factory) as uow:
        assert uow.session is not None
        stmt_update = text(
            "UPDATE audit_events SET event_type = 'SQL_MUTATED' "
            "WHERE audit_event_id = :id"
        )
        with pytest.raises(
            (DBAPIError, InternalError, ProgrammingError), match="append-only"
        ):
            await uow.session.execute(stmt_update, {"id": aud_id})
            await uow.session.commit()

    # Direct raw SQL DELETE must be rejected by PostgreSQL trigger
    async with UnitOfWork(session_factory) as uow:
        assert uow.session is not None
        stmt_delete = text("DELETE FROM audit_events WHERE audit_event_id = :id")
        with pytest.raises(
            (DBAPIError, InternalError, ProgrammingError), match="append-only"
        ):
            await uow.session.execute(stmt_delete, {"id": aud_id})
            await uow.session.commit()

    await engine.dispose()
