"""Tests for Narrow IntegrityError Handling inside EventPipeline process_webhook."""

import hashlib
import hmac
import json
import os
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apro.config import settings
from apro.events.pipeline import EventPipeline, is_provider_event_uniqueness_error
from apro.persistence.base import Base
from apro.persistence.repositories import RawEventRepository

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


def test_is_provider_event_uniqueness_error_helper():
    """Verify helper identifies provider event uniqueness constraint errors strictly."""
    orig_msg_pg = (
        "duplicate key value violates unique constraint "
        '"uq_raw_events_provider_event_id"'
    )
    exc_pg = IntegrityError(
        statement="INSERT INTO raw_events...",
        params={},
        orig=Exception(orig_msg_pg),
    )
    assert is_provider_event_uniqueness_error(exc_pg) is True

    orig_msg_sqlite = (
        "UNIQUE constraint failed: raw_events.provider, raw_events.provider_event_id"
    )
    exc_sqlite = IntegrityError(
        statement="INSERT INTO raw_events...",
        params={},
        orig=Exception(orig_msg_sqlite),
    )
    assert is_provider_event_uniqueness_error(exc_sqlite) is True

    # Unrelated unique constraint (e.g. payment_events or customers)
    unrelated_msg = (
        "duplicate key value violates unique constraint "
        '"uq_payments_provider_payment_id"'
    )
    exc_unrelated_unique = IntegrityError(
        statement="INSERT INTO payments...",
        params={},
        orig=Exception(unrelated_msg),
    )
    assert is_provider_event_uniqueness_error(exc_unrelated_unique) is False

    # Unrelated FK error
    exc_fk = IntegrityError(
        statement="INSERT INTO raw_events...",
        params={},
        orig=Exception("FOREIGN KEY constraint failed"),
    )
    assert is_provider_event_uniqueness_error(exc_fk) is False


@pytest.mark.asyncio
async def test_unexpected_integrity_error_internal_branch_propagates(
    pg_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blocker 2: Unexpected integrity error propagates out of process_webhook."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

    with open(PAYMENT_FAILED_FIXTURE) as f:
        payload: dict[str, Any] = json.load(f)

    body = json.dumps(payload).encode("utf-8")
    sig = sign_payload(body, WEBHOOK_SECRET)
    evt_id = f"evt_unexp_{uuid.uuid4().hex[:8]}"

    pipeline = EventPipeline(pg_session_factory)

    unexpected_exc = IntegrityError(
        statement="INSERT INTO raw_events...",
        params={},
        orig=Exception("violates foreign key constraint fk_unrelated_table"),
    )

    # Patch raw_events.save to raise unexpected IntegrityError inside process_webhook
    with patch.object(RawEventRepository, "save", side_effect=unexpected_exc):
        with pytest.raises(IntegrityError) as exc_info:
            await pipeline.process_webhook(
                raw_body=body,
                signature=sig,
                event_id=evt_id,
                webhook_secret=WEBHOOK_SECRET,
            )
        assert "fk_unrelated_table" in str(exc_info.value)


@pytest.mark.asyncio
async def test_expected_uniqueness_integrity_error_internal_branch_returns_duplicate(
    pg_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blocker 2: Expected uniqueness conflict returns DUPLICATE."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

    with open(PAYMENT_FAILED_FIXTURE) as f:
        payload: dict[str, Any] = json.load(f)

    body = json.dumps(payload).encode("utf-8")
    sig = sign_payload(body, WEBHOOK_SECRET)
    evt_id = f"evt_dup_{uuid.uuid4().hex[:8]}"

    pipeline = EventPipeline(pg_session_factory)

    dup_msg = (
        "duplicate key value violates unique constraint "
        '"uq_raw_events_provider_event_id"'
    )
    expected_exc = IntegrityError(
        statement="INSERT INTO raw_events...",
        params={},
        orig=Exception(dup_msg),
    )

    # Patch raw_events.save to raise expected uniqueness IntegrityError inside pipeline
    with patch.object(RawEventRepository, "save", side_effect=expected_exc):
        res = await pipeline.process_webhook(
            raw_body=body,
            signature=sig,
            event_id=evt_id,
            webhook_secret=WEBHOOK_SECRET,
        )
        assert res.status == "duplicate"
        assert res.classification == "DUPLICATE"
        assert res.event_id == evt_id
