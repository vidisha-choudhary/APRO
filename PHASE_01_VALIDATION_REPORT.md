# Phase 01 Validation Report — Razorpay Failure Event & Webhook Ingestion

This report documents the verification results of Phase 01: Razorpay Failure Event & Webhook Validation.

---

## Final Status Summary

PHASE:
01 — Razorpay Failure Event & Webhook Validation

STATUS:
PASS (Phase 01 validation is 100% complete. Automated unit & integration tests, static code quality checks, local simulation tools, and real live Razorpay Test Mode webhook ingestion over public zrok HTTPS tunnel are verified and passing).

SUMMARY:
Implemented the FastAPI webhook endpoint `POST /webhooks/razorpay` to receive, authenticate, parse, and validate payment failure webhooks. The signature verification is executed over the exact raw body using SHA-256 HMAC and constant-time comparison via Python's standard library `hmac`. Captured the unique `X-Razorpay-Event-Id` and implemented an in-memory tracking set in `app.state` to classify events as NEW or DUPLICATE. The endpoint successfully extracts essential payment details and failure-specific metadata from `payment.failed` payloads. All 30 unit and integration tests are passing, Ruff and Mypy checks are clean, and real Razorpay Test Mode webhooks were successfully ingested and validated over a public `zrok` HTTPS tunnel.

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

LOCAL PAYMENT.FAILED SIMULATION:
PASS (Controlled payment failures successfully verified via local `simulate_webhook.py` and mock fixtures)

LIVE RAZORPAY TEST MODE PAYMENT FAILURE:
PASS (Real Razorpay Test Mode payment failures triggered `payment.failed` webhooks received over public HTTPS tunnel)

LIVE RAZORPAY WEBHOOK EVIDENCE:
PRESENT (Real `payment.failed` webhooks reached APRO, passed HMAC verification, and extracted failure metadata)

RAW BODY CAPTURE:
PASS (Endpoint captures raw request body using `await request.body()` before parsing)

SIGNATURE VERIFICATION:
PASS (HMAC-SHA256 verification verified via `tests/webhooks/test_razorpay_signature.py` and live webhooks)

INVALID SIGNATURE:
PASS (Requests with invalid or mutated signatures are rejected with `HTTP 400 Bad Request`)

MISSING SIGNATURE:
PASS (Requests missing the `X-Razorpay-Signature` header are rejected with `HTTP 400 Bad Request`)

BODY MUTATION:
PASS (Changing a byte in the payload body invalidates signature check, returning `HTTP 400 Bad Request`)

EVENT ID:
PASS (`X-Razorpay-Event-Id` is captured from headers)

DUPLICATE DETECTION:
PASS (Classifies first event ID delivery as `NEW` and subsequent identical IDs as `DUPLICATE` in-memory)

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
PASS (Formatter and linter checks pass cleanly across all source, test, and script files)

MYPY:
PASS (Strict static type checker checks pass cleanly with 0 errors across 5 source files)

PHASE 00 REGRESSION:
PASS (Health endpoint `/health` continues to return `{"status": "ok", "service": "apro"}`)

LIVE RAZORPAY EVIDENCE:
PRESENT (Live webhooks received over public tunnel; signatures verified and metadata extracted)

TUNNEL METHOD:
`zrok share public http://localhost:8000`

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
None.

RECOMMENDED NEXT STEP:
Proceed to Phase 02 — Event Schema & Database.

---

## Live Razorpay Test Mode Evidence Log

### 1. Real Test Mode Webhook Delivery (Public zrok Ingress)
- **Ingress Tunnel:** `zrok share public http://localhost:8000`
- **Target Endpoint:** `POST /webhooks/razorpay`
- **Events Validated Live:**
  - Event ID `TUjiGuHpBK6wGt` (Payment `pay_TUjhysnYIt3LeL`): Verified HMAC-SHA256 signature, extracted metadata, returned `HTTP 200 OK`, `status: accepted`, `classification: NEW`.
  - Event ID `TUjcyBLBxXJKT9` (Payment `pay_TUjYkNAJzQmC5L`): Verified HMAC-SHA256 signature, extracted metadata, returned `HTTP 200 OK`, `status: accepted`, `classification: NEW`.

### 2. Live Duplicate Event Delivery Verification
- **Test Target:** Event ID `evt_dup_verification_001`
- **First Delivery:**
  - `HTTP 200 OK`
  - Body: `{"status": "accepted", "event_id": "evt_dup_verification_001", "classification": "NEW", ...}`
- **Second Delivery (Identical Request without Application Restart):**
  - `HTTP 200 OK`
  - Body: `{"status": "duplicate", "event_id": "evt_dup_verification_001", "classification": "DUPLICATE"}`
- **Verification:** Proves in-memory duplicate event detection (`app.state.processed_event_ids`) correctly identifies repeated event IDs without re-processing as new events.

### 3. Live Invalid Signature & Body Mutation Verification
- **Test Target:** Event ID `evt_mutation_test_002`
- **Execution:** HMAC signature calculated over original payload body; body subsequently mutated (`amount` changed) before transmission.
- **Outcome:** APRO recalculated HMAC-SHA256 over exact raw bytes, detected signature mismatch, logged `Signature verification failed`, and rejected request with `HTTP 400 Bad Request` (`{"detail": "Invalid or missing webhook signature"}`).

---

## Verification Evidence (Local Unit & Integration Tests)

Below is the summary of passing unit and integration tests:

```text
tests\test_app.py .                                                      [  3%]
tests\test_config.py ...                                                 [ 13%]
tests\webhooks\test_razorpay_signature.py ......                         [ 33%]
tests\webhooks\test_razorpay_webhook.py ................................ [100%]
======================== 30 passed, 1 warning in 1.01s ========================
```

Output of `ruff check .`:
```text
All checks passed!
```

Output of `mypy src`:
```text
Success: no issues found in 5 source files
```
