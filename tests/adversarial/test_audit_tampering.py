"""Tests for Scenario 7: Audit Tampering, SQL Mutation, and Reconstruction Truth."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import text

from apro.adversarial.assertions import (
    assert_audit_immutability_enforced,
    assert_reconstruction_detects_omission,
)
from apro.adversarial.enums import AttackDisposition
from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.generators import generate_audit_tampering_cases
from apro.audit.enums import AuditCompleteness, AuditEventType
from apro.audit.models import AuditEvent
from apro.audit.reconstruction import CaseReconstructionService
from apro.domain.enums import AuditActor, PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Customer, Payment, RecoveryCase
from apro.persistence.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_scenario_7_audit_tampering_cases(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Scenario 7: Audit tampering cases are detected or blocked."""
    cases = generate_audit_tampering_cases(seed=1701, count=5)

    for case in cases:
        result = await adversarial_executor.execute_case(case)
        assert result.passed is True
        assert result.disposition in (
            AttackDisposition.BLOCKED,
            AttackDisposition.DETECTED,
        )


@pytest.mark.asyncio
async def test_scenario_7_sql_audit_triggers(
    attack_db_session_factory: Any,
) -> None:
    """Scenario 7: Direct SQL UPDATE and DELETE on audit_events are rejected by PostgreSQL triggers."""
    cid = str(uuid.uuid4())
    pid = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    aud_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    async with UnitOfWork(attack_db_session_factory) as uow:
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
        await uow.audit_events.append(
            AuditEvent(
                audit_event_id=aud_id,
                case_id=case_id,
                event_type=AuditEventType.CASE_CREATED,
                actor=AuditActor.SYSTEM,
                timestamp=now,
                payload={"initial": True},
            )
        )
        await uow.commit()

    # Attempt direct SQL UPDATE
    update_blocked = False
    try:
        async with attack_db_session_factory() as session, session.begin():
            await session.execute(
                text(
                    "UPDATE audit_events SET payload = '{\"tampered\": true}' WHERE audit_event_id = :id;"
                ),
                {"id": aud_id},
            )
    except Exception as exc:
        err_msg = str(exc).lower()
        if (
            "audit_events is append-only" in err_msg
            or "trg_audit_events_immutability" in err_msg
        ):
            update_blocked = True

    assert update_blocked is True

    # Verify row unchanged after UPDATE attempt
    async with attack_db_session_factory() as session:
        res = await session.execute(
            text(
                "SELECT audit_event_id, event_type, payload FROM audit_events WHERE audit_event_id = :id;"
            ),
            {"id": aud_id},
        )
        row = res.fetchone()
        assert row is not None
        assert str(row[0]) == str(aud_id)
        assert str(row[1]) == "CASE_CREATED"
        assert row[2] in ({"initial": True}, '{"initial": true}', '{"initial": True}')

    # Attempt direct SQL DELETE
    delete_blocked = False
    try:
        async with attack_db_session_factory() as session, session.begin():
            await session.execute(
                text("DELETE FROM audit_events WHERE audit_event_id = :id;"),
                {"id": aud_id},
            )
    except Exception as exc:
        err_msg = str(exc).lower()
        if (
            "audit_events is append-only" in err_msg
            or "trg_audit_events_immutability" in err_msg
        ):
            delete_blocked = True

    assert delete_blocked is True

    # Verify row unchanged (still exists) after DELETE attempt
    async with attack_db_session_factory() as session:
        res = await session.execute(
            text(
                "SELECT audit_event_id, event_type, payload FROM audit_events WHERE audit_event_id = :id;"
            ),
            {"id": aud_id},
        )
        row = res.fetchone()
        assert row is not None
        assert str(row[0]) == str(aud_id)

    assert_audit_immutability_enforced(
        attempted_updates=1,
        attempted_deletes=1,
        blocked_updates=1,
        blocked_deletes=1,
    )


@pytest.mark.asyncio
async def test_scenario_7_missing_stages_reconstruction() -> None:
    """Scenario 7: Reconstruction accurately surfaces missing lifecycle stages as INCOMPLETE."""
    now = datetime.now(UTC)
    case_obj = RecoveryCase(
        case_id="case_partial_001",
        payment_id="pay_partial_001",
        customer_id="cust_partial_001",
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
    )
    events = [
        AuditEvent(
            audit_event_id="ev_only_start_001",
            case_id="case_partial_001",
            event_type=AuditEventType.CASE_CREATED,
            actor=AuditActor.SYSTEM,
            timestamp=now,
            payload={"reason": "TIMEOUT"},
        )
    ]

    trace = await CaseReconstructionService.reconstruct_case(
        case_id="case_partial_001",
        case=case_obj,
        audit_events=events,
    )

    assert trace.completeness == AuditCompleteness.INCOMPLETE
    assert_reconstruction_detects_omission(trace)
