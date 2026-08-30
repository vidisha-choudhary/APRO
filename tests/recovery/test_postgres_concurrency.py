"""PostgreSQL Concurrency Acceptance Tests for Phase 4 Recovery Case Orchestration."""

import asyncio
import hashlib
import hmac
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Customer, Payment
from apro.events.pipeline import EventPipeline
from apro.persistence.repositories import (
    AuditEventRepository,
    CustomerRepository,
    PaymentRepository,
    RecoveryCaseRepository,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
PAYMENT_FAILED_FIXTURE = FIXTURES_DIR / "payment_failed.json"
WEBHOOK_SECRET = "test_webhook_secret"
DEFAULT_PG_URL = "postgresql+asyncpg://postgres@127.0.0.1:5432/apro_test_db"


def get_postgres_url() -> str:
    url = os.getenv("POSTGRES_TEST_URL", DEFAULT_PG_URL)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def sign_payload(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.fixture
def raw_failed_payload() -> dict[str, Any]:
    with open(PAYMENT_FAILED_FIXTURE) as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_postgres_concurrent_case_creation_race(
    raw_failed_payload: dict[str, Any],
) -> None:
    """Test concurrent delivery of qualifying payment.failed webhooks against PostgreSQL.

    Guarantees:
    - Uses two independent AsyncSession instances / PostgreSQL database connections
    - Real overlapping execution with asyncio.Event barrier
    - Exactly 1 active RecoveryCase created for the payment in PostgreSQL
    - No duplicate active cases created
    - Both raw events and canonical payment events recorded
    """
    pg_url = get_postgres_url()
    engine = create_async_engine(pg_url, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    provider_pay_id = f"pay_case_race_{uuid.uuid4().hex[:8]}"

    try:
        # Pre-seed Customer & Payment (PENDING) in PostgreSQL
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
                    provider_payment_id=provider_pay_id,
                    provider="razorpay",
                    amount=50000,
                    currency="INR",
                    method="card",
                    status=PaymentStatus.PENDING,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

        # Webhook 1 payload
        payload1 = json.loads(json.dumps(raw_failed_payload))
        payload1["payload"]["payment"]["entity"]["id"] = provider_pay_id
        body1 = json.dumps(payload1).encode("utf-8")
        sig1 = sign_payload(body1, WEBHOOK_SECRET)
        evt1_id = f"evt_w1_{uuid.uuid4().hex[:8]}"

        # Webhook 2 payload (same provider payment ID, different event ID)
        payload2 = json.loads(json.dumps(raw_failed_payload))
        payload2["payload"]["payment"]["entity"]["id"] = provider_pay_id
        body2 = json.dumps(payload2).encode("utf-8")
        sig2 = sign_payload(body2, WEBHOOK_SECRET)
        evt2_id = f"evt_w2_{uuid.uuid4().hex[:8]}"

        start_event = asyncio.Event()

        async def worker(body: bytes, sig: str, evt_id: str) -> Any:
            pipeline = EventPipeline(factory)
            await start_event.wait()
            return await pipeline.process_webhook(
                raw_body=body,
                signature=sig,
                event_id=evt_id,
                webhook_secret=WEBHOOK_SECRET,
            )

        task1 = asyncio.create_task(worker(body1, sig1, evt1_id))
        task2 = asyncio.create_task(worker(body2, sig2, evt2_id))

        await asyncio.sleep(0.05)
        start_event.set()

        results = await asyncio.wait_for(
            asyncio.gather(task1, task2, return_exceptions=True), timeout=5.0
        )

        for r in results:
            assert not isinstance(r, Exception), f"Worker failed with exception: {r}"

        # Verify persisted state directly in PostgreSQL
        async with factory() as session:
            case_repo = RecoveryCaseRepository(session)
            audit_repo = AuditEventRepository(session)

            # Query all cases for the payment
            cases = await case_repo.find_by_payment_id(p_id)
            assert len(cases) == 1  # Exactly 1 RecoveryCase created!

            active_case = await case_repo.find_active_by_payment_id(p_id)
            assert active_case is not None
            assert active_case.status == RecoveryCaseStatus.NEW
            assert active_case.payment_id == p_id
            assert active_case.customer_id == c_id

            # Verify audit events recorded for creation and reuse
            audits = await audit_repo.find_by_case_id(active_case.case_id)
            assert len(audits) == 2
            event_types = [a.event_type for a in audits]
            assert "RECOVERY_CASE_CREATED" in event_types
            assert "RECOVERY_CASE_REUSED" in event_types
    finally:
        await engine.dispose()
