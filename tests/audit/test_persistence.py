"""Tests for PostgreSQL AuditEvent persistence, querying, and transaction boundaries."""

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
async def test_audit_event_persistence_and_retrieval() -> None:
    """AuditEvent persists atomically with parent case in PostgreSQL."""
    postgres_url = os.environ.get("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set; skipping database persistence test")

    engine = get_async_engine(postgres_url)
    session_factory = get_session_factory(engine)

    cid = str(uuid.uuid4())
    pid = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    aud_id = str(uuid.uuid4())
    trace_id = f"trace_{uuid.uuid4().hex}"
    now = datetime.now(UTC)

    async with UnitOfWork(session_factory) as uow:
        customer = Customer(customer_id=cid, created_at=now, updated_at=now)
        await uow.customers.save(customer)

        payment = Payment(
            payment_id=pid,
            customer_id=cid,
            provider="razorpay",
            amount=25000,
            currency="INR",
            method="upi",
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
            recovery_amount=25000,
        )
        await uow.recovery_cases.save(case)

        audit_ev = AuditEvent(
            audit_event_id=aud_id,
            case_id=case_id,
            event_type=AuditEventType.CASE_CREATED,
            actor=AuditActor.SYSTEM,
            timestamp=now,
            payload={"initial_amount": 25000},
            correlation_id=trace_id,
        )
        await uow.audit_events.append(audit_ev)
        await uow.commit()

    # Query back
    async with UnitOfWork(session_factory) as uow:
        retrieved_by_id = await uow.audit_events.get_by_id(aud_id)
        assert retrieved_by_id is not None
        assert retrieved_by_id.case_id == case_id
        assert retrieved_by_id.payload["initial_amount"] == 25000

        by_case = await uow.audit_events.find_by_case_id(case_id)
        assert len(by_case) == 1
        assert by_case[0].audit_event_id == aud_id

        by_trace = await uow.audit_events.find_by_trace_id(trace_id)
        assert len(by_trace) == 1
        assert by_trace[0].audit_event_id == aud_id

    await engine.dispose()


@pytest.mark.asyncio
async def test_internal_transaction_audit_attachment_failure_raises_error() -> None:
    """When audit session attachment fails, an explicit AuditPersistenceError is raised
    and the transaction does not silently succeed.
    """
    from unittest.mock import MagicMock

    from apro.audit.exceptions import AuditPersistenceError
    from apro.audit.service import AuditService

    service = AuditService()
    failing_uow = MagicMock()
    failing_uow.session = MagicMock()
    failing_uow.session.add.side_effect = RuntimeError(
        "Database connection dropped during audit attach"
    )

    with pytest.raises(AuditPersistenceError) as exc_info:
        service.record_event_sync(
            case_id="case_fail_attach",
            event_type=AuditEventType.DECISION_CREATED,
            payload={"decision": "test"},
            uow=failing_uow,
        )

    assert "Failed to attach audit event to UnitOfWork session" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, RuntimeError)


@pytest.mark.asyncio
async def test_post_dispatch_audit_persistence_failure_preserves_side_effect() -> None:
    """When a provider dispatch succeeds but post-dispatch audit persistence fails:
    1. The external side effect is NOT rolled back or fabricated as nonexistent.
    2. Exactly 1 dispatch occurred.
    3. An explicit AuditPersistenceError is raised to the caller.
    """
    from typing import Any
    from unittest.mock import AsyncMock, MagicMock

    from apro.audit.exceptions import AuditPersistenceError
    from apro.audit.service import AuditService
    from apro.domain.enums import (
        ExecutionMode,
        ExecutionStatus,
        RecoveryActionStatus,
        RecoveryActionType,
    )
    from apro.domain.models import RecoveryAction
    from apro.execution.interfaces import BaseExecutor
    from apro.execution.models import ApprovedExecutionRequest, ExecutionResult
    from apro.execution.orchestrator import ExecutionOrchestrator
    from apro.execution.registry import ExecutorRegistry
    from apro.policy.enums import PolicyOutcome, PolicyReasonCode
    from apro.policy.models import PolicyDecision
    from apro.recovery_prediction.enums import RecoveryAction as PredRecoveryAction

    dispatch_count = 0
    provider_dispatched_ids: list[str] = []

    class MockExternalExecutor(BaseExecutor):
        @property
        def action_type(self) -> RecoveryActionType:
            return RecoveryActionType.ALTERNATE_RECOVERY

        @property
        def supported_modes(self) -> set[ExecutionMode]:
            return {ExecutionMode.SIMULATION}

        def validate(self, request: ApprovedExecutionRequest) -> None:
            _ = request

        async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
            nonlocal dispatch_count
            dispatch_count += 1
            ref_id = f"rzp_plink_{uuid.uuid4().hex[:8]}"
            provider_dispatched_ids.append(ref_id)
            return ExecutionResult(
                execution_id=request.execution_id,
                action_id=request.action_id,
                case_id=request.case_id,
                execution_mode=request.execution_mode,
                status=ExecutionStatus.SUCCEEDED,
                provider_reference=ref_id,
                started_at=request.requested_at,
                completed_at=request.requested_at,
                executor_name="MockExternalExecutor",
                metadata={"status": "created", "id": ref_id},
            )

    registry = ExecutorRegistry()
    registry.register(MockExternalExecutor())

    # Audit service where post-dispatch record_execution_completed fails
    class FailingPostDispatchAuditService(AuditService):
        async def record_execution_completed(
            self,
            execution: Any,
            cycle_number: int = 1,
            uow: Any | None = None,
        ) -> Any:
            _ = (execution, cycle_number, uow)
            raise AuditPersistenceError("Post-dispatch database connection lost")

    failing_audit_service = FailingPostDispatchAuditService()
    orchestrator = ExecutionOrchestrator(
        registry=registry, audit_service=failing_audit_service
    )

    now = datetime.now(UTC)
    case_id = str(uuid.uuid4())
    pol_id = str(uuid.uuid4())
    act_id = str(uuid.uuid4())

    pol = PolicyDecision(
        policy_decision_id=pol_id,
        decision_id="dec_test",
        case_id=case_id,
        payment_id="pay_test",
        requested_action=PredRecoveryAction.PAYMENT_LINK,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=PredRecoveryAction.PAYMENT_LINK,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Allowed for simulation test",
        idempotency_key=f"idem_{case_id}_PAYMENT_LINK_1",
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="1.0.0",
        diagnosis_model_version="1.0.0",
        outcome_model_version="1.0.0",
        created_at=now,
    )
    act = RecoveryAction(
        action_id=act_id,
        case_id=case_id,
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
        execution_mode=ExecutionMode.SIMULATION,
    )
    case = RecoveryCase(
        case_id=case_id,
        payment_id="pay_test",
        customer_id="cust_test",
        status=RecoveryCaseStatus.ACTION_APPROVED,
        opened_at=now,
        updated_at=now,
    )
    payment = Payment(
        payment_id="pay_test",
        customer_id="cust_test",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )

    mock_uow = MagicMock()
    mock_uow.recovery_actions = AsyncMock()
    mock_uow.recovery_cases = AsyncMock()
    mock_uow.executions = AsyncMock()
    mock_uow.executions.find_by_idempotency_key = AsyncMock(return_value=None)
    mock_uow.flush = AsyncMock()
    mock_uow.commit = AsyncMock()

    with pytest.raises(AuditPersistenceError) as exc_info:
        await orchestrator.execute(
            policy_decision=pol,
            recovery_action=act,
            recovery_case=case,
            payment=payment,
            execution_mode=ExecutionMode.SIMULATION,
            current_time=now,
            parameters={"amount": 50000},
            unit_of_work=mock_uow,
        )

    # 1. Verification: Provider dispatch occurred and side effect is preserved
    assert dispatch_count == 1, "Provider dispatch must execute exactly once"
    assert len(provider_dispatched_ids) == 1
    assert provider_dispatched_ids[0].startswith("rzp_plink_")

    # 2. Verification: The failure is surfaced explicitly as AuditPersistenceError
    assert "Post-dispatch database connection lost" in str(exc_info.value)
