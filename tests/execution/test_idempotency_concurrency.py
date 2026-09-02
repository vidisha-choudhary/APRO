"""Unit and integration tests for execution idempotency and concurrency."""

import asyncio
import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Customer, Payment, RecoveryAction, RecoveryCase
from apro.execution.executors.retry import SimulationRetryExecutor
from apro.execution.models import ApprovedExecutionRequest, ExecutionResult
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.execution.registry import ExecutorRegistry
from apro.persistence.models import ExecutionModel
from apro.persistence.unit_of_work import UnitOfWork
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import PolicyDecision
from apro.recovery_prediction.enums import RecoveryAction as PredictRecoveryAction

DEFAULT_PG_URL = (
    "postgresql+asyncpg://postgres:postgres_local_dev_2026@127.0.0.1:5432/apro_test_db"
)


def get_pg_url() -> str:
    url = os.getenv("POSTGRES_TEST_URL", DEFAULT_PG_URL)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def check_pg(url: str) -> bool:
    try:
        engine = create_async_engine(url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


def _make_fixture() -> tuple[
    PolicyDecision, RecoveryAction, RecoveryCase, Payment, Customer
]:
    now = datetime.now(UTC)
    cust_id = str(uuid.uuid4())
    pay_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    act_id = str(uuid.uuid4())
    pol_id = str(uuid.uuid4())
    dec_id = str(uuid.uuid4())
    idem_key = f"idem_{case_id}_RETRY_1"

    cust = Customer(
        customer_id=cust_id,
        created_at=now,
        updated_at=now,
    )
    pay = Payment(
        payment_id=pay_id,
        customer_id=cust_id,
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id=case_id,
        payment_id=pay_id,
        customer_id=cust_id,
        status=RecoveryCaseStatus.ACTION_APPROVED,
        opened_at=now,
        updated_at=now,
    )
    act = RecoveryAction(
        action_id=act_id,
        case_id=case_id,
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    pol = PolicyDecision(
        policy_decision_id=pol_id,
        case_id=case_id,
        payment_id=pay_id,
        decision_id=dec_id,
        requested_action=PredictRecoveryAction.RETRY,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=PredictRecoveryAction.RETRY,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Policy allow",
        idempotency_key=idem_key,
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        created_at=now,
    )
    return pol, act, case, pay, cust


class CountingRetryExecutor(SimulationRetryExecutor):
    """Executor instrumented with call count tracking and simulated dispatch latency."""

    def __init__(self) -> None:
        super().__init__()
        self.invocation_count = 0

    async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
        self.invocation_count += 1
        await asyncio.sleep(0.03)  # Simulate real execution window
        return await super().execute(request)


@pytest.mark.asyncio
async def test_in_memory_idempotency_duplicate_protection() -> None:
    """Verify in-memory duplicate claims return existing execution."""
    pol, act, case, pay, _ = _make_fixture()
    orchestrator = ExecutionOrchestrator()

    res1 = await orchestrator.execute(pol, act, case, pay, ExecutionMode.SIMULATION)
    res2 = await orchestrator.execute(pol, act, case, pay, ExecutionMode.SIMULATION)

    assert res1.execution_id == res2.execution_id
    assert res1.status == ExecutionStatus.SUCCEEDED
    assert res2.status == ExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_in_memory_concurrent_duplicate_claims_at_most_one_dispatch() -> None:
    """Verify in-memory lock prevents concurrent overlapping double dispatch."""
    pol, act, case, pay, _ = _make_fixture()
    counting_executor = CountingRetryExecutor()
    registry = ExecutorRegistry()
    registry.register(counting_executor)
    orchestrator = ExecutionOrchestrator(registry=registry)

    async def in_mem_worker() -> ExecutionResult:
        return await orchestrator.execute(pol, act, case, pay, ExecutionMode.SIMULATION)

    res1, res2 = await asyncio.gather(in_mem_worker(), in_mem_worker())

    # In-memory lock across whole execution guarantees exactly 1 invocation
    assert counting_executor.invocation_count == 1
    assert res1.execution_id == res2.execution_id
    assert res1.status == ExecutionStatus.SUCCEEDED
    assert res2.status == ExecutionStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_database_idempotency_and_concurrency() -> None:
    """Verify durable uniqueness and duplicate protection via PostgreSQL."""
    url = get_pg_url()
    reachable = await check_pg(url)
    if not reachable:
        pytest.skip(f"PostgreSQL not reachable at {url}")

    engine = create_async_engine(url, echo=False)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    pol, act, case, pay, cust = _make_fixture()

    # Pre-seed customer, payment, case, action in database
    uow_seed = UnitOfWork(session_maker)
    async with uow_seed:
        await uow_seed.customers.save(cust)
        await uow_seed.payments.save(pay)
        await uow_seed.recovery_cases.save(case)
        await uow_seed.recovery_actions.save(act)
        await uow_seed.commit()

    orchestrator = ExecutionOrchestrator()

    # Sequential duplicate test with database persistence
    uow1 = UnitOfWork(session_maker)
    async with uow1:
        res1 = await orchestrator.execute(
            pol,
            act,
            case,
            pay,
            ExecutionMode.SIMULATION,
            unit_of_work=uow1,
        )

    uow2 = UnitOfWork(session_maker)
    async with uow2:
        res2 = await orchestrator.execute(
            pol,
            act,
            case,
            pay,
            ExecutionMode.SIMULATION,
            unit_of_work=uow2,
        )

    assert res1.execution_id == res2.execution_id
    assert res2.metadata.get("reused_existing_execution") is True

    await engine.dispose()


@pytest.mark.asyncio
async def test_database_concurrent_duplicate_claims_at_most_one_dispatch() -> None:
    """Verify concurrent workers on same key invoke executor at most once."""
    url = get_pg_url()
    reachable = await check_pg(url)
    if not reachable:
        pytest.skip(f"PostgreSQL not reachable at {url}")

    engine = create_async_engine(url, echo=False)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    pol, act, case, pay, cust = _make_fixture()

    # Pre-seed entities
    uow_seed = UnitOfWork(session_maker)
    async with uow_seed:
        await uow_seed.customers.save(cust)
        await uow_seed.payments.save(pay)
        await uow_seed.recovery_cases.save(case)
        await uow_seed.recovery_actions.save(act)
        await uow_seed.commit()

    counting_executor = CountingRetryExecutor()
    registry = ExecutorRegistry()
    registry.register(counting_executor)
    orchestrator = ExecutionOrchestrator(registry=registry)

    async def worker_task() -> ExecutionResult:
        uow = UnitOfWork(session_maker)
        async with uow:
            return await orchestrator.execute(
                pol,
                act,
                case,
                pay,
                ExecutionMode.SIMULATION,
                unit_of_work=uow,
            )

    # Launch two concurrent worker requests against PostgreSQL
    res1, res2 = await asyncio.gather(worker_task(), worker_task())

    # 1. Assert executor was invoked at most once
    assert counting_executor.invocation_count <= 1

    # 2. Assert both workers resolved to the same execution
    assert res1.execution_id == res2.execution_id

    # 3. Assert exactly one execution record exists in database
    async with engine.connect() as conn:
        stmt = select(ExecutionModel).where(
            ExecutionModel.idempotency_key == pol.idempotency_key
        )
        db_rows = (await conn.execute(stmt)).fetchall()
        assert len(db_rows) == 1

    await engine.dispose()
