"""Integration tests for all 13 domain persistence repositories."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apro.domain.enums import (
    AuditActor,
    ExecutionMode,
    ExecutionStatus,
    FailureCategory,
    OutcomeType,
    PaymentStatus,
    PolicyDecisionResult,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import (
    ActionEvaluation,
    AuditEvent,
    Customer,
    Decision,
    Diagnosis,
    Execution,
    Outcome,
    Payment,
    PolicyDecision,
    RecoveryAction,
    RecoveryCase,
)
from apro.persistence.base import Base
from apro.persistence.repositories import (
    ActionEvaluationRepository,
    AuditEventRepository,
    CustomerRepository,
    DecisionRepository,
    DiagnosisRepository,
    ExecutionRepository,
    OutcomeRepository,
    PaymentRepository,
    PolicyDecisionRepository,
    RawEventRepository,
    RecoveryActionRepository,
    RecoveryCaseRepository,
)


async def create_test_session() -> tuple[Any, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    return engine, factory


@pytest.mark.asyncio
async def test_customer_and_payment_repositories() -> None:
    engine, factory = await create_test_session()
    async with factory() as async_session:
        now = datetime.now(UTC)
        cust_repo = CustomerRepository(async_session)
        pay_repo = PaymentRepository(async_session)

        c_id = str(uuid.uuid4())
        p_id = str(uuid.uuid4())

        cust = Customer(
            customer_id=c_id,
            external_reference="ext_1",
            created_at=now,
            updated_at=now,
        )
        saved_cust = await cust_repo.save(cust)
        assert saved_cust.customer_id == c_id

        retrieved_cust = await cust_repo.get_by_id(c_id)
        assert retrieved_cust is not None
        assert retrieved_cust.customer_id == c_id

        pay = Payment(
            payment_id=p_id,
            customer_id=c_id,
            provider="razorpay",
            amount=10000,  # 100 INR in paise
            currency="INR",
            method="card",
            status=PaymentStatus.FAILED,
            created_at=now,
            updated_at=now,
        )
        saved_pay = await pay_repo.save(pay)
        assert saved_pay.payment_id == p_id
        assert saved_pay.amount == 10000

        retrieved_pay = await pay_repo.get_by_id(p_id)
        assert retrieved_pay is not None
        assert retrieved_pay.status == PaymentStatus.FAILED

    await engine.dispose()


@pytest.mark.asyncio
async def test_raw_event_repository() -> None:
    engine, factory = await create_test_session()
    async with factory() as async_session:
        now = datetime.now(UTC)
        raw_repo = RawEventRepository(async_session)
        raw_id = str(uuid.uuid4())

        saved_raw = await raw_repo.save(
            raw_event_id=raw_id,
            provider="razorpay",
            provider_event_id="evt_razor_1",
            event_type="payment.failed",
            received_at=now,
            raw_payload={"event": "payment.failed", "id": "pay_mock_1"},
        )
        assert saved_raw.raw_event_id == raw_id

        found = await raw_repo.find_by_provider_event_id("razorpay", "evt_razor_1")
        assert found is not None
        assert found.raw_payload["id"] == "pay_mock_1"

    await engine.dispose()


@pytest.mark.asyncio
async def test_recovery_case_and_action_repositories() -> None:
    engine, factory = await create_test_session()
    async with factory() as async_session:
        now = datetime.now(UTC)
        cust_repo = CustomerRepository(async_session)
        pay_repo = PaymentRepository(async_session)
        case_repo = RecoveryCaseRepository(async_session)
        act_repo = RecoveryActionRepository(async_session)

        c_id = str(uuid.uuid4())
        p_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        act_id = str(uuid.uuid4())

        await cust_repo.save(Customer(customer_id=c_id, created_at=now, updated_at=now))
        await pay_repo.save(
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

        case = RecoveryCase(
            case_id=case_id,
            payment_id=p_id,
            customer_id=c_id,
            status=RecoveryCaseStatus.NEW,
            opened_at=now,
            updated_at=now,
        )
        await case_repo.save(case)

        found_cases = await case_repo.find_by_payment_id(p_id)
        assert len(found_cases) == 1
        assert found_cases[0].case_id == case_id

        action = RecoveryAction(
            action_id=act_id,
            case_id=case_id,
            action_type=RecoveryActionType.RETRY,
            status=RecoveryActionStatus.CANDIDATE,
            created_at=now,
            updated_at=now,
        )
        await act_repo.save(action)

        found_actions = await act_repo.find_by_case_id(case_id)
        assert len(found_actions) == 1
        assert found_actions[0].action_id == act_id

    await engine.dispose()


@pytest.mark.asyncio
async def test_historical_append_repositories() -> None:
    engine, factory = await create_test_session()
    async with factory() as async_session:
        now = datetime.now(UTC)
        cust_repo = CustomerRepository(async_session)
        pay_repo = PaymentRepository(async_session)
        case_repo = RecoveryCaseRepository(async_session)
        act_repo = RecoveryActionRepository(async_session)
        exec_repo = ExecutionRepository(async_session)
        diag_repo = DiagnosisRepository(async_session)
        eval_repo = ActionEvaluationRepository(async_session)
        dec_repo = DecisionRepository(async_session)
        pdec_repo = PolicyDecisionRepository(async_session)
        out_repo = OutcomeRepository(async_session)
        audit_repo = AuditEventRepository(async_session)

        c_id = str(uuid.uuid4())
        p_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        act_id = str(uuid.uuid4())
        diag_id = str(uuid.uuid4())
        eval_id = str(uuid.uuid4())
        dec_id = str(uuid.uuid4())
        pdec_id = str(uuid.uuid4())
        exec_id = str(uuid.uuid4())
        out_id = str(uuid.uuid4())
        aud_id = str(uuid.uuid4())

        await cust_repo.save(Customer(customer_id=c_id, created_at=now, updated_at=now))
        await pay_repo.save(
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

        # 1. Diagnosis append
        diag = Diagnosis(
            diagnosis_id=diag_id,
            case_id=case_id,
            category=FailureCategory.TRANSIENT,
            confidence=0.9,
            evidence=("timeout",),
            model_name="diag_v1",
            model_version="1.0",
            created_at=now,
        )
        await diag_repo.append(diag)
        assert len(await diag_repo.find_by_case_id(case_id)) == 1

        # 2. Evaluation append
        eval_obj = ActionEvaluation(
            evaluation_id=eval_id,
            case_id=case_id,
            action_type=RecoveryActionType.RETRY,
            success_probability=0.8,
            recoverable_amount=5000,
            action_cost=100,
            expected_recovery_value=3900,
            model_name="eval_v1",
            model_version="1.0",
            created_at=now,
        )
        await eval_repo.append(eval_obj)
        assert len(await eval_repo.find_by_case_id(case_id)) == 1

        # 3. Decision append
        dec = Decision(
            decision_id=dec_id,
            case_id=case_id,
            recommended_action=RecoveryActionType.RETRY,
            confidence=0.85,
            expected_recovery_value=3900,
            reason="Optimal ERV",
            model_name="dec_v1",
            model_version="1.0",
            created_at=now,
        )
        await dec_repo.append(dec)
        assert len(await dec_repo.find_by_case_id(case_id)) == 1

        # 4. Policy Decision append
        pdec = PolicyDecision(
            policy_decision_id=pdec_id,
            decision_id=dec_id,
            case_id=case_id,
            result=PolicyDecisionResult.ALLOW,
            reason="Within policy bounds",
            policy_version="1.0",
            created_at=now,
        )
        await pdec_repo.append(pdec)
        assert len(await pdec_repo.find_by_case_id(case_id)) == 1

        # 5. Execution save
        ex = Execution(
            execution_id=exec_id,
            action_id=act_id,
            case_id=case_id,
            execution_type="standard_retry",
            execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
            status=ExecutionStatus.PENDING,
            started_at=now,
        )
        await exec_repo.save(ex, idempotency_key="idempotency_key_200")
        assert len(await exec_repo.find_by_case_id(case_id)) == 1

        # 6. Outcome append
        out = Outcome(
            outcome_id=out_id,
            case_id=case_id,
            execution_id=exec_id,
            type=OutcomeType.RECOVERED,
            amount_recovered=5000,
            observed_at=now,
        )
        await out_repo.append(out)
        assert len(await out_repo.find_by_case_id(case_id)) == 1

        # 7. Audit Event append
        aud = AuditEvent(
            audit_event_id=aud_id,
            case_id=case_id,
            event_type="CASE_CREATED",
            actor=AuditActor.SYSTEM,
            timestamp=now,
            payload={"action": "created"},
        )
        await audit_repo.append(aud)
        assert len(await audit_repo.find_by_case_id(case_id)) == 1

    await engine.dispose()
