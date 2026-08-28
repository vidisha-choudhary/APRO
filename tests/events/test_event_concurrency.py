"""PostgreSQL Concurrency Tests for Phase 3 Canonical Event Pipeline."""

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

from apro.domain.enums import PaymentStatus
from apro.domain.models import Customer, Payment
from apro.events.pipeline import EventPipeline
from apro.persistence.repositories import (
    CustomerRepository,
    PaymentEventRepository,
    PaymentRepository,
    RawEventRepository,
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
async def test_postgres_concurrent_duplicate_webhook_delivery(
    raw_failed_payload: dict[str, Any],
) -> None:
    """Test concurrent duplicate delivery of same provider event against PostgreSQL."""
    pg_url = get_postgres_url()
    engine = create_async_engine(pg_url, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    provider_pay_id = f"pay_race_{uuid.uuid4().hex[:8]}"
    race_evt_id = f"evt_race_{uuid.uuid4().hex[:8]}"

    try:
        # Pre-seed Customer & Payment in PostgreSQL
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

        payload = json.loads(json.dumps(raw_failed_payload))
        payload["payload"]["payment"]["entity"]["id"] = provider_pay_id

        body = json.dumps(payload).encode("utf-8")
        sig = sign_payload(body, WEBHOOK_SECRET)

        start_event = asyncio.Event()

        async def worker(_worker_id: str):  # type: ignore[no-untyped-def]
            pipeline = EventPipeline(factory)
            await start_event.wait()
            return await pipeline.process_webhook(
                raw_body=body,
                signature=sig,
                event_id=race_evt_id,
                webhook_secret=WEBHOOK_SECRET,
            )

        task1 = asyncio.create_task(worker("w1"))
        task2 = asyncio.create_task(worker("w2"))

        await asyncio.sleep(0.05)
        start_event.set()

        results = await asyncio.wait_for(
            asyncio.gather(task1, task2, return_exceptions=True), timeout=5.0
        )

        classifications = [
            r.classification for r in results if not isinstance(r, Exception)
        ]

        assert len(classifications) == 2
        assert "NEW" in classifications
        assert "DUPLICATE" in classifications

        # Verify persisted state in PostgreSQL
        async with factory() as session:
            p_repo = PaymentRepository(session)
            pevt_repo = PaymentEventRepository(session)
            raw_repo = RawEventRepository(session)

            pay = await p_repo.get_by_id(p_id)
            assert pay is not None
            assert pay.status == PaymentStatus.FAILED

            events = await pevt_repo.find_by_payment_id(p_id)
            assert len(events) == 1  # Exactly 1 canonical PaymentEvent

            raw_evt = await raw_repo.find_by_provider_event_id("razorpay", race_evt_id)
            assert raw_evt is not None  # Exactly 1 raw event
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_concurrent_different_events_race(
    raw_failed_payload: dict[str, Any],
) -> None:
    """Test concurrent delivery of TWO DIFFERENT valid events for the SAME payment.

    Guarantees:
    - Uses two independent AsyncSession instances / PostgreSQL connections
    - Real overlapping execution with asyncio.Event barrier
    - Row locking (SELECT ... FOR UPDATE) serializes workers
    - Deterministic final state: Payment.status = CAPTURED
    - Both historical events stored in payment_events
    """
    pg_url = get_postgres_url()
    engine = create_async_engine(pg_url, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    provider_pay_id = f"pay_diff_race_{uuid.uuid4().hex[:8]}"

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

        # Worker 1 payload: payment.failed (created_at = 1000)
        payload1 = json.loads(json.dumps(raw_failed_payload))
        payload1["event"] = "payment.failed"
        payload1["created_at"] = 1000
        payload1["payload"]["payment"]["entity"]["id"] = provider_pay_id
        body1 = json.dumps(payload1).encode("utf-8")
        sig1 = sign_payload(body1, WEBHOOK_SECRET)
        evt1_id = f"evt_fail_{uuid.uuid4().hex[:8]}"

        # Worker 2 payload: payment.captured (created_at = 2000)
        payload2 = json.loads(json.dumps(raw_failed_payload))
        payload2["event"] = "payment.captured"
        payload2["created_at"] = 2000
        payload2["payload"]["payment"]["entity"]["id"] = provider_pay_id
        payload2["payload"]["payment"]["entity"]["status"] = "captured"
        body2 = json.dumps(payload2).encode("utf-8")
        sig2 = sign_payload(body2, WEBHOOK_SECRET)
        evt2_id = f"evt_cap_{uuid.uuid4().hex[:8]}"

        start_event = asyncio.Event()

        async def worker_failed() -> Any:
            pipeline = EventPipeline(factory)
            await start_event.wait()
            return await pipeline.process_webhook(
                raw_body=body1,
                signature=sig1,
                event_id=evt1_id,
                webhook_secret=WEBHOOK_SECRET,
            )

        async def worker_captured() -> Any:
            pipeline = EventPipeline(factory)
            await start_event.wait()
            return await pipeline.process_webhook(
                raw_body=body2,
                signature=sig2,
                event_id=evt2_id,
                webhook_secret=WEBHOOK_SECRET,
            )

        task1 = asyncio.create_task(worker_failed())
        task2 = asyncio.create_task(worker_captured())

        await asyncio.sleep(0.05)
        start_event.set()

        results = await asyncio.wait_for(
            asyncio.gather(task1, task2, return_exceptions=True), timeout=5.0
        )

        for r in results:
            assert not isinstance(r, Exception), f"Worker failed with exception: {r}"

        # Verify DB state in PostgreSQL
        async with factory() as session:
            p_repo = PaymentRepository(session)
            pevt_repo = PaymentEventRepository(session)

            pay = await p_repo.get_by_id(p_id)
            assert pay is not None
            # Must resolve to CAPTURED without lost updates or state regression
            assert pay.status == PaymentStatus.CAPTURED

            events = await pevt_repo.find_by_payment_id(p_id)
            assert len(events) == 2  # Both events preserved in history
            types = {e.event_type for e in events}
            assert "payment.failed" in types
            assert "payment.captured" in types
    finally:
        await engine.dispose()
