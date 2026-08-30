"""HTTP Route Integration Tests for /webhooks/razorpay with EventPipeline."""

import hashlib
import hmac
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apro.config import settings
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Customer, Payment
from apro.main import app
from apro.persistence.base import Base
from apro.persistence.repositories import (
    AuditEventRepository,
    CustomerRepository,
    PaymentEventRepository,
    PaymentRepository,
    RawEventRepository,
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


@pytest.mark.asyncio
async def test_http_route_event_pipeline_postgres_integration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Correction B: Test POST /webhooks/razorpay exercises EventPipeline over HTTP.

    Proves:
    1. HTTP request -> EventPipeline -> PostgreSQL
    2. Raw event persisted
    3. Canonical PaymentEvent persisted
    4. APRO Payment state updated
    5. Duplicate HTTP request returns status='duplicate', classification='DUPLICATE'
    6. No duplicate canonical event created
    """
    pg_url = get_postgres_url()
    monkeypatch.setattr(settings, "DATABASE_URL", pg_url)
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    provider_pay_id = f"pay_http_{uuid.uuid4().hex[:8]}"
    evt_id = f"evt_http_{uuid.uuid4().hex[:8]}"

    # Seed customer and payment in PostgreSQL using dedicated engine
    engine1 = create_async_engine(pg_url, echo=False)
    async with engine1.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory1 = async_sessionmaker(
        bind=engine1, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with factory1() as session:
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
    await engine1.dispose()

    # Enter TestClient context (app lifespan creates app.state.session_factory)
    with TestClient(app) as client:
        with open(PAYMENT_FAILED_FIXTURE) as f:
            payload: dict[str, Any] = json.load(f)

        payload["payload"]["payment"]["entity"]["id"] = provider_pay_id

        body = json.dumps(payload).encode("utf-8")
        sig = sign_payload(body, WEBHOOK_SECRET)

        headers = {
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": evt_id,
        }

        # 1. First HTTP POST
        res1 = client.post("/webhooks/razorpay", content=body, headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "accepted"
        assert data1["classification"] == "NEW"
        assert data1["event_id"] == evt_id
        assert data1["payment_id"] == p_id

        # 2. Second HTTP POST (Duplicate Delivery)
        res2 = client.post("/webhooks/razorpay", content=body, headers=headers)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "duplicate"
        assert data2["classification"] == "DUPLICATE"
        assert data2["event_id"] == evt_id

    # Verify DB persistence using a fresh engine session
    engine2 = create_async_engine(pg_url, echo=False)
    factory2 = async_sessionmaker(
        bind=engine2, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with factory2() as session:
        p_repo = PaymentRepository(session)
        pevt_repo = PaymentEventRepository(session)
        raw_repo = RawEventRepository(session)
        case_repo = RecoveryCaseRepository(session)
        audit_repo = AuditEventRepository(session)

        pay = await p_repo.get_by_id(p_id)
        assert pay is not None
        assert pay.status == PaymentStatus.FAILED

        events = await pevt_repo.find_by_payment_id(p_id)
        assert len(events) == 1
        assert events[0].event_type == "payment.failed"

        raw_evt = await raw_repo.find_by_provider_event_id("razorpay", evt_id)
        assert raw_evt is not None

        # Phase 4 end-to-end HTTP verification: RecoveryCase + AuditEvent
        case = await case_repo.find_active_by_payment_id(p_id)
        assert case is not None
        assert case.status == RecoveryCaseStatus.NEW

        audits = await audit_repo.find_by_case_id(case.case_id)
        assert len(audits) >= 1
        assert audits[0].event_type == "RECOVERY_CASE_CREATED"
    await engine2.dispose()
