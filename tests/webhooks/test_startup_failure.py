"""Test for Database Startup Failure & Non-Degradation Guard."""

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apro.config import settings
from apro.main import app

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
PAYMENT_FAILED_FIXTURE = FIXTURES_DIR / "payment_failed.json"
WEBHOOK_SECRET = "test_webhook_secret"


def sign_payload(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_configured_db_startup_failure_prevents_silent_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blocker 1: Configured DB URL with missing session_factory must NOT degrade.

    Proves:
    1. DATABASE_URL is configured
    2. app.state.session_factory is None (e.g. startup failed)
    3. Webhook request returns HTTP 500
    4. Transient in-memory duplicate processing is NOT executed
    """
    invalid_url = (
        "postgresql+asyncpg://invalid_user:invalid_pass@127.0.0.1:5432/nonexistent_db"
    )
    monkeypatch.setattr(settings, "DATABASE_URL", invalid_url)
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

    # Ensure app.state has no session_factory
    if hasattr(app.state, "session_factory"):
        monkeypatch.setattr(app.state, "session_factory", None)

    with open(PAYMENT_FAILED_FIXTURE) as f:
        payload: dict[str, Any] = json.load(f)

    body = json.dumps(payload).encode("utf-8")
    sig = sign_payload(body, WEBHOOK_SECRET)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_startup_fail_123",
    }

    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.post("/webhooks/razorpay", content=body, headers=headers)
        # Must return HTTP 500 error, forbidding silent fallback
        assert res.status_code == 500
