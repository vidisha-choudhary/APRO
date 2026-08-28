"""Integration tests for EventPipeline with SQLite & PostgreSQL persistence."""

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
from apro.events.exceptions import InvalidSignatureError, MalformedPayloadError
from apro.events.pipeline import EventPipeline
from apro.persistence.base import Base
from apro.persistence.repositories import (
    CustomerRepository,
    PaymentEventRepository,
    PaymentRepository,
    RawEventRepository,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
PAYMENT_FAILED_FIXTURE = FIXTURES_DIR / "payment_failed.json"
WEBHOOK_SECRET = "test_webhook_secret"


@pytest.fixture
def raw_failed_payload() -> dict[str, Any]:
    with open(PAYMENT_FAILED_FIXTURE) as f:
        return json.load(f)


def sign_payload(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest_asyncio.fixture
async def async_factory(tmp_path):  # type: ignore[no-untyped-def]
    db_file = tmp_path / "test_pipeline.db"
    db_url = os.getenv("POSTGRES_TEST_URL", f"sqlite+aiosqlite:///{db_file}")
    engine = create_async_engine(db_url, echo=False)

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
async def test_pipeline_new_payment_failed(
    async_factory: async_sessionmaker[AsyncSession],
    raw_failed_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test pipeline processing new payment.failed event."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    provider_pay_id = f"pay_failed_{uuid.uuid4().hex[:8]}"

    # Pre-seed Customer & Payment
    async with async_factory() as session:
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

    payload = json.loads(json.dumps(raw_failed_payload))
    payload["payload"]["payment"]["entity"]["id"] = provider_pay_id

    body = json.dumps(payload).encode("utf-8")
    sig = sign_payload(body, WEBHOOK_SECRET)
    event_id = f"evt_pipe_{uuid.uuid4().hex[:8]}"

    pipeline = EventPipeline(async_factory)
    result = await pipeline.process_webhook(
        raw_body=body,
        signature=sig,
        event_id=event_id,
        webhook_secret=WEBHOOK_SECRET,
    )

    assert result.status == "accepted"
    assert result.classification == "NEW"
    assert result.event_id == event_id
    assert result.payment_id == p_id
    assert result.event_type == "payment.failed"

    # Verify persisted Payment state and PaymentEvent
    async with async_factory() as session:
        p_repo = PaymentRepository(session)
        pevt_repo = PaymentEventRepository(session)
        raw_repo = RawEventRepository(session)

        pay = await p_repo.get_by_id(p_id)
        assert pay is not None
        assert pay.status == PaymentStatus.FAILED

        events = await pevt_repo.find_by_payment_id(p_id)
        assert len(events) == 1
        assert events[0].event_type == "payment.failed"

        raw_evt = await raw_repo.find_by_provider_event_id("razorpay", event_id)
        assert raw_evt is not None


@pytest.mark.asyncio
async def test_pipeline_new_payment_authorized(
    async_factory: async_sessionmaker[AsyncSession],
    raw_failed_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test pipeline processing new payment.authorized event."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    provider_pay_id = f"pay_auth_{uuid.uuid4().hex[:8]}"

    async with async_factory() as session:
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

    payload = json.loads(json.dumps(raw_failed_payload))
    payload["event"] = "payment.authorized"
    payload["payload"]["payment"]["entity"]["id"] = provider_pay_id
    payload["payload"]["payment"]["entity"]["status"] = "authorized"
    del payload["payload"]["payment"]["entity"]["error_code"]

    body = json.dumps(payload).encode("utf-8")
    sig = sign_payload(body, WEBHOOK_SECRET)
    event_id = f"evt_auth_{uuid.uuid4().hex[:8]}"

    pipeline = EventPipeline(async_factory)
    result = await pipeline.process_webhook(
        raw_body=body,
        signature=sig,
        event_id=event_id,
        webhook_secret=WEBHOOK_SECRET,
    )

    assert result.status == "accepted"
    assert result.classification == "NEW"
    assert result.payment_id == p_id

    async with async_factory() as session:
        p_repo = PaymentRepository(session)
        pay = await p_repo.get_by_id(p_id)
        assert pay is not None
        assert pay.status == PaymentStatus.AUTHORIZED


@pytest.mark.asyncio
async def test_pipeline_duplicate_event(
    async_factory: async_sessionmaker[AsyncSession],
    raw_failed_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test duplicate delivery of same provider event returns DUPLICATE."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    provider_pay_id = f"pay_dup_{uuid.uuid4().hex[:8]}"

    async with async_factory() as session:
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

    payload = json.loads(json.dumps(raw_failed_payload))
    payload["payload"]["payment"]["entity"]["id"] = provider_pay_id

    body = json.dumps(payload).encode("utf-8")
    sig = sign_payload(body, WEBHOOK_SECRET)
    event_id = f"evt_dup_{uuid.uuid4().hex[:8]}"

    pipeline = EventPipeline(async_factory)

    # First delivery
    r1 = await pipeline.process_webhook(
        raw_body=body, signature=sig, event_id=event_id, webhook_secret=WEBHOOK_SECRET
    )
    assert r1.status == "accepted"
    assert r1.classification == "NEW"

    # Second delivery
    r2 = await pipeline.process_webhook(
        raw_body=body, signature=sig, event_id=event_id, webhook_secret=WEBHOOK_SECRET
    )
    assert r2.status == "duplicate"
    assert r2.classification == "DUPLICATE"


@pytest.mark.asyncio
async def test_pipeline_stale_failed_after_captured(
    async_factory: async_sessionmaker[AsyncSession],
    raw_failed_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-09: Captured protection: stale payment.failed cannot regress CAPTURED."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    now = datetime.now(UTC)

    c_id = str(uuid.uuid4())
    p_id = str(uuid.uuid4())
    provider_pay_id = f"pay_captured_{uuid.uuid4().hex[:8]}"

    # Payment is already CAPTURED
    async with async_factory() as session:
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
                status=PaymentStatus.CAPTURED,
                created_at=now,
                updated_at=now,
                captured_at=now,
            )
        )
        await session.commit()

    payload = json.loads(json.dumps(raw_failed_payload))
    payload["payload"]["payment"]["entity"]["id"] = provider_pay_id

    body = json.dumps(payload).encode("utf-8")
    sig = sign_payload(body, WEBHOOK_SECRET)
    event_id = f"evt_stale_{uuid.uuid4().hex[:8]}"

    pipeline = EventPipeline(async_factory)
    result = await pipeline.process_webhook(
        raw_body=body, signature=sig, event_id=event_id, webhook_secret=WEBHOOK_SECRET
    )

    assert result.status == "accepted"
    assert result.classification == "STALE"

    # Verify current payment remains CAPTURED, but historical PaymentEvent was recorded
    async with async_factory() as session:
        p_repo = PaymentRepository(session)
        pevt_repo = PaymentEventRepository(session)

        pay = await p_repo.get_by_id(p_id)
        assert pay is not None
        assert pay.status == PaymentStatus.CAPTURED

        events = await pevt_repo.find_by_payment_id(p_id)
        assert len(events) == 1
        assert events[0].event_type == "payment.failed"


@pytest.mark.asyncio
async def test_pipeline_unsupported_event(
    async_factory: async_sessionmaker[AsyncSession],
    raw_failed_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-12: Authenticated unsupported event returns HTTP 2xx ignored."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

    payload = json.loads(json.dumps(raw_failed_payload))
    payload["event"] = "payment.downtime.updated"

    body = json.dumps(payload).encode("utf-8")
    sig = sign_payload(body, WEBHOOK_SECRET)
    event_id = f"evt_unsupported_{uuid.uuid4().hex[:8]}"

    pipeline = EventPipeline(async_factory)
    result = await pipeline.process_webhook(
        raw_body=body, signature=sig, event_id=event_id, webhook_secret=WEBHOOK_SECRET
    )

    assert result.status == "ignored"
    assert result.classification == "UNSUPPORTED"

    # Raw event evidence persisted
    async with async_factory() as session:
        raw_repo = RawEventRepository(session)
        raw_evt = await raw_repo.find_by_provider_event_id("razorpay", event_id)
        assert raw_evt is not None
        assert raw_evt.event_type == "payment.downtime.updated"


@pytest.mark.asyncio
async def test_pipeline_unknown_provider_payment(
    async_factory: async_sessionmaker[AsyncSession],
    raw_failed_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-14: Unknown provider payment returns UNRESOLVED_PAYMENT."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

    payload = json.loads(json.dumps(raw_failed_payload))
    unk_id = f"pay_unknown_{uuid.uuid4().hex[:8]}"
    payload["payload"]["payment"]["entity"]["id"] = unk_id

    body = json.dumps(payload).encode("utf-8")
    sig = sign_payload(body, WEBHOOK_SECRET)
    event_id = f"evt_unknown_{uuid.uuid4().hex[:8]}"

    pipeline = EventPipeline(async_factory)
    result = await pipeline.process_webhook(
        raw_body=body, signature=sig, event_id=event_id, webhook_secret=WEBHOOK_SECRET
    )

    assert result.status == "accepted"
    assert result.classification == "UNRESOLVED_PAYMENT"


@pytest.mark.asyncio
async def test_pipeline_invalid_signature(
    async_factory: async_sessionmaker[AsyncSession],
    raw_failed_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-01: Invalid signature raises InvalidSignatureError."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    body = json.dumps(raw_failed_payload).encode("utf-8")

    pipeline = EventPipeline(async_factory)
    with pytest.raises(InvalidSignatureError):
        await pipeline.process_webhook(
            raw_body=body,
            signature="invalid_signature_string",
            event_id="evt_123",
            webhook_secret=WEBHOOK_SECRET,
        )


@pytest.mark.asyncio
async def test_pipeline_malformed_json(
    async_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-13: Malformed JSON raises MalformedPayloadError."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    body = b'{"entity": "event", "event": "payment.failed", "payload":'
    sig = sign_payload(body, WEBHOOK_SECRET)

    pipeline = EventPipeline(async_factory)
    with pytest.raises(MalformedPayloadError):
        await pipeline.process_webhook(
            raw_body=body,
            signature=sig,
            event_id="evt_123",
            webhook_secret=WEBHOOK_SECRET,
        )
