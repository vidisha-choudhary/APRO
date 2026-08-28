"""PostgreSQL Acceptance Test Suite for APRO Phase 2.

This test suite strictly requires a running PostgreSQL database instance.
It does NOT silently fall back to SQLite.
"""

import asyncio
import os
import uuid
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
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
from apro.domain.exceptions import InvalidStateTransitionError
from apro.domain.models import (
    ActionEvaluation,
    AuditEvent,
    Customer,
    Decision,
    Diagnosis,
    Execution,
    Outcome,
    Payment,
    PaymentEvent,
    PolicyDecision,
    RecoveryAction,
    RecoveryCase,
)
from apro.persistence.repositories import (
    ActionEvaluationRepository,
    AuditEventRepository,
    CustomerRepository,
    DecisionRepository,
    DiagnosisRepository,
    ExecutionRepository,
    OutcomeRepository,
    PaymentEventRepository,
    PaymentRepository,
    PolicyDecisionRepository,
    RawEventRepository,
    RecoveryActionRepository,
    RecoveryCaseRepository,
)
from apro.persistence.unit_of_work import UnitOfWork

DEFAULT_PG_URL = "postgresql+asyncpg://postgres@127.0.0.1:5432/apro_test_db"


def get_postgres_url() -> str:
    url = os.getenv("POSTGRES_TEST_URL", DEFAULT_PG_URL)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def check_postgres_connection(url: str) -> bool:
    try:
        engine = create_async_engine(url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def postgres_url() -> str:
    url = get_postgres_url()
    reachable = asyncio.run(check_postgres_connection(url))
    if not reachable:
        pytest.skip(
            f"PostgreSQL database is not reachable at {url}. "
            "A running PostgreSQL instance is strictly required."
        )
    return url


async def _create_isolated_db(base_pg_url: str, db_name: str) -> None:
    admin_engine = create_async_engine(base_pg_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            await conn.execute(text(f"CREATE DATABASE {db_name}"))
    finally:
        await admin_engine.dispose()


async def _drop_isolated_db(base_pg_url: str, db_name: str) -> None:
    admin_engine = create_async_engine(base_pg_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            term_sql = (
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
            )
            await conn.execute(text(term_sql))
            await conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
    finally:
        await admin_engine.dispose()


# 1. Fresh PostgreSQL Migration
def test_postgres_alembic_fresh_database_migration(postgres_url: str) -> None:
    """Fresh isolated PostgreSQL database migration test."""
    parts = postgres_url.split("/")
    base_pg_url = "/".join(parts[:-1]) + "/postgres"

    db_name = f"test_mig_{uuid.uuid4().hex[:8]}"

    # 1. Create fresh isolated empty database
    asyncio.run(_create_isolated_db(base_pg_url, db_name))

    isolated_pg_url = "/".join(parts[:-1]) + f"/{db_name}"

    try:
        # 2. Run Alembic upgrade head against the fresh empty database
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", isolated_pg_url)
        command.upgrade(alembic_cfg, "head")

        # 3. Inspect schema & verify alembic_version and 13 Phase 2 tables
        sync_url = isolated_pg_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg://"
        )
        engine = create_engine(sync_url, echo=False)
        try:
            with engine.connect() as conn:
                inspector = inspect(conn)
                tables = set(inspector.get_table_names())
                expected_tables = {
                    "alembic_version",
                    "customers",
                    "payments",
                    "raw_events",
                    "payment_events",
                    "recovery_cases",
                    "recovery_actions",
                    "diagnoses",
                    "action_evaluations",
                    "decisions",
                    "policy_decisions",
                    "executions",
                    "outcomes",
                    "audit_events",
                }
                assert expected_tables.issubset(tables)

                # Verify PostgreSQL data types & constraints
                raw_cols = {c["name"]: c for c in inspector.get_columns("raw_events")}
                assert "JSONB" in str(raw_cols["raw_payload"]["type"]).upper()

                cust_cols = {c["name"]: c for c in inspector.get_columns("customers")}
                assert "UUID" in str(cust_cols["customer_id"]["type"]).upper()

                pay_cols = {c["name"]: c for c in inspector.get_columns("payments")}
                assert (
                    "BIGINT" in str(pay_cols["amount"]["type"]).upper()
                    or "INTEGER" in str(pay_cols["amount"]["type"]).upper()
                )
                assert pay_cols["created_at"]["type"].timezone is True

                raw_uqs = [
                    u["name"] for u in inspector.get_unique_constraints("raw_events")
                ]
                assert "uq_raw_events_provider_event_id" in raw_uqs

                fks = [
                    fk["referred_table"]
                    for fk in inspector.get_foreign_keys("payments")
                ]
                assert "customers" in fks
        finally:
            engine.dispose()

    finally:
        # 4. Clean up isolated temporary database
        asyncio.run(_drop_isolated_db(base_pg_url, db_name))


# 2. PostgreSQL Schema, Types & Constraints Verification
def test_postgres_schema_types_and_constraints(postgres_url: str) -> None:
    """Inspect actual PostgreSQL schema data types and constraints."""
    sync_url = postgres_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    engine = create_engine(sync_url, echo=False)
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)

            # 1. Verify JSONB raw_payload in raw_events
            raw_cols = {c["name"]: c for c in inspector.get_columns("raw_events")}
            assert "raw_payload" in raw_cols
            assert "JSONB" in str(raw_cols["raw_payload"]["type"]).upper()

            # 2. Verify UUID primary key in customers
            cust_cols = {c["name"]: c for c in inspector.get_columns("customers")}
            assert "customer_id" in cust_cols
            assert "UUID" in str(cust_cols["customer_id"]["type"]).upper()

            # 3. Verify BIGINT amount in payments
            pay_cols = {c["name"]: c for c in inspector.get_columns("payments")}
            assert "amount" in pay_cols
            assert (
                "BIGINT" in str(pay_cols["amount"]["type"]).upper()
                or "INTEGER" in str(pay_cols["amount"]["type"]).upper()
            )
            assert pay_cols["created_at"]["type"].timezone is True

            # 4. Verify unique constraints on raw_events and executions
            raw_uqs = [
                u["name"] for u in inspector.get_unique_constraints("raw_events")
            ]
            assert "uq_raw_events_provider_event_id" in raw_uqs

            exec_uqs = [
                u["name"] for u in inspector.get_unique_constraints("executions")
            ]
            assert "uq_executions_idempotency_key" in exec_uqs

            # 5. Verify foreign key on payments
            fks = [
                fk["referred_table"] for fk in inspector.get_foreign_keys("payments")
            ]
            assert "customers" in fks
    finally:
        engine.dispose()


# 3. PostgreSQL Repository Round Trips
@pytest.mark.asyncio
async def test_postgres_repositories_roundtrip(postgres_url: str) -> None:
    """Test all 13 domain repositories against PostgreSQL."""
    engine = create_async_engine(postgres_url, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    try:
        async with factory() as session:
            c_repo = CustomerRepository(session)
            p_repo = PaymentRepository(session)
            raw_repo = RawEventRepository(session)
            pevt_repo = PaymentEventRepository(session)
            case_repo = RecoveryCaseRepository(session)
            act_repo = RecoveryActionRepository(session)
            diag_repo = DiagnosisRepository(session)
            eval_repo = ActionEvaluationRepository(session)
            dec_repo = DecisionRepository(session)
            pdec_repo = PolicyDecisionRepository(session)
            exec_repo = ExecutionRepository(session)
            out_repo = OutcomeRepository(session)
            aud_repo = AuditEventRepository(session)

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
            raw_id = str(uuid.uuid4())
            pevt_id = str(uuid.uuid4())

            provider_evt_id = f"evt_pg_{uuid.uuid4().hex[:8]}"
            idem_key = f"idempotency_key_pg_{uuid.uuid4().hex[:8]}"

            # Customer & Payment
            await c_repo.save(
                Customer(customer_id=c_id, created_at=now, updated_at=now)
            )
            await p_repo.save(
                Payment(
                    payment_id=p_id,
                    customer_id=c_id,
                    provider="razorpay",
                    amount=7500,
                    currency="INR",
                    method="card",
                    status=PaymentStatus.FAILED,
                    created_at=now,
                    updated_at=now,
                )
            )
            # Raw event
            await raw_repo.save(
                raw_event_id=raw_id,
                provider="razorpay",
                provider_event_id=provider_evt_id,
                event_type="payment.failed",
                received_at=now,
                raw_payload={"id": provider_evt_id, "status": "failed"},
            )
            # Payment event
            await pevt_repo.append(
                PaymentEvent(
                    event_id=pevt_id,
                    provider="razorpay",
                    event_type="payment.failed",
                    payment_id=p_id,
                    amount=7500,
                    currency="INR",
                    method="card",
                    status=PaymentStatus.FAILED,
                    event_timestamp=now,
                    received_at=now,
                )
            )
            # Case & Action
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
            # Diagnosis, Evaluation, Decision, Policy Decision
            await diag_repo.append(
                Diagnosis(
                    diagnosis_id=diag_id,
                    case_id=case_id,
                    category=FailureCategory.TRANSIENT,
                    confidence=0.95,
                    evidence=("timeout",),
                    model_name="diag_v1",
                    model_version="1.0",
                    created_at=now,
                )
            )
            await eval_repo.append(
                ActionEvaluation(
                    evaluation_id=eval_id,
                    case_id=case_id,
                    action_type=RecoveryActionType.RETRY,
                    success_probability=0.85,
                    recoverable_amount=7500,
                    action_cost=150,
                    expected_recovery_value=6225,
                    model_name="eval_v1",
                    model_version="1.0",
                    created_at=now,
                )
            )
            await dec_repo.append(
                Decision(
                    decision_id=dec_id,
                    case_id=case_id,
                    recommended_action=RecoveryActionType.RETRY,
                    confidence=0.85,
                    expected_recovery_value=6225,
                    reason="High expected value",
                    model_name="dec_v1",
                    model_version="1.0",
                    created_at=now,
                )
            )
            await pdec_repo.append(
                PolicyDecision(
                    policy_decision_id=pdec_id,
                    decision_id=dec_id,
                    case_id=case_id,
                    result=PolicyDecisionResult.ALLOW,
                    reason="Policy compliance ok",
                    policy_version="1.0",
                    created_at=now,
                )
            )
            # Execution, Outcome, Audit
            await exec_repo.save(
                Execution(
                    execution_id=exec_id,
                    action_id=act_id,
                    case_id=case_id,
                    execution_type="standard_retry",
                    execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
                    status=ExecutionStatus.PENDING,
                    started_at=now,
                ),
                idempotency_key=idem_key,
            )
            await out_repo.append(
                Outcome(
                    outcome_id=out_id,
                    case_id=case_id,
                    execution_id=exec_id,
                    type=OutcomeType.RECOVERED,
                    amount_recovered=7500,
                    observed_at=now,
                )
            )
            await aud_repo.append(
                AuditEvent(
                    audit_event_id=aud_id,
                    case_id=case_id,
                    event_type="CASE_CREATED",
                    actor=AuditActor.SYSTEM,
                    timestamp=now,
                    payload={"action": "created"},
                )
            )
            await session.commit()

        # Verification read back
        async with factory() as session:
            c_repo = CustomerRepository(session)
            assert await c_repo.get_by_id(c_id) is not None

            raw_repo = RawEventRepository(session)
            raw_found = await raw_repo.find_by_provider_event_id(
                "razorpay", provider_evt_id
            )
            assert raw_found is not None
            assert raw_found.raw_payload["status"] == "failed"

            exec_repo = ExecutionRepository(session)
            exec_found = await exec_repo.find_by_idempotency_key(idem_key)
            assert exec_found is not None
    finally:
        await engine.dispose()


# 4. PostgreSQL Unit of Work Transaction Commit & Rollback
@pytest.mark.asyncio
async def test_postgres_unit_of_work_transaction(postgres_url: str) -> None:
    """Test Unit of Work atomic commit and rollback against PostgreSQL."""
    engine = create_async_engine(postgres_url, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    c_rollback_id = str(uuid.uuid4())

    try:
        # 1. Commit
        async with UnitOfWork(factory) as uow:
            await uow.customers.save(
                Customer(customer_id=c_id, created_at=now, updated_at=now)
            )
            await uow.payments.save(
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

        # Verify commit
        async with UnitOfWork(factory) as uow:
            assert await uow.payments.get_by_id(p_id) is not None

        # 2. Rollback
        try:
            async with UnitOfWork(factory) as uow:
                await uow.customers.save(
                    Customer(customer_id=c_rollback_id, created_at=now, updated_at=now)
                )
                raise RuntimeError("Artificial transaction failure")
        except RuntimeError:
            pass

        # Verify rollback
        async with UnitOfWork(factory) as uow:
            assert await uow.customers.get_by_id(c_rollback_id) is None
    finally:
        await engine.dispose()


# 5. PostgreSQL Provider-Event Uniqueness Test (with explicit session rollback)
@pytest.mark.asyncio
async def test_postgres_provider_event_uniqueness(postgres_url: str) -> None:
    """Test PostgreSQL database-enforced provider event uniqueness constraint."""
    engine = create_async_engine(postgres_url, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    raw_id1 = str(uuid.uuid4())
    raw_id2 = str(uuid.uuid4())
    dup_evt_id = f"evt_pg_uniq_{uuid.uuid4().hex[:8]}"

    try:
        async with factory() as session:
            raw_repo = RawEventRepository(session)
            await raw_repo.save(
                raw_event_id=raw_id1,
                provider="razorpay",
                provider_event_id=dup_evt_id,
                event_type="payment.failed",
                received_at=now,
                raw_payload={"id": dup_evt_id},
            )
            await session.commit()

        with pytest.raises(IntegrityError):
            async with factory() as session:
                try:
                    raw_repo = RawEventRepository(session)
                    await raw_repo.save(
                        raw_event_id=raw_id2,
                        provider="razorpay",
                        provider_event_id=dup_evt_id,
                        event_type="payment.failed",
                        received_at=now,
                        raw_payload={"id": dup_evt_id},
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        # Verify exactly 1 event exists
        async with factory() as session:
            raw_repo = RawEventRepository(session)
            evt = await raw_repo.find_by_provider_event_id("razorpay", dup_evt_id)
            assert evt is not None
            assert evt.raw_event_id == raw_id1
    finally:
        await engine.dispose()


# 6. PostgreSQL Execution Idempotency Uniqueness Test (with explicit session rollback)
@pytest.mark.asyncio
async def test_postgres_execution_idempotency_uniqueness(postgres_url: str) -> None:
    """Test PostgreSQL execution idempotency_key uniqueness constraint."""
    engine = create_async_engine(postgres_url, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    act_id = str(uuid.uuid4())
    exec_id1 = str(uuid.uuid4())
    exec_id2 = str(uuid.uuid4())
    dup_idem_key = f"idem_key_pg_uniq_{uuid.uuid4().hex[:8]}"

    try:
        async with factory() as session:
            c_repo = CustomerRepository(session)
            p_repo = PaymentRepository(session)
            case_repo = RecoveryCaseRepository(session)
            act_repo = RecoveryActionRepository(session)
            await c_repo.save(
                Customer(customer_id=c_id, created_at=now, updated_at=now)
            )
            await p_repo.save(
                Payment(
                    payment_id=p_id,
                    customer_id=c_id,
                    provider="razorpay",
                    amount=5000,
                    currency="INR",
                    method="card",
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

        # Insert 1st execution
        async with factory() as session:
            exec_repo = ExecutionRepository(session)
            ex1 = Execution(
                execution_id=exec_id1,
                action_id=act_id,
                case_id=case_id,
                execution_type="standard_retry",
                execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
                status=ExecutionStatus.PENDING,
                started_at=now,
            )
            await exec_repo.save(ex1, idempotency_key=dup_idem_key)
            await session.commit()

        # Attempt inserting 2nd execution with same idempotency_key
        with pytest.raises(IntegrityError):
            async with factory() as session:
                try:
                    exec_repo = ExecutionRepository(session)
                    ex2 = Execution(
                        execution_id=exec_id2,
                        action_id=act_id,
                        case_id=case_id,
                        execution_type="standard_retry",
                        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
                        status=ExecutionStatus.PENDING,
                        started_at=now,
                    )
                    await exec_repo.save(ex2, idempotency_key=dup_idem_key)
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        # Verify exactly 1 execution exists for dup_idem_key
        async with factory() as session:
            exec_repo = ExecutionRepository(session)
            ex_found = await exec_repo.find_by_idempotency_key(dup_idem_key)
            assert ex_found is not None
            assert ex_found.execution_id == exec_id1
    finally:
        await engine.dispose()


# 7. PostgreSQL Provider-Event Concurrency Race Test
@pytest.mark.asyncio
async def test_postgres_provider_event_concurrency_race(postgres_url: str) -> None:
    """Test concurrent duplicate provider event insertion race on PostgreSQL."""
    engine = create_async_engine(postgres_url, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    race_evt_id = f"evt_pg_race_{uuid.uuid4().hex[:8]}"
    start_event = asyncio.Event()

    async def worker(_worker_id: str):  # type: ignore[no-untyped-def]
        async with factory() as session:
            try:
                repo = RawEventRepository(session)
                raw_id = str(uuid.uuid4())
                await start_event.wait()
                await repo.save(
                    raw_event_id=raw_id,
                    provider="razorpay",
                    provider_event_id=race_evt_id,
                    event_type="payment.failed",
                    received_at=now,
                    raw_payload={"id": race_evt_id},
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    try:
        task1 = asyncio.create_task(worker("w1"))
        task2 = asyncio.create_task(worker("w2"))

        await asyncio.sleep(0.05)
        start_event.set()

        results = await asyncio.wait_for(
            asyncio.gather(task1, task2, return_exceptions=True), timeout=5.0
        )

        successes = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]

        assert len(successes) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], IntegrityError)

        # Verify exactly 1 event persisted in PostgreSQL
        async with factory() as session:
            repo = RawEventRepository(session)
            evt = await repo.find_by_provider_event_id("razorpay", race_evt_id)
            assert evt is not None
    finally:
        await engine.dispose()


# 8. PostgreSQL Execution-Idempotency Concurrency Race Test
@pytest.mark.asyncio
async def test_postgres_execution_idempotency_concurrency_race(
    postgres_url: str,
) -> None:
    """Test concurrent execution creation race with identical idempotency_key."""
    engine = create_async_engine(postgres_url, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    act_id = str(uuid.uuid4())
    race_idem_key = f"idem_key_pg_race_{uuid.uuid4().hex[:8]}"

    try:
        async with factory() as session:
            c_repo = CustomerRepository(session)
            p_repo = PaymentRepository(session)
            case_repo = RecoveryCaseRepository(session)
            act_repo = RecoveryActionRepository(session)
            await c_repo.save(
                Customer(customer_id=c_id, created_at=now, updated_at=now)
            )
            await p_repo.save(
                Payment(
                    payment_id=p_id,
                    customer_id=c_id,
                    provider="razorpay",
                    amount=5000,
                    currency="INR",
                    method="card",
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

        start_event = asyncio.Event()

        async def exec_worker(exec_id: str):  # type: ignore[no-untyped-def]
            async with factory() as session:
                try:
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
                    await start_event.wait()
                    await exec_repo.save(ex, idempotency_key=race_idem_key)
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        exec_id1 = str(uuid.uuid4())
        exec_id2 = str(uuid.uuid4())

        task1 = asyncio.create_task(exec_worker(exec_id1))
        task2 = asyncio.create_task(exec_worker(exec_id2))

        await asyncio.sleep(0.05)
        start_event.set()

        results = await asyncio.wait_for(
            asyncio.gather(task1, task2, return_exceptions=True), timeout=5.0
        )

        successes = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]

        assert len(successes) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], IntegrityError)

        # Verify exactly 1 execution persisted in PostgreSQL for race_idem_key
        async with factory() as session:
            exec_repo = ExecutionRepository(session)
            ex_found = await exec_repo.find_by_idempotency_key(race_idem_key)
            assert ex_found is not None
    finally:
        await engine.dispose()


# 9. PostgreSQL Mutable-State Concurrency Race Test (with timeout and explicit rollback)
@pytest.mark.asyncio
async def test_postgres_genuine_concurrency_race(postgres_url: str) -> None:
    """Synchronized concurrent payment state-update race on PostgreSQL."""
    engine = create_async_engine(postgres_url, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())

    try:
        # 1. Setup initial payment in FAILED status
        async with factory() as session:
            c_repo = CustomerRepository(session)
            p_repo = PaymentRepository(session)
            await c_repo.save(
                Customer(customer_id=c_id, created_at=now, updated_at=now)
            )
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

        # Worker A attempts transition FAILED -> PENDING
        async def worker_a():  # type: ignore[no-untyped-def]
            async with factory() as s1:
                try:
                    p_repo1 = PaymentRepository(s1)
                    pay1 = await p_repo1.get_by_id(p_id)
                    assert pay1 is not None
                    pay1.status = PaymentStatus.PENDING
                    await start_event.wait()
                    await p_repo1.update_status_conditional(
                        pay1, expected_status=PaymentStatus.FAILED
                    )
                    await s1.commit()
                except Exception:
                    await s1.rollback()
                    raise

        # Worker B attempts transition FAILED -> CAPTURED
        async def worker_b():  # type: ignore[no-untyped-def]
            async with factory() as s2:
                try:
                    p_repo2 = PaymentRepository(s2)
                    pay2 = await p_repo2.get_by_id(p_id)
                    assert pay2 is not None
                    pay2.status = PaymentStatus.CAPTURED
                    await start_event.wait()
                    await p_repo2.update_status_conditional(
                        pay2, expected_status=PaymentStatus.FAILED
                    )
                    await s2.commit()
                except Exception:
                    await s2.rollback()
                    raise

        # Launch both workers concurrently
        task_a = asyncio.create_task(worker_a())
        task_b = asyncio.create_task(worker_b())

        # Allow both workers to open sessions and reach race point
        await asyncio.sleep(0.05)

        # Release start gate to trigger simultaneous execution
        start_event.set()

        results = await asyncio.wait_for(
            asyncio.gather(task_a, task_b, return_exceptions=True), timeout=5.0
        )

        successes = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]

        # Exactly 1 worker must succeed, 1 worker must fail with error
        assert len(successes) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], InvalidStateTransitionError)

        # Verify final persisted state in PostgreSQL is valid
        async with factory() as check_session:
            check_repo = PaymentRepository(check_session)
            final_pay = await check_repo.get_by_id(p_id)
            assert final_pay is not None
            assert final_pay.status in (PaymentStatus.PENDING, PaymentStatus.CAPTURED)
    finally:
        await engine.dispose()
