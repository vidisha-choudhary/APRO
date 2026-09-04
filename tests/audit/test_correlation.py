"""Tests for correlation propagation and concurrent async context isolation."""

import asyncio

import pytest

from apro.audit.correlation import (
    async_correlation_scope,
    clear_correlation_context,
    correlation_scope,
    get_correlation_context,
)


def test_correlation_scope_sync() -> None:
    """Sync correlation scope correctly sets and resets context."""
    clear_correlation_context()
    assert get_correlation_context().case_id is None

    with correlation_scope(case_id="case_1", trace_id="trace_1", cycle_id=1):
        ctx = get_correlation_context()
        assert ctx.case_id == "case_1"
        assert ctx.trace_id == "trace_1"
        assert ctx.cycle_id == 1

    assert get_correlation_context().case_id is None


@pytest.mark.asyncio
async def test_correlation_scope_async() -> None:
    """Async correlation scope correctly sets and resets context."""
    clear_correlation_context()
    async with async_correlation_scope(
        case_id="case_async", trace_id="trace_async", cycle_id=2
    ):
        ctx = get_correlation_context()
        assert ctx.case_id == "case_async"
        assert ctx.trace_id == "trace_async"
        assert ctx.cycle_id == 2

    assert get_correlation_context().case_id is None


@pytest.mark.asyncio
async def test_concurrent_context_isolation() -> None:
    """Two concurrent async tasks do not cross-contaminate correlation contexts."""
    results_a: list[str | None] = []
    results_b: list[str | None] = []

    async def worker_a() -> None:
        async with async_correlation_scope(
            case_id="case_A", trace_id="trace_A", cycle_id=1
        ):
            for _ in range(5):
                await asyncio.sleep(0.01)
                results_a.append(get_correlation_context().case_id)

    async def worker_b() -> None:
        async with async_correlation_scope(
            case_id="case_B", trace_id="trace_B", cycle_id=2
        ):
            for _ in range(5):
                await asyncio.sleep(0.01)
                results_b.append(get_correlation_context().case_id)

    await asyncio.gather(worker_a(), worker_b())

    assert len(results_a) == 5
    assert all(c == "case_A" for c in results_a)
    assert len(results_b) == 5
    assert all(c == "case_B" for c in results_b)


@pytest.mark.asyncio
async def test_concurrent_real_lifecycle_correlation_postgres() -> None:
    """Two concurrent APRO case operations execute through the real
    ExecutionOrchestrator boundary and record audit events to PostgreSQL
    without cross-contamination of correlation IDs (case_id, trace_id).
    """
    import os
    import uuid
    from datetime import UTC, datetime

    from apro.audit.enums import AuditEventType
    from apro.audit.service import AuditService
    from apro.domain.enums import (
        ExecutionMode,
        PaymentStatus,
        RecoveryActionStatus,
        RecoveryActionType,
        RecoveryCaseStatus,
    )
    from apro.domain.models import Customer, Payment, RecoveryAction, RecoveryCase
    from apro.execution.orchestrator import ExecutionOrchestrator
    from apro.persistence.database import get_async_engine, get_session_factory
    from apro.persistence.unit_of_work import UnitOfWork
    from apro.policy.enums import PolicyOutcome, PolicyReasonCode
    from apro.policy.models import PolicyDecision
    from apro.recovery_prediction.enums import RecoveryAction as PredictRecoveryAction

    postgres_url = os.environ.get("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set; skipping database correlation test")

    engine = get_async_engine(postgres_url)
    session_factory = get_session_factory(engine)
    audit_service = AuditService()
    orchestrator = ExecutionOrchestrator(audit_service=audit_service)

    case_a = str(uuid.uuid4())
    trace_a = f"trace_A_{uuid.uuid4()}"
    case_b = str(uuid.uuid4())
    trace_b = f"trace_B_{uuid.uuid4()}"
    cid = str(uuid.uuid4())
    pid_a = str(uuid.uuid4())
    pid_b = str(uuid.uuid4())
    act_a_id = str(uuid.uuid4())
    act_b_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    payment_a = Payment(
        payment_id=pid_a,
        customer_id=cid,
        provider="razorpay",
        amount=10000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    payment_b = Payment(
        payment_id=pid_b,
        customer_id=cid,
        provider="razorpay",
        amount=20000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case_obj_a = RecoveryCase(
        case_id=case_a,
        payment_id=pid_a,
        customer_id=cid,
        status=RecoveryCaseStatus.ACTION_APPROVED,
        opened_at=now,
        updated_at=now,
    )
    case_obj_b = RecoveryCase(
        case_id=case_b,
        payment_id=pid_b,
        customer_id=cid,
        status=RecoveryCaseStatus.ACTION_APPROVED,
        opened_at=now,
        updated_at=now,
    )
    action_a = RecoveryAction(
        action_id=act_a_id,
        case_id=case_a,
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    action_b = RecoveryAction(
        action_id=act_b_id,
        case_id=case_b,
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
        parameters={"amount": 20000},
    )

    pol_a = PolicyDecision(
        policy_decision_id=f"pol_{uuid.uuid4()}",
        case_id=case_a,
        payment_id=pid_a,
        decision_id=f"dec_{uuid.uuid4()}",
        requested_action=PredictRecoveryAction.RETRY,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=PredictRecoveryAction.RETRY,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Allowed",
        idempotency_key=f"idem_{case_a}_retry_1",
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        created_at=now,
    )
    pol_b = PolicyDecision(
        policy_decision_id=f"pol_{uuid.uuid4()}",
        case_id=case_b,
        payment_id=pid_b,
        decision_id=f"dec_{uuid.uuid4()}",
        requested_action=PredictRecoveryAction.PAYMENT_LINK,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=PredictRecoveryAction.PAYMENT_LINK,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Allowed",
        idempotency_key=f"idem_{case_b}_plink_1",
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        created_at=now,
    )

    async with UnitOfWork(session_factory) as uow_init:
        await uow_init.customers.save(
            Customer(customer_id=cid, created_at=now, updated_at=now)
        )
        await uow_init.payments.save(payment_a)
        await uow_init.payments.save(payment_b)
        await uow_init.recovery_cases.save(case_obj_a)
        await uow_init.recovery_cases.save(case_obj_b)
        await uow_init.recovery_actions.save(action_a)
        await uow_init.recovery_actions.save(action_b)
        await uow_init.commit()

    async def worker_case_a() -> None:
        async with async_correlation_scope(
            case_id=case_a, trace_id=trace_a, cycle_id=1
        ):
            await asyncio.sleep(0.01)
            async with UnitOfWork(session_factory) as uow:
                await orchestrator.execute(
                    policy_decision=pol_a,
                    recovery_action=action_a,
                    recovery_case=case_obj_a,
                    payment=payment_a,
                    execution_mode=ExecutionMode.SIMULATION,
                    unit_of_work=uow,
                )

    async def worker_case_b() -> None:
        async with async_correlation_scope(
            case_id=case_b, trace_id=trace_b, cycle_id=2
        ):
            await asyncio.sleep(0.01)
            async with UnitOfWork(session_factory) as uow:
                await orchestrator.execute(
                    policy_decision=pol_b,
                    recovery_action=action_b,
                    recovery_case=case_obj_b,
                    payment=payment_b,
                    execution_mode=ExecutionMode.SIMULATION,
                    parameters={"amount": 20000},
                    unit_of_work=uow,
                )

    await asyncio.gather(worker_case_a(), worker_case_b())

    async with UnitOfWork(session_factory) as uow:
        events_a = await uow.audit_events.find_by_case_id(case_a)
        events_b = await uow.audit_events.find_by_case_id(case_b)

    assert len(events_a) == 2
    assert len(events_b) == 2
    assert trace_a != trace_b

    types_a = [e.event_type for e in events_a]
    assert AuditEventType.EXECUTION_STARTED.value in types_a
    assert AuditEventType.EXECUTION_COMPLETED.value in types_a

    types_b = [e.event_type for e in events_b]
    assert AuditEventType.EXECUTION_STARTED.value in types_b
    assert AuditEventType.EXECUTION_COMPLETED.value in types_b

    for ev in events_a:
        assert ev.case_id == case_a
        assert ev.correlation_id == trace_a
        assert ev.correlation_id != trace_b

    for ev in events_b:
        assert ev.case_id == case_b
        assert ev.correlation_id == trace_b
        assert ev.correlation_id != trace_a

    await engine.dispose()
