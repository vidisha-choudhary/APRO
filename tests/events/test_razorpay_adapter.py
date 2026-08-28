"""Unit tests for RazorpayAdapter mapping and validation."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from apro.domain.enums import PaymentStatus
from apro.events.exceptions import MalformedPayloadError
from apro.events.razorpay_adapter import RazorpayAdapter, payment_status_from_string

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
PAYMENT_FAILED_FIXTURE = FIXTURES_DIR / "payment_failed.json"


@pytest.fixture
def raw_failed_payload() -> dict[str, Any]:
    with open(PAYMENT_FAILED_FIXTURE) as f:
        return json.load(f)


def test_adapter_is_supported_event():
    assert RazorpayAdapter.is_supported_event("payment.failed") is True
    assert RazorpayAdapter.is_supported_event("payment.authorized") is True
    assert RazorpayAdapter.is_supported_event("payment.captured") is True
    assert RazorpayAdapter.is_supported_event("payment.downtime.updated") is False
    assert RazorpayAdapter.is_supported_event("order.paid") is False


def test_payment_status_from_string():
    assert payment_status_from_string("failed") == PaymentStatus.FAILED
    assert payment_status_from_string("authorized") == PaymentStatus.AUTHORIZED
    assert payment_status_from_string("captured") == PaymentStatus.CAPTURED
    assert payment_status_from_string("created") == PaymentStatus.PENDING

    with pytest.raises(MalformedPayloadError):
        payment_status_from_string("unknown_status")


def test_adapter_payment_failed_mapping(raw_failed_payload: dict[str, Any]):
    internal_pay_id = "00000000-0000-0000-0000-000000000001"
    raw_event_id = "11111111-1111-1111-1111-111111111111"
    received_at = datetime.now(UTC)

    event = RazorpayAdapter.to_canonical_event(
        payload=raw_failed_payload,
        internal_payment_id=internal_pay_id,
        raw_event_id=raw_event_id,
        received_at=received_at,
    )

    assert event.provider == "razorpay"
    assert event.event_type == "payment.failed"
    assert event.payment_id == internal_pay_id
    assert event.order_id == "order_failed_123"
    assert event.amount == 50000
    assert event.currency == "INR"
    assert event.method == "card"
    assert event.status == PaymentStatus.FAILED
    assert event.failure_code == "BAD_REQUEST_ERROR"
    assert event.failure_source == "customer"
    assert event.failure_step == "payment_authentication"
    assert event.failure_reason == "payment_failed_incorrect_otp"
    assert event.failure_description == "Payment failed due to incorrect OTP."
    assert event.raw_payload_reference == raw_event_id
    assert event.received_at == received_at


def test_adapter_payment_authorized_mapping(raw_failed_payload: dict[str, Any]):
    payload = json.loads(json.dumps(raw_failed_payload))
    payload["event"] = "payment.authorized"
    payload["payload"]["payment"]["entity"]["status"] = "authorized"
    del payload["payload"]["payment"]["entity"]["error_code"]

    internal_pay_id = "00000000-0000-0000-0000-000000000002"
    raw_event_id = "22222222-2222-2222-2222-222222222222"
    received_at = datetime.now(UTC)

    event = RazorpayAdapter.to_canonical_event(
        payload=payload,
        internal_payment_id=internal_pay_id,
        raw_event_id=raw_event_id,
        received_at=received_at,
    )

    assert event.event_type == "payment.authorized"
    assert event.status == PaymentStatus.AUTHORIZED
    assert event.failure_code is None


def test_adapter_payment_captured_mapping(raw_failed_payload: dict[str, Any]):
    payload = json.loads(json.dumps(raw_failed_payload))
    payload["event"] = "payment.captured"
    payload["payload"]["payment"]["entity"]["status"] = "captured"

    internal_pay_id = "00000000-0000-0000-0000-000000000003"
    raw_event_id = "33333333-3333-3333-3333-333333333333"
    received_at = datetime.now(UTC)

    event = RazorpayAdapter.to_canonical_event(
        payload=payload,
        internal_payment_id=internal_pay_id,
        raw_event_id=raw_event_id,
        received_at=received_at,
    )

    assert event.event_type == "payment.captured"
    assert event.status == PaymentStatus.CAPTURED


def test_adapter_status_mismatch_raises_malformed(raw_failed_payload: dict[str, Any]):
    payload = json.loads(json.dumps(raw_failed_payload))
    payload["event"] = "payment.failed"
    payload["payload"]["payment"]["entity"]["status"] = "captured"  # Mismatch

    with pytest.raises(MalformedPayloadError) as exc_info:
        RazorpayAdapter.to_canonical_event(
            payload=payload,
            internal_payment_id="00000000-0000-0000-0000-000000000001",
            raw_event_id="11111111-1111-1111-1111-111111111111",
            received_at=datetime.now(UTC),
        )
    assert "contradicts payment status" in str(exc_info.value)


def test_adapter_missing_top_level_created_at_raises_malformed(
    raw_failed_payload: dict[str, Any],
):
    payload = json.loads(json.dumps(raw_failed_payload))
    del payload["created_at"]

    with pytest.raises(MalformedPayloadError) as exc_info:
        RazorpayAdapter.to_canonical_event(
            payload=payload,
            internal_payment_id="00000000-0000-0000-0000-000000000001",
            raw_event_id="11111111-1111-1111-1111-111111111111",
            received_at=datetime.now(UTC),
        )
    assert "Missing required provider event timestamp" in str(exc_info.value)
