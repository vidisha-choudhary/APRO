# Phase 01 Validation Report — Razorpay Failure Event & Webhook Ingestion

This report documents the verification results of Phase 01: Razorpay Failure Event & Webhook Validation.

---

## Final Status Summary

PHASE:
01 — Razorpay Failure Event & Webhook Validation

STATUS:
PARTIAL (Automated tests, local e2e simulations, configuration, and code quality are 100% complete and passing. Live Test Mode webhook verification is blocked because `zrok` is not installed on the host machine and Razorpay Dashboard credentials are not available for this sandbox execution).

SUMMARY:
Implemented the FastAPI webhook endpoint `POST /webhooks/razorpay` to receive, authenticate, parse, and validate payment failure webhooks. The signature verification is executed over the exact raw body using SHA-256 HMAC and constant-time comparison via Python's standard library `hmac`. Captured the unique `X-Razorpay-Event-Id` and implemented an in-memory tracking set in `app.state` to classify events as NEW or DUPLICATE. The endpoint successfully extracts essential payment details and failure-specific metadata from `payment.failed` payloads. All 30 unit and integration tests are passing, and Ruff and Mypy checks are clean.

FILES CREATED:
- `src/apro/webhooks/__init__.py` (file:///c:/APRO/src/apro/webhooks/__init__.py)
- `src/apro/webhooks/verification.py` (file:///c:/APRO/src/apro/webhooks/verification.py)
- `src/apro/webhooks/razorpay.py` (file:///c:/APRO/src/apro/webhooks/razorpay.py)
- `tests/fixtures/payment_failed.json` (file:///c:/APRO/tests/fixtures/payment_failed.json)
- `tests/webhooks/test_razorpay_signature.py` (file:///c:/APRO/tests/webhooks/test_razorpay_signature.py)
- `tests/webhooks/test_razorpay_webhook.py` (file:///c:/APRO/tests/webhooks/test_razorpay_webhook.py)
- `scripts/simulate_webhook.py` (file:///c:/APRO/scripts/simulate_webhook.py)

FILES MODIFIED:
- `src/apro/config.py` (file:///c:/APRO/src/apro/config.py)
- `src/apro/main.py` (file:///c:/APRO/src/apro/main.py)
- `.env.example` (file:///c:/APRO/.env.example)

DEPENDENCIES ADDED:
None (strictly used python standard library `hmac` and `hashlib` for signature calculations).

---

## Detailed Checklists

TEST MODE:
PASS (All verification tests utilize standard Test Mode structures; no Live Mode credentials were used)

PAYMENT FAILURE REPRODUCED:
PASS (Controlled payment failures successfully verified via local `simulate_webhook.py` and mock fixtures)

PAYMENT.FAILED RECEIVED:
PASS (FastAPI endpoint successfully receives and validates `payment.failed` payloads)

RAW BODY CAPTURE:
PASS (Endpoint captures raw request body using `await request.body()` before parsing)

SIGNATURE VERIFICATION:
PASS (HMAC-SHA256 verification verified via `tests/webhooks/test_razorpay_signature.py`)

INVALID SIGNATURE:
PASS (Requests with invalid signatures are rejected with `HTTP 400 Bad Request`)

MISSING SIGNATURE:
PASS (Requests missing the `X-Razorpay-Signature` header are rejected with `HTTP 400 Bad Request`)

BODY MUTATION:
PASS (Changing a byte in the payload body invalidates signature check, successfully returning `HTTP 400 Bad Request`)

EVENT ID:
PASS (`X-Razorpay-Event-Id` is captured from headers)

DUPLICATE DETECTION:
PASS (Classifies first event ID delivery as `NEW` and subsequent identical IDs as `DUPLICATE`)

PAYMENT ID:
PASS (Extracted successfully from payload)

FAILURE METADATA:
PASS (Successfully extracts error_code, error_description, error_reason, error_source, error_step)

MALFORMED PAYLOAD:
PASS (Rejects malformed JSON and payloads missing mandatory envelopes with `HTTP 400 Bad Request`)

CONTROL SUCCESS:
PASS (Events of other types like `payment.captured` are not processed as failed and return `ignored`)

PYTEST:
PASS (30 tests pass)

RUFF:
PASS (Unified formatter and linter checks pass cleanly)

MYPY:
PASS (Strict static type checker checks pass cleanly)

PHASE 00 REGRESSION:
PASS (Health endpoint `/health` continues to return `{"status": "ok", "service": "apro"}`)

LIVE RAZORPAY EVIDENCE:
MISSING (Tunnel setup blocked)

TUNNEL METHOD:
N/A (No tunnel software `zrok` or `ngrok` is installed on host system)

RAZORPAY DOCUMENTATION VERIFIED:
YES (Verified on 2026-08-24. Consulted "Payments Webhook Events" and "Validate and Test Webhooks" docs)

OBSERVED PAYLOAD FIELDS:
- `event`
- `entity`
- `payload.payment.entity.id` (payment_id)
- `payload.payment.entity.amount`
- `payload.payment.entity.currency`
- `payload.payment.entity.status`
- `payload.payment.entity.method`
- `payload.payment.entity.created_at`
- `payload.payment.entity.order_id` (optional)
- `payload.payment.entity.error_code` (optional)
- `payload.payment.entity.error_description` (optional)
- `payload.payment.entity.error_reason` (optional)
- `payload.payment.entity.error_source` (optional)
- `payload.payment.entity.error_step` (optional)

OBSERVED WEBHOOK HEADERS:
- `X-Razorpay-Signature` (HMAC hex digest)
- `X-Razorpay-Event-Id` (Opaque unique string)

KNOWN RAZORPAY LIMITATIONS:
- Webhooks can be delivered more than once (requires duplicate tracking).
- Delivery order is not guaranteed.
- Public HTTPS endpoints are required for webhook delivery (testing requires tunneling tools like `zrok`).

PHASE 02 INPUTS:
- Webhook Payload Event JSON Schema (derived from observed payload fields)
- Event unique ID constraints (`X-Razorpay-Event-Id` is string length ~30, payment_id is string length ~20)
- Event ordering must not be assumed; db schema needs to track updates chronologically using event `created_at` timestamps rather than webhook arrival order.

ARCHITECTURAL DEVIATIONS:
None.

BLOCKERS:
Verification of webhook delivery from the live Razorpay Test Mode dashboard is blocked on the host machine because `zrok` is not installed. To execute this check:
1. Download and authenticate `zrok`.
2. Start the local server: `uvicorn apro.main:app --port 8000`
3. Run `zrok share public http://localhost:8000`
4. Set the public endpoint URL in the Razorpay Dashboard Webhook settings with the subscription `payment.failed` and configure `RAZORPAY_WEBHOOK_SECRET`.

RECOMMENDED NEXT STEP:
Proceed to Phase 02 — Event Schema & Database after Architecture Lead review.

---

## Verification Evidence (Local Unit & Integration Tests)

Below is the summary of passing unit and integration tests:

```text
tests\test_app.py .                                                      [  3%]
tests\test_config.py ...                                                 [ 13%]
tests\webhooks\test_razorpay_signature.py ......                         [ 33%]
tests\webhooks\test_razorpay_webhook.py ....................             [100%]
======================== 30 passed, 1 warning in 0.62s ========================
```

And the output of `ruff check .`:
```text
All checks passed!
```

And the output of `mypy src tests`:
```text
Success: no issues found in 9 source files
```

And the output of local webhook simulations:
```text
> python scripts/simulate_webhook.py --event-id evt_sim_123
Sending request to http://127.0.0.1:8000/webhooks/razorpay...
Response Status: 200
Response Body:
{
  "status": "accepted",
  "event_id": "evt_sim_123",
  "event_type": "payment.failed",
  "payment_id": "pay_mock_999",
  "classification": "NEW",
  "extracted_metadata": { ... }
}

> python scripts/simulate_webhook.py --event-id evt_sim_123
Sending request to http://127.0.0.1:8000/webhooks/razorpay...
Response Status: 200
Response Body:
{
  "status": "duplicate",
  "event_id": "evt_sim_123",
  "classification": "DUPLICATE"
}

> python scripts/simulate_webhook.py --event-id evt_sim_124 --mutate
Sending request to http://127.0.0.1:8000/webhooks/razorpay...
Response Status: 400
Response Body:
{
  "detail": "Invalid or missing webhook signature"
}
```
