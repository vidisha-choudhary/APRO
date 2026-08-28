"""Tests for Out-of-Order Webhook Delivery Protection in EventPipeline."""

import hashlib
import hmac
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apro.config import settings
from apro.domain.enums import PaymentStatus
from apro.domain.models import Customer, Payment
from apro.events.pipeline import EventPipeline
from apro.persistence.base import Base
from apro.persistence.repositories import (
    CustomerRepository,
    PaymentEventRepository,
    PaymentRepository,
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


@pytest_asyncio.fixture
async def pg_session_factory():  # type: ignore[no-untyped-def]
    pg_url = get_postgres_url()
    engine = create_async_engine(pg_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_out_of_order_case_1_captured_t2_then_failed_t1(
    pg_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Correction D Case 1: captured at T2 arrives 1st, failed at T1 arrives 2nd.

    Arrival order:
    1. payment.captured (created_at = T2 = 2000)
    2. payment.failed   (created_at = T1 = 1000)

    Verification:
    - Final Payment.status = CAPTURED
    - Both historical PaymentEvents exist in payment_events
    - Second event returns classification = STALE
    """
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    provider_pay_id = f"pay_ooo1_{uuid.uuid4().hex[:8]}"

    async with pg_session_factory() as session:
        c_repo = CustomerRepository(session)
        p_repo = PaymentRepository(session)
        await c_repo.save(Customer(customer_id=c_id, created_at=now, updated_at=now))
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

    with open(PAYMENT_FAILED_FIXTURE) as f:
        base_payload: dict[str, Any] = json.load(f)

    # Webhook 1: payment.captured at T2 (2000)
    payload_cap = json.loads(json.dumps(base_payload))
    payload_cap["event"] = "payment.captured"
    payload_cap["created_at"] = 2000
    payload_cap["payload"]["payment"]["entity"]["id"] = provider_pay_id
    payload_cap["payload"]["payment"]["entity"]["status"] = "captured"

    body1 = json.dumps(payload_cap).encode("utf-8")
    sig1 = sign_payload(body1, WEBHOOK_SECRET)
    evt1_id = f"evt_cap_t2_{uuid.uuid4().hex[:8]}"

    pipeline = EventPipeline(pg_session_factory)
    r1 = await pipeline.process_webhook(
        raw_body=body1, signature=sig1, event_id=evt1_id, webhook_secret=WEBHOOK_SECRET
    )
    assert r1.status == "accepted"
    assert r1.classification == "NEW"

    # Webhook 2: payment.failed at T1 (1000 < 2000)
    payload_fail = json.loads(json.dumps(base_payload))
    payload_fail["event"] = "payment.failed"
    payload_fail["created_at"] = 1000
    payload_fail["payload"]["payment"]["entity"]["id"] = provider_pay_id

    body2 = json.dumps(payload_fail).encode("utf-8")
    sig2 = sign_payload(body2, WEBHOOK_SECRET)
    evt2_id = f"evt_fail_t1_{uuid.uuid4().hex[:8]}"

    r2 = await pipeline.process_webhook(
        raw_body=body2, signature=sig2, event_id=evt2_id, webhook_secret=WEBHOOK_SECRET
    )
    assert r2.status == "accepted"
    assert r2.classification == "STALE"

    # Final DB Verification
    async with pg_session_factory() as session:
        p_repo = PaymentRepository(session)
        pevt_repo = PaymentEventRepository(session)

        pay = await p_repo.get_by_id(p_id)
        assert pay is not None
        assert pay.status == PaymentStatus.CAPTURED  # Payment status was protected

        events = await pevt_repo.find_by_payment_id(p_id)
        assert len(events) == 2  # Both events preserved in history
        event_types = {e.event_type for e in events}
        assert "payment.captured" in event_types
        assert "payment.failed" in event_types


@pytest.mark.asyncio
async def test_out_of_order_case_2_failed_t1_then_captured_t2(
    pg_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Correction D Case 2: failed at T1 arrives 1st, captured at T2 arrives 2nd.

    Arrival order:
    1. payment.failed   (created_at = T1 = 1000)
    2. payment.captured (created_at = T2 = 2000)

    Verification:
    - Final Payment.status = CAPTURED
    - Both historical PaymentEvents exist in payment_events
    """
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    provider_pay_id = f"pay_ooo2_{uuid.uuid4().hex[:8]}"

    async with pg_session_factory() as session:
        c_repo = CustomerRepository(session)
        p_repo = PaymentRepository(session)
        await c_repo.save(Customer(customer_id=c_id, created_at=now, updated_at=now))
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

    with open(PAYMENT_FAILED_FIXTURE) as f:
        base_payload: dict[str, Any] = json.load(f)

    # Webhook 1: payment.failed at T1 (1000)
    payload_fail = json.loads(json.dumps(base_payload))
    payload_fail["event"] = "payment.failed"
    payload_fail["created_at"] = 1000
    payload_fail["payload"]["payment"]["entity"]["id"] = provider_pay_id

    body1 = json.dumps(payload_fail).encode("utf-8")
    sig1 = sign_payload(body1, WEBHOOK_SECRET)
    evt1_id = f"evt_fail_t1_{uuid.uuid4().hex[:8]}"

    pipeline = EventPipeline(pg_session_factory)
    r1 = await pipeline.process_webhook(
        raw_body=body1, signature=sig1, event_id=evt1_id, webhook_secret=WEBHOOK_SECRET
    )
    assert r1.status == "accepted"
    assert r1.classification == "NEW"

    # Webhook 2: payment.captured at T2 (2000 > 1000)
    payload_cap = json.loads(json.dumps(base_payload))
    payload_cap["event"] = "payment.captured"
    payload_cap["created_at"] = 2000
    payload_cap["payload"]["payment"]["entity"]["id"] = provider_pay_id
    payload_cap["payload"]["payment"]["entity"]["status"] = "captured"

    body2 = json.dumps(payload_cap).encode("utf-8")
    sig2 = sign_payload(body2, WEBHOOK_SECRET)
    evt2_id = f"evt_cap_t2_{uuid.uuid4().hex[:8]}"

    r2 = await pipeline.process_webhook(
        raw_body=body2, signature=sig2, event_id=evt2_id, webhook_secret=WEBHOOK_SECRET
    )
    assert r2.status == "accepted"
    assert r2.classification == "NEW"

    # Final DB Verification
    async with pg_session_factory() as session:
        p_repo = PaymentRepository(session)
        pevt_repo = PaymentEventRepository(session)

        pay = await p_repo.get_by_id(p_id)
        assert pay is not None
        assert pay.status == PaymentStatus.CAPTURED  # Transitioned to CAPTURED

        events = await pevt_repo.find_by_payment_id(p_id)
        assert len(events) == 2  # Both events preserved in history
