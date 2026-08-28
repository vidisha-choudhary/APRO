import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from apro.config import settings
from apro.main import app

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
PAYMENT_FAILED_FIXTURE_PATH = FIXTURES_DIR / "payment_failed.json"


@pytest.fixture
def valid_payload() -> dict[str, Any]:
    with open(PAYMENT_FAILED_FIXTURE_PATH) as f:
        return cast(dict[str, Any], json.load(f))


@pytest.fixture
def secret_setup(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "test_webhook_secret"
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", secret)
    return secret


@pytest.fixture(autouse=True)
def disable_db_session_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure legacy isolated unit tests use standalone router path without DB."""
    monkeypatch.setattr(settings, "DATABASE_URL", None)
    if hasattr(app.state, "session_factory"):
        monkeypatch.setattr(app.state, "session_factory", None)


def sign_payload(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_health_endpoint_regression() -> None:
    """Ensure Phase 00 health endpoint continues to return expected status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "apro"}


def test_valid_webhook_payment_failed(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test standard payment.failed webhook verification and extraction."""
    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)

    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_test_failed_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "accepted"
    assert res_data["classification"] == "NEW"
    assert res_data["event_id"] == "evt_test_failed_123"

    meta = res_data["extracted_metadata"]
    assert meta["payment_id"] == "pay_failed_123"
    assert meta["amount"] == 50000
    assert meta["currency"] == "INR"
    assert meta["status"] == "failed"
    assert meta["method"] == "card"
    assert meta["order_id"] == "order_failed_123"
    assert meta["created_at"] == 1672531199
    assert meta["error_code"] == "BAD_REQUEST_ERROR"
    assert meta["error_description"] == "Payment failed due to incorrect OTP."
    assert meta["error_reason"] == "payment_failed_incorrect_otp"
    assert meta["error_source"] == "customer"
    assert meta["error_step"] == "payment_authentication"


def test_webhook_invalid_signature(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test invalid signature is explicitly rejected with 400."""
    _ = secret_setup
    body = json.dumps(valid_payload).encode("utf-8")
    headers = {
        "X-Razorpay-Signature": "invalid_sig_here",
        "X-Razorpay-Event-Id": "evt_test_failed_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert response.status_code == 400
    assert "signature" in response.json()["detail"].lower()


def test_webhook_missing_signature(valid_payload: dict[str, Any]) -> None:
    """Test missing signature is rejected with 400."""
    body = json.dumps(valid_payload).encode("utf-8")
    headers = {
        "X-Razorpay-Event-Id": "evt_test_failed_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert response.status_code == 400


def test_webhook_missing_event_id(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test missing event ID header is rejected with 400."""
    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)
    headers = {
        "X-Razorpay-Signature": sig,
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert response.status_code == 400


def test_webhook_duplicate_event_id(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test duplicate delivery (same event ID) returns duplicate classification."""
    # Reset in-memory tracking in TestClient app state
    app.state.processed_event_ids = set()

    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)
    event_id = "evt_duplicate_test_999"

    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": event_id,
    }

    # First delivery: accepted
    r1 = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["classification"] == "NEW"

    # Second delivery: duplicate detected (marked DUPLICATE)
    r2 = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "duplicate"
    assert r2.json()["classification"] == "DUPLICATE"
    assert r2.json()["event_id"] == event_id


def test_webhook_wrong_event_type(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test non-payment events are ignored and not processed as payment failures."""
    valid_payload["event"] = "payment.downtime.updated"
    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)

    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_test_downtime_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ignored"
    assert "Unsupported event type" in res_data["reason"]


def test_webhook_malformed_json(secret_setup: str) -> None:
    """Test malformed JSON is rejected with 400."""
    body = b'{"entity": "event", "event": "payment.failed", "payload":'  # incomplete
    sig = sign_payload(body, secret_setup)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_test_malformed_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert response.status_code == 400
    assert "JSON" in response.json()["detail"]


def test_webhook_missing_required_fields(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test payload validation fails if critical required fields are missing."""
    entity = valid_payload["payload"]["payment"]["entity"]

    # Test missing payment ID
    entity["id"] = None
    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_missing_id_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert response.status_code == 400


def test_webhook_optional_fields_missing(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test that missing optional fields do not cause failure."""
    entity = valid_payload["payload"]["payment"]["entity"]
    entity["order_id"] = None
    entity["error_code"] = None
    entity["error_description"] = None
    entity["error_reason"] = None
    entity["error_source"] = None
    entity["error_step"] = None

    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_optional_missing_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)

    assert response.status_code == 200
    meta = response.json()["extracted_metadata"]
    assert meta["payment_id"] == "pay_failed_123"
    assert meta["order_id"] is None
    assert meta["error_code"] is None


def test_webhook_status_inconsistency(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test status other than 'failed' triggers inconsistency 400."""
    entity = valid_payload["payload"]["payment"]["entity"]

    entity["status"] = (
        "captured"  # Mismatch: event is payment.failed, status is captured
    )

    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_mismatch_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)

    assert response.status_code == 400
    assert "inconsistent payment status" in response.json()["detail"].lower()


def test_webhook_missing_event_field(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test payload validation fails if event field is missing."""
    del valid_payload["event"]
    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_missing_event_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert response.status_code == 400


def test_webhook_missing_payload_field(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test payload validation fails if payload container is missing."""
    del valid_payload["payload"]
    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_missing_payload_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert response.status_code == 400


def test_webhook_missing_payment_field(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test payload validation fails if payment details are missing."""
    del valid_payload["payload"]["payment"]
    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_missing_payment_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert response.status_code == 400


def test_webhook_missing_payment_entity(
    valid_payload: dict[str, Any], secret_setup: str
) -> None:
    """Test payload validation fails if payment entity is missing."""
    del valid_payload["payload"]["payment"]["entity"]
    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_missing_entity_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert response.status_code == 400


@pytest.mark.parametrize(
    "field", ["amount", "currency", "status", "method", "created_at"]
)
def test_webhook_missing_required_payment_fields(
    valid_payload: dict[str, Any], secret_setup: str, field: str
) -> None:
    """Test payload validation fails if critical payment fields are missing."""
    entity = valid_payload["payload"]["payment"]["entity"]
    if field in entity:
        del entity[field]
    body = json.dumps(valid_payload).encode("utf-8")
    sig = sign_payload(body, secret_setup)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": f"evt_missing_{field}_123",
    }
    response = client.post("/webhooks/razorpay", content=body, headers=headers)
    assert response.status_code == 400
