# APRO --- Phase 01 Razorpay Failure Event & Webhook Validation Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)\
**Track:** Razorpay AI Buildathon 2026 --- Track 03: AI Revenue
Recovery\
**Phase:** 01 --- Razorpay Failure Events, Failure Metadata & Webhook
Validation\
**Specification:**
`PHASE_01_RAZORPAY_FAILURE_EVENT_AND_WEBHOOK_VALIDATION_SPECIFICATION.md`\
**Version:** 2.0\
**Status:** Architecture Specification --- Ready for Implementation\
**Architecture Authority:** Architectural Lead\
**Implementation Authority:** Antigravity\
**Repository:** APRO

------------------------------------------------------------------------

## 1. Purpose

Phase 01 is the first technical validation phase of APRO.

Its purpose is to prove, with Razorpay Test Mode and the actual APRO
application, that APRO can reliably observe a supported Razorpay payment
failure and receive the corresponding webhook event with trustworthy
metadata.

The phase must establish:

``` text
Razorpay Test Mode
        ↓
Test payment attempt
        ↓
Payment failure
        ↓
Razorpay `payment.failed` webhook
        ↓
APRO webhook endpoint
        ↓
Raw-body capture
        ↓
Webhook signature verification
        ↓
Event identity capture
        ↓
Payload validation
        ↓
Failure metadata extraction
        ↓
Structured Phase 01 validation record
```

Phase 01 is a **Razorpay integration-validation phase**.

It is NOT the domain-model phase, database phase, failure-taxonomy
phase, AI phase, policy phase, execution phase, or dashboard phase.

------------------------------------------------------------------------

## 2. Critical Phase Boundary

The authoritative APRO development sequence defines:

``` text
PHASE 1
Validate Razorpay failure events and webhooks.

PHASE 2
Define event schema and database.

PHASE 3
Build failure taxonomy.

PHASE 4
Build synthetic evaluation dataset.

PHASE 5
Build recovery probability/value engine.

PHASE 6
Build LLM decision agent.

PHASE 7
Build policy/guardrail engine.

PHASE 8
Build controlled execution tools.

PHASE 9
Build outcome measurement and audit trail.

PHASE 10
Build command-center dashboard.

PHASE 11
Run batch evaluation against baseline.

PHASE 12
Polish demo and submission.
```

Therefore, this specification deliberately does **not** introduce a new
"Phase 01 Domain Foundation" boundary.

A separate domain specification may be created later only if it is
explicitly assigned to a phase or architecture milestone.

------------------------------------------------------------------------

## 3. Correction to the Previous Phase 01 Document

The previous document named
`PHASE_01_DOMAIN_IMPLEMENTATION_SPECIFICATION.md` defined Phase 01 as a
domain foundation containing Payment, PaymentAttempt, PaymentFailure,
RecoveryCase, RecoveryDecision, Execution, RecoveryOutcome, state
machines, invariants, and value objects.

That document was internally coherent as a possible architecture
artifact, but it was **incorrect as the Phase 01 specification** because
the locked APRO development sequence defines Phase 01 as validation of
Razorpay failure events and webhooks.

The corrected Phase 01 must therefore validate the real external event
boundary before the production event schema and database are designed.

**Instruction:** Do not use the old domain specification as the
implementation authority for Phase 01.

------------------------------------------------------------------------

## 4. Project Context

APRO is a reactive payment-recovery system.

The central business event is:

``` text
PAYMENT FAILURE
```

The intended product loop is:

``` text
PAYMENT FAILURE
      ↓
UNDERSTAND FAILURE
      ↓
ASSESS RECOVERY
      ↓
SELECT PERMITTED ACTION
      ↓
EXECUTE
      ↓
OBSERVE RESULT
      ↓
RETRY / CHANGE STRATEGY / ESCALATE / STOP
      ↓
MEASURE RECOVERY
```

APRO is distinct from the separate proactive trial-to-paid recovery
project.

APRO is:

``` text
Payment failure
→ diagnosis
→ adaptive recovery
→ recovered payment
```

It is not:

``` text
Trial
→ future revenue risk
→ intervention
→ conversion
```

This distinction remains locked.

------------------------------------------------------------------------

## 5. Phase 01 Objective

Phase 01 must answer:

> Can APRO reliably receive, authenticate, identify, and understand a
> supported Razorpay Test Mode payment-failure webhook?

The phase must establish evidence for:

1.  A supported Test Mode payment-failure path exists.
2.  A test transaction can intentionally fail.
3.  Razorpay emits `payment.failed`.
4.  The webhook reaches APRO.
5.  APRO receives the raw request body.
6.  APRO can validate `X-Razorpay-Signature`.
7.  APRO can capture `x-razorpay-event-id`.
8.  APRO can parse the payload after signature verification.
9.  APRO can identify the failed payment.
10. APRO can extract the relevant failure metadata.
11. Duplicate webhook delivery can be detected conceptually.
12. Event ordering is not assumed.
13. The observed payload is sufficient to inform Phase 02 schema design.
14. All claims are based on observed Test Mode behavior rather than
    assumptions.

------------------------------------------------------------------------

## 6. In Scope

Phase 01 includes:

-   Razorpay Test Mode validation.
-   A controlled payment-failure test transaction.
-   Razorpay payment webhook configuration.
-   `payment.failed` subscription.
-   APRO webhook endpoint.
-   Public HTTPS exposure for webhook delivery.
-   Raw request-body capture.
-   Webhook secret configuration.
-   HMAC-SHA256 signature verification.
-   `X-Razorpay-Signature` handling.
-   `x-razorpay-event-id` capture.
-   Duplicate-event detection at validation level.
-   Webhook payload capture.
-   Payload parsing after signature verification.
-   `payment.failed` event validation.
-   Payment entity extraction.
-   Provider failure-metadata extraction.
-   Safe Test Mode logging.
-   Automated webhook validation tests.
-   End-to-end Test Mode verification.
-   Evidence capture.
-   Phase 01 validation report.

------------------------------------------------------------------------

## 7. Explicitly Out of Scope

Do NOT implement:

-   PostgreSQL.
-   SQLAlchemy.
-   Alembic.
-   Production event persistence.
-   Production event schema.
-   Full domain model.
-   Recovery-case state machine.
-   Final failure taxonomy.
-   ML models.
-   Recovery probability model.
-   Expected recovery value.
-   LLM decision agent.
-   Policy engine.
-   Safety engine.
-   Recovery action ranking.
-   Payment retry scheduler.
-   Payment Link recovery execution.
-   Customer outreach execution.
-   Human approval workflow.
-   Autonomous recovery.
-   Revenue attribution.
-   Control groups.
-   Synthetic evaluation dataset.
-   Dashboard.
-   Command center.
-   Production audit subsystem.
-   Batch evaluation.
-   Production deployment.

If implementation appears to require one of these, STOP and report the
dependency.

------------------------------------------------------------------------

## 8. Authoritative Razorpay Validation Rule

Before using any Razorpay capability:

1.  Check current official Razorpay documentation.
2.  Verify the exact endpoint/event.
3.  Verify Test Mode support.
4.  Verify the request/response structure.
5.  Verify the security requirements.
6.  Test the capability.
7.  Only then incorporate it into APRO.

Never invent a Razorpay endpoint, webhook event, failure simulation
mechanism, or recovery capability.

------------------------------------------------------------------------

## 9. Current Known Razorpay Validation Status

The APRO architectural record states that the following have already
been manually validated:

-   Test API credentials.
-   GET Payments API.
-   POST Orders API.
-   Razorpay Dashboard Test Mode.
-   Subscriptions product.
-   Dashboard plan creation.
-   Test Plan creation.
-   Test Subscription creation.
-   Future subscription start date.
-   Subscription ID generation.

Those validations do **not** prove payment-failure webhook ingestion.

Phase 01 specifically closes the validation gap around:

``` text
actual payment failure events
+
webhook ingestion
+
failure metadata
+
test-mode failure simulation
+
signature verification
+
event identity / duplicate delivery
```

------------------------------------------------------------------------

## 10. Primary Razorpay Event

The primary event for Phase 01 is:

``` text
payment.failed
```

This is the canonical payment-failure webhook event APRO must validate.

Do not substitute `payment.captured`, `order.paid`, or another event for
the core failure-validation requirement.

------------------------------------------------------------------------

## 11. Test Mode Requirement

All Phase 01 financial activity must use Razorpay Test Mode.

No real money may move.

No Live Mode credentials may be used.

No production customer data may be used.

The implementation report must explicitly identify the environment as
Test Mode.

------------------------------------------------------------------------

## 12. Failure Simulation Requirement

The preferred validation path is a supported Razorpay Test Mode payment
flow in which the payment outcome can be intentionally made to fail.

Current Razorpay documentation describes Test Mode failure simulation
for supported payment methods, including a documented UPI test
identifier for failure and mock failure flows for supported payment
methods.

Antigravity must verify the currently supported failure mechanism
against the actual Test Mode environment before execution.

Do not hard-code a failure mechanism solely from memory.

------------------------------------------------------------------------

## 13. Test Case A --- Controlled Payment Failure

Create a deterministic Test Mode payment attempt.

Expected:

``` text
payment attempt
      ↓
failure
      ↓
Razorpay payment status = failed
      ↓
payment.failed webhook
```

Capture evidence for:

-   Test transaction.
-   Payment identifier.
-   Failure outcome.
-   Webhook receipt.
-   Event identifier.
-   Signature verification result.
-   Extracted failure metadata.

------------------------------------------------------------------------

## 14. Test Case B --- Successful Control Transaction

Perform one successful Test Mode transaction as a control.

Purpose:

``` text
prove that the test harness can distinguish
success from failure.
```

Expected:

``` text
successful transaction
≠
payment.failed
```

This control does not implement the later success domain model.

------------------------------------------------------------------------

## 15. Webhook Configuration

Configure the Razorpay Test Mode webhook from the Dashboard using a
dedicated APRO endpoint.

The webhook subscription must include:

``` text
payment.failed
```

Do not enable unrelated events unless required for a specific validation
experiment.

Keep the Phase 01 webhook configuration minimal.

------------------------------------------------------------------------

## 16. Webhook Secret

The Test Mode webhook must have a dedicated webhook secret.

Important:

``` text
Webhook secret
≠
Razorpay API key secret
```

The webhook secret is used for webhook signature verification.

Never hard-code it in source code.

Never commit it to Git.

Use the repository's existing environment configuration mechanism.

------------------------------------------------------------------------

## 17. Public Endpoint Requirement

Razorpay webhook delivery requires a publicly reachable endpoint.

A local endpoint such as:

``` text
http://127.0.0.1:8000/webhooks/razorpay
```

is not directly reachable by Razorpay.

APRO may run locally, but it must be exposed through a supported public
HTTPS tunnel or staging endpoint.

------------------------------------------------------------------------

## 18. Local Development Exposure

Razorpay's current webhook documentation states that localhost cannot
directly receive webhook events because delivery requires a public URL.

Razorpay currently documents `zrok` as an option for tunneling localhost
and maintains restrictions/blacklists for some common testing and
tunneling domains.

Therefore:

``` text
local APRO
    ↓
supported public HTTPS tunnel
    ↓
Razorpay Test Mode
```

The exact tunnel/staging method used must be recorded in the validation
report.

------------------------------------------------------------------------

## 19. Endpoint Shape

Expose one dedicated webhook endpoint, for example:

``` text
POST /webhooks/razorpay
```

The exact route may differ, but it must be:

-   dedicated to Razorpay webhook ingestion,
-   documented,
-   testable,
-   isolated from normal application endpoints.

Do not use `/health` for webhook processing.

------------------------------------------------------------------------

## 20. Raw Request Body Requirement

This is a hard security requirement.

The webhook signature must be calculated against the **raw request
body**.

Do not parse JSON, reserialize JSON, and then calculate the signature.

Correct sequence:

``` text
HTTP request
      ↓
read raw body
      ↓
read signature header
      ↓
verify signature
      ↓
only then parse JSON
```

------------------------------------------------------------------------

## 21. Signature Header

The implementation must read:

``` text
X-Razorpay-Signature
```

A missing signature must be rejected.

An invalid signature must be rejected.

A valid signature permits further processing.

------------------------------------------------------------------------

## 22. Signature Algorithm

Razorpay documents webhook signatures as HMAC-SHA256.

Conceptually:

``` text
key:
    webhook_secret

message:
    raw_webhook_body

expected_signature:
    HMAC-SHA256(message, key)
```

Compare the expected and received signatures using a constant-time
comparison.

Do not log the webhook secret.

------------------------------------------------------------------------

## 23. Signature Verification Ordering

Required order:

``` text
1. Receive request.
2. Capture raw body.
3. Capture signature header.
4. Verify signature.
5. Reject invalid signature.
6. Parse JSON.
7. Validate event type.
8. Capture event identity.
9. Extract payment data.
10. Record validation result.
11. Return webhook response.
```

Do not trust payload content before signature verification.

------------------------------------------------------------------------

## 24. Invalid Signature Test

Send a payload with a valid body and an incorrect signature.

Expected:

``` text
HTTP 4xx

request rejected

event not trusted
```

The exact HTTP status may be chosen by implementation, but rejection
must be explicit.

------------------------------------------------------------------------

## 25. Missing Signature Test

Send a valid-looking payload without `X-Razorpay-Signature`.

Expected:

``` text
request rejected
```

No trusted payment-failure observation may be created.

------------------------------------------------------------------------

## 26. Body Mutation Test

Take a known valid webhook body, modify one or more bytes, and reuse the
original signature.

Expected:

``` text
signature verification fails
```

This proves that the implementation is verifying the raw body rather
than a normalized JSON representation.

------------------------------------------------------------------------

## 27. Event Identity Header

Capture:

``` text
x-razorpay-event-id
```

Treat this value as the event identity supplied by Razorpay.

Do not construct a substitute identity from payment ID plus timestamp
when the provider event ID is available.

------------------------------------------------------------------------

## 28. Duplicate Delivery

Razorpay documents that duplicate webhook delivery can occur.

Phase 01 must demonstrate that APRO can identify duplicate delivery
using `x-razorpay-event-id`.

Persistence is out of scope, so an in-memory set or test double may be
used strictly for validation.

This temporary mechanism must not be presented as production
idempotency.

------------------------------------------------------------------------

## 29. Duplicate Test

Send the same authenticated webhook event twice using the same event ID.

Expected:

``` text
first delivery:
    accepted

second delivery:
    duplicate detected
```

The second delivery must not be interpreted as a new distinct event.

Persistent idempotency belongs to Phase 02.

------------------------------------------------------------------------

## 30. Event Ordering

Razorpay documents that webhook events may not always arrive in the
order in which the underlying events occurred.

Therefore Phase 01 must not assume a fixed webhook-delivery order.

This must be explicitly recorded as a Phase 02 schema/design constraint.

------------------------------------------------------------------------

## 31. `payment.failed` Payload Envelope

The documented payment webhook envelope contains concepts such as:

``` text
account_id
contains
created_at
entity
event
payload
```

For the target event:

``` text
event == "payment.failed"
```

The actual Test Mode payload received by APRO is authoritative for the
integration evidence.

Do not fabricate a local payload and call it a live observation.

------------------------------------------------------------------------

## 32. `payment.failed` Event Validation

For a trusted target event, validate:

``` text
entity == "event"
event == "payment.failed"
payload.payment.entity exists
```

If the actual Test Mode payload differs materially from current
documentation, stop and report the discrepancy.

------------------------------------------------------------------------

## 33. Required Payment Metadata

Capture, at minimum, the fields needed to identify and understand the
failed payment:

``` text
payment_id
amount
currency
status
method
order_id (when present)
created_at
error_code
error_description
error_reason
error_source
error_step
```

Some fields may be empty or null depending on the payment method and
failure scenario.

Preserve absent/null values; do not invent them.

------------------------------------------------------------------------

## 34. Failure Metadata vs APRO Diagnosis

Phase 01 records:

``` text
provider failure metadata
```

It does not produce:

``` text
APRO failure diagnosis
```

For example:

``` text
error_code
error_description
error_reason
error_source
error_step
```

are observed provider data.

The final APRO failure taxonomy belongs to Phase 03.

Do not silently convert provider fields into final APRO categories
during Phase 01.

------------------------------------------------------------------------

## 35. Payment Identifier

For `payment.failed`, extract the provider payment identifier from the
payment entity.

Preserve the identifier exactly as received.

Do not generate a new production payment identity in Phase 01.

------------------------------------------------------------------------

## 36. Amount and Currency

Capture `amount` exactly as received.

Capture `currency` exactly as received.

Do not:

-   convert currency,
-   calculate recovery value,
-   use floating-point currency arithmetic as a business decision,
-   assume INR for every payment.

The final persistent monetary representation belongs to Phase 02 schema
design.

------------------------------------------------------------------------

## 37. Payment Status and Method

Capture the observed payment `status` and `method`.

For a valid `payment.failed` event, verify that the observed payment
state is consistent with failure.

If the event name and payment state materially disagree, do not silently
normalize the discrepancy. Record it and stop the validation run for
review.

Provider method values must be treated as provider data, not as the
final APRO failure taxonomy.

------------------------------------------------------------------------

## 38. Order Relationship

If `order_id` is present, capture it.

Do not assume every payment has an order unless the actual integration
path guarantees it.

Phase 01 records the observed relationship only.

------------------------------------------------------------------------

## 39. Error Fields

Capture provider error fields separately:

``` text
error_code
error_description
error_reason
error_source
error_step
```

Do not collapse them into one field.

These fields are inputs to later failure analysis.

------------------------------------------------------------------------

## 40. Sensitive Data Handling

Webhook payloads may contain customer/payment information.

Phase 01 logging must minimize sensitive data.

Do not log:

-   API credentials,
-   webhook secrets,
-   authorization tokens,
-   unnecessary full card details,
-   unnecessary personal data.

If a raw payload is retained for Test Mode evidence, redact it before
committing documentation.

------------------------------------------------------------------------

## 41. Logging Requirements

Recommended validation log fields:

``` text
event_id
event_type
payment_id
payment_status
validation_status
signature_valid
received_at
```

Avoid logging secrets or unnecessary full payloads.

------------------------------------------------------------------------

## 42. Response Behavior

For an authenticated, structurally valid `payment.failed` event:

``` text
HTTP 2xx
```

For an invalid signature:

``` text
HTTP 4xx
```

For malformed JSON:

``` text
HTTP 4xx
```

For an unsupported event, the implementation must not process it as
`payment.failed`.

The chosen response policy must be documented.

Do not introduce slow recovery or AI processing into the webhook path.

------------------------------------------------------------------------

## 43. Webhook Processing Boundary

Phase 01 terminates at:

``` text
validated observation
```

It must not perform:

``` text
failure diagnosis
recovery decision
retry
Payment Link creation
customer outreach
AI reasoning
policy evaluation
```

------------------------------------------------------------------------

## 44. No Database

Phase 01 does not create production database tables.

Temporary in-memory structures may be used only for duplicate-event
demonstration and tests.

They must not be presented as the Phase 02 persistence design.

------------------------------------------------------------------------

## 45. No Full Domain Model

Do not implement the previous incorrect Phase 01 domain architecture as
part of this phase.

Specifically, Phase 01 is not responsible for production implementation
of:

``` text
Payment aggregate
PaymentAttempt aggregate
PaymentFailure aggregate
RecoveryCase
RecoveryDecision
Execution
RecoveryOutcome
```

Phase 01 produces validated event evidence that will inform later
schema/domain work.

------------------------------------------------------------------------

## 46. No Failure Taxonomy

Do not build the final APRO failure taxonomy in Phase 01.

Provider-level error metadata is observed now.

The normalized APRO taxonomy belongs to Phase 03.

------------------------------------------------------------------------

## 47. No AI

Phase 01 contains:

``` text
NO LLM
NO ML
NO AGENT
NO EMBEDDINGS
NO AI DECISION
```

------------------------------------------------------------------------

## 48. No Recovery Logic

Phase 01 must not:

``` text
retry a payment
choose a recovery action
send a payment link
contact a customer
escalate a customer
stop a recovery case
calculate expected recovery
```

------------------------------------------------------------------------

## 49. No Production Claims

After Phase 01, do not claim that APRO can recover failed payments.

The valid Phase 01 claim is:

``` text
APRO can receive and validate supported Razorpay Test Mode
payment-failure webhooks and extract their provider failure metadata.
```

------------------------------------------------------------------------

## 50. Minimum Application Boundary

The minimum implementation should be:

``` text
Razorpay
   ↓
POST /webhooks/razorpay
   ↓
raw body
   ↓
signature verification
   ↓
event validation
   ↓
payment.failed extraction
   ↓
validation result
```

Do not expand the application architecture unnecessarily.

------------------------------------------------------------------------

## 51. Suggested Repository Structure

A reasonable Phase 01 implementation may look like:

``` text
src/
└── apro/
    ├── __init__.py
    ├── config.py
    ├── main.py
    └── webhooks/
        ├── __init__.py
        ├── razorpay.py
        └── verification.py

tests/
├── test_health.py
└── webhooks/
    ├── test_razorpay_signature.py
    ├── test_razorpay_webhook.py
    └── fixtures/
        └── payment_failed.json
```

This is a suggested structure, not a requirement.

Do not create empty abstractions merely to match the diagram.

------------------------------------------------------------------------

## 52. Configuration Requirements

The implementation may require:

``` text
RAZORPAY_WEBHOOK_SECRET
```

and already-approved APRO configuration.

Do not place secrets in source code, tests, fixtures, README files, or
committed `.env` files.

Use the repository's existing environment configuration mechanism.

------------------------------------------------------------------------

## 53. Test Fixture Policy

A static `payment.failed` fixture may be used for deterministic unit
tests.

However:

``` text
fixture
≠
live Razorpay evidence
```

The final report must distinguish:

``` text
synthetic fixture tests
```

from:

``` text
actual Test Mode webhook observation
```

------------------------------------------------------------------------

## 54. Signature Test Matrix

  Case                                 Expected
  ------------------------------------ ------------------------------------
  Valid body + valid signature         Accept
  Valid body + invalid signature       Reject
  Valid body + missing signature       Reject
  Modified body + original signature   Reject
  Empty body + signature               Reject
  Valid signature + malformed JSON     Reject as malformed payload
  Valid event + wrong event type       Do not process as `payment.failed`

------------------------------------------------------------------------

## 55. Event Identity Test Matrix

  -----------------------------------------------------------------------
  Case                                Expected
  ----------------------------------- -----------------------------------
  New event ID                        Accept

  Same event ID repeated              Duplicate detected

  Different event ID, same payment ID Distinct event

  Missing event ID                    Validation failure or explicitly
                                      reported degraded state

  Same body with a different event ID Different delivery identity
  -----------------------------------------------------------------------

Persistent idempotency belongs to Phase 02.

------------------------------------------------------------------------

## 56. Payload Extraction Test Matrix

Required tests:

``` text
test_payment_failed_event_type
test_payment_id_extraction
test_amount_extraction
test_currency_extraction
test_status_extraction
test_method_extraction
test_order_id_extraction_when_present
test_error_code_extraction
test_error_description_extraction
test_error_reason_extraction
test_error_source_extraction
test_error_step_extraction
```

Optional fields must be handled safely.

------------------------------------------------------------------------

## 57. Malformed Payload Tests

Test at minimum:

``` text
missing event
missing payload
missing payment
missing payment.entity
missing payment.id
wrong event type
wrong entity type
invalid JSON
unexpected primitive where object expected
```

The endpoint must fail explicitly rather than silently accepting
malformed input.

------------------------------------------------------------------------

## 58. End-to-End Test

The primary acceptance test is:

``` text
1. Start APRO.
2. Expose the webhook endpoint publicly.
3. Configure Razorpay Test Mode webhook.
4. Enable `payment.failed`.
5. Create a controlled Test Mode payment failure.
6. Observe the webhook at APRO.
7. Capture raw request.
8. Verify signature.
9. Capture event ID.
10. Confirm event == `payment.failed`.
11. Extract payment ID.
12. Extract failure metadata.
13. Return successful webhook response.
14. Repeat the same event and detect duplicate delivery.
```

This is the core Phase 01 proof.

------------------------------------------------------------------------

## 59. Required Failure Scenarios

At least one actual Test Mode payment failure must be validated.

If feasible, validate more than one payment method/failure mode.

Minimum evidence:

``` text
one actual Test Mode payment failure
one actual `payment.failed` webhook
one valid signature verification
one duplicate-event demonstration
one invalid-signature rejection
```

If a specific failure mode cannot be reproduced, report the attempt and
reason.

Do not fake the result.

------------------------------------------------------------------------

## 60. Evidence Requirements

Capture evidence for:

### A. Test Mode

Proof that the transaction was performed in Test Mode.

### B. Failed payment

Proof of the failed payment.

### C. Webhook configuration

Proof that `payment.failed` was enabled.

### D. Webhook receipt

Proof that APRO received the event.

### E. Signature

Proof that the signature was successfully validated.

### F. Event identity

Proof of `x-razorpay-event-id`.

### G. Payload

Redacted payload showing required metadata.

### H. Duplicate handling

Proof that the same event ID was detected as duplicate.

------------------------------------------------------------------------

## 61. Required Redaction

Before placing screenshots or payloads into documentation, redact:

``` text
API keys
API secrets
webhook secrets
authorization headers
unnecessary personal data
unnecessary payment-instrument data
```

Keep only what is technically necessary to prove the Phase 01 result.

------------------------------------------------------------------------

## 62. Test Mode Safety

Explicitly verify:

``` text
Test API key
Test Dashboard
Test webhook configuration
Test payment
```

Do not allow the application to accidentally use Live Mode credentials.

------------------------------------------------------------------------

## 63. Dependency Rules

Phase 01 may use the existing FastAPI stack.

Do not add a Razorpay SDK unless a verified capability genuinely
requires it and the dependency is approved.

Webhook signature verification can be implemented using standard
cryptographic functionality.

Do not add large infrastructure dependencies to validate one webhook.

------------------------------------------------------------------------

## 64. Security Boundary

The webhook endpoint is an externally reachable security boundary.

It must:

1.  authenticate webhook authenticity through signature validation;
2.  use the raw request body;
3.  reject invalid signatures;
4.  avoid secret leakage;
5.  avoid trusting event data before validation;
6.  capture the provider event ID for duplicate detection.

------------------------------------------------------------------------

## 65. Event Ordering Boundary

The implementation must not depend on webhook delivery order.

The validation report must explicitly state that ordering is not
guaranteed and that this affects Phase 02 event persistence/schema
design.

------------------------------------------------------------------------

## 66. Failure Metadata Boundary

Phase 01 observes:

``` text
provider failure metadata
```

Phase 03 interprets:

``` text
APRO failure category
```

Do not merge these layers.

------------------------------------------------------------------------

## 67. MVP Recovery Actions Remain Out of Scope

The overall APRO architecture contains:

``` text
WAIT_AND_RETRY
ALTERNATE_RETRY_STRATEGY
PAYMENT_LINK
CUSTOMER_OUTREACH
ESCALATE
STOP
```

These are not implemented in Phase 01.

Their existence must not cause Phase 01 to build execution logic.

------------------------------------------------------------------------

## 68. No Economic Logic

Do not calculate:

``` text
recovery_probability
expected_recovery_value
revenue_at_risk
expected_loss
incremental_revenue
```

Phase 01 proves that the underlying failure event can be observed.

------------------------------------------------------------------------

## 69. No AI Reasoning

Do not send the webhook payload to an LLM.

Do not ask an LLM to diagnose the failure in Phase 01.

That belongs to later intelligence architecture.

------------------------------------------------------------------------

## 70. No Automatic Recovery Response

Do not automatically:

``` text
retry
refund
capture
create payment link
message customer
escalate
```

based on the webhook.

The endpoint terminates at validated observation.

------------------------------------------------------------------------

## 71. Existing Phase 00 Compatibility

Phase 01 must not break Phase 00.

The existing health endpoint must continue to return:

``` json
{
  "status": "ok",
  "service": "apro"
}
```

Existing configuration and quality gates must remain functional.

------------------------------------------------------------------------

## 72. Existing Quality Gates

The repository currently expects:

``` text
pytest
ruff format --check .
ruff check .
mypy src
```

All must pass after Phase 01 implementation.

Do not weaken test, lint, formatting, or type-checking configuration
merely to make Phase 01 pass.

------------------------------------------------------------------------

## 73. Required Automated Tests

At minimum:

``` text
Health endpoint regression
Signature verification
Invalid signature
Missing signature
Body mutation
Event parsing
payment.failed validation
Payment metadata extraction
Malformed payload
Duplicate event ID
Unsupported event type
```

------------------------------------------------------------------------

## 74. Required Live Test

Automated fixtures alone are insufficient.

Phase 01 is not complete until an actual Razorpay Test Mode webhook is
observed by APRO.

Required evidence:

``` text
Razorpay Test Mode
        ↓
payment failure
        ↓
payment.failed
        ↓
APRO receives webhook
        ↓
signature verified
        ↓
event ID captured
        ↓
failure metadata extracted
```

------------------------------------------------------------------------

## 75. Required Manual Verification

Before declaring Phase 01 complete:

### Scenario 1 --- Valid failure

``` text
Test payment fails
→ payment.failed arrives
→ signature valid
→ payload accepted
```

### Scenario 2 --- Invalid signature

``` text
webhook arrives
→ signature invalid
→ request rejected
```

### Scenario 3 --- Duplicate

``` text
same event ID
→ second delivery detected as duplicate
```

### Scenario 4 --- Payload mutation

``` text
body modified
→ original signature reused
→ validation fails
```

### Scenario 5 --- Control success

``` text
Test payment succeeds
→ no false payment.failed interpretation
```

------------------------------------------------------------------------

## 76. Phase 01 Acceptance Criteria

Phase 01 is complete only when:

### AC-01

Razorpay Test Mode is used.

### AC-02

A supported Test Mode payment failure can be reproduced.

### AC-03

The `payment.failed` webhook is enabled.

### AC-04

APRO exposes a publicly reachable webhook endpoint.

### AC-05

APRO captures the raw request body.

### AC-06

APRO validates `X-Razorpay-Signature`.

### AC-07

Invalid signatures are rejected.

### AC-08

Missing signatures are rejected.

### AC-09

A body mutation invalidates the original signature.

### AC-10

`x-razorpay-event-id` is captured.

### AC-11

Duplicate event IDs can be detected.

### AC-12

`event == "payment.failed"` is validated.

### AC-13

The failed payment ID is extracted.

### AC-14

Amount and currency are extracted.

### AC-15

Payment status is extracted and validated.

### AC-16

Payment method is captured when present.

### AC-17

Order ID is captured when present.

### AC-18

Provider failure metadata is captured.

### AC-19

Malformed payloads are rejected explicitly.

### AC-20

Unsupported events are not incorrectly processed as failures.

### AC-21

No AI/recovery/policy/execution logic is triggered.

### AC-22

No production database is introduced.

### AC-23

No Live Mode transaction is performed.

### AC-24

Existing Phase 00 functionality continues to work.

### AC-25

All automated tests pass.

### AC-26

Ruff passes.

### AC-27

Mypy passes.

### AC-28

Actual Test Mode webhook evidence exists.

### AC-29

The implementation report distinguishes live Test Mode evidence from
fixtures.

### AC-30

Phase 02 receives a documented list of validated event fields and
unresolved schema questions.

------------------------------------------------------------------------

## 77. Phase 01 Exit Artifact

At the end of Phase 01, create:

``` text
PHASE_01_VALIDATION_REPORT.md
```

The report must include:

``` text
Phase:
01 — Razorpay Failure Event & Webhook Validation

Status:
PASS / PARTIAL / BLOCKED

Test Mode:
PASS / FAIL

Failure Simulation:
PASS / FAIL

Webhook Configuration:
PASS / FAIL

Public Endpoint:
PASS / FAIL

payment.failed Receipt:
PASS / FAIL

Signature Verification:
PASS / FAIL

Invalid Signature Rejection:
PASS / FAIL

Duplicate Event Detection:
PASS / FAIL

Event ID Capture:
PASS / FAIL

Payment ID Extraction:
PASS / FAIL

Failure Metadata Extraction:
PASS / FAIL

Malformed Payload Handling:
PASS / FAIL

Control Success Transaction:
PASS / FAIL

Automated Tests:
PASS / FAIL

Pytest:
PASS / FAIL

Ruff Format:
PASS / FAIL

Ruff Check:
PASS / FAIL

Mypy:
PASS / FAIL

Phase 00 Regression:
PASS / FAIL

Live Test Mode Evidence:
PRESENT / MISSING

Validated Payload Fields:
...

Observed Failure Fields:
...

Webhook Headers Observed:
...

Razorpay Behavior Confirmed:
...

Razorpay Behavior Not Yet Confirmed:
...

Temporary Test Doubles:
...

Security Notes:
...

Phase 02 Schema Implications:
...

Open Questions:
...

Architectural Deviations:
...

Known Limitations:
...

Recommended Next Step:
Proceed to Phase 02 only after Architecture Lead review.
```

------------------------------------------------------------------------

## 78. Phase 02 Handoff

Phase 01 must provide Phase 02 with evidence about:

``` text
event envelope
event name
event identity
payment entity structure
payment identifiers
amount representation
currency
status
payment method
order relationship
failure metadata
timestamp representation
webhook headers
duplicate delivery behavior
ordering behavior
```

Phase 02 will use this evidence to define the event schema and database.

Phase 01 must not design the final database schema prematurely.

------------------------------------------------------------------------

## 79. Architectural Stop Conditions

Antigravity must STOP and report if:

1.  `payment.failed` cannot be reproduced in Test Mode.
2.  Razorpay documentation conflicts with observed behavior.
3.  The actual payload structure differs materially from current
    documentation.
4.  Signature verification cannot be validated.
5.  Webhook-secret behavior is unclear.
6.  The endpoint cannot be made publicly reachable.
7.  A required capability is not available in Test Mode.
8.  Implementation appears to require production credentials.
9.  Implementation requires a database.
10. Implementation requires AI.
11. Implementation requires recovery execution.
12. Implementation requires an unverified Razorpay API.
13. An existing Phase 00 contract must change.
14. A new unapproved dependency appears necessary.
15. The architecture cannot distinguish provider observations from APRO
    diagnosis.

Correct response:

``` text
STOP
→ identify the exact conflict
→ provide evidence
→ explain the architectural impact
→ wait for Architecture Lead approval
```

Do not guess.

------------------------------------------------------------------------

## 80. Prohibited Shortcuts

``` text
❌ Fake a Razorpay webhook and call it live evidence
❌ Invent an undocumented Razorpay event
❌ Use an unverified endpoint
❌ Use Live Mode
❌ Hard-code webhook secrets
❌ Verify signatures after parsing/re-serializing the body
❌ Ignore x-razorpay-event-id
❌ Assume webhook ordering
❌ Build the production database
❌ Build the final failure taxonomy
❌ Call an LLM
❌ Select recovery actions
❌ Retry payments
❌ Create Payment Links
❌ Contact customers
❌ Add policy thresholds
❌ Calculate recovery value
❌ Build the dashboard
❌ Claim revenue recovery from webhook receipt
❌ Treat fixture evidence as live evidence
```

------------------------------------------------------------------------

## 81. Implementation Authority

The Architecture Lead owns:

-   product definition,
-   architecture,
-   data model,
-   APIs,
-   AI boundaries,
-   agent behavior,
-   policy,
-   evaluation,
-   milestones,
-   acceptance criteria.

Antigravity owns implementation execution:

-   writing code,
-   creating files,
-   installing approved dependencies,
-   running tests,
-   implementing the approved plan,
-   reporting results.

Antigravity must not independently redefine the product or phase
boundary.

------------------------------------------------------------------------

## 82. Required Implementation Report

After implementation, Antigravity must report:

``` text
PHASE:
01 — Razorpay Failure Event & Webhook Validation

STATUS:
PASS / PARTIAL / BLOCKED

SUMMARY:
...

FILES CREATED:
...

FILES MODIFIED:
...

DEPENDENCIES ADDED:
...

ENDPOINT:
...

WEBHOOK EVENT:
payment.failed

SIGNATURE VERIFICATION:
...

EVENT ID HANDLING:
...

PAYLOAD EXTRACTION:
...

TEST FIXTURES:
...

LIVE TEST MODE RUN:
...

EVIDENCE:
...

PYTEST:
PASS / FAIL

RUFF FORMAT:
PASS / FAIL

RUFF CHECK:
PASS / FAIL

MYPY:
PASS / FAIL

HEALTH CHECK:
PASS / FAIL

INVALID SIGNATURE TEST:
PASS / FAIL

DUPLICATE EVENT TEST:
PASS / FAIL

BODY MUTATION TEST:
PASS / FAIL

CONTROL SUCCESS TEST:
PASS / FAIL

PHASE 00 REGRESSION:
PASS / FAIL

RAZORPAY CAPABILITIES VERIFIED:
...

RAZORPAY CAPABILITIES NOT VERIFIED:
...

SECURITY NOTES:
...

PHASE 02 INPUTS:
...

ARCHITECTURAL DEVIATIONS:
...

KNOWN LIMITATIONS:
...

UNRESOLVED QUESTIONS:
...

RECOMMENDED NEXT STEP:
...
```

------------------------------------------------------------------------

## 83. Final Definition of Done

Phase 01 is DONE when APRO can demonstrate:

``` text
Razorpay Test Mode
        ↓
controlled payment failure
        ↓
payment.failed
        ↓
public APRO webhook endpoint
        ↓
raw request captured
        ↓
signature verified
        ↓
event ID captured
        ↓
duplicate delivery recognized
        ↓
payment entity validated
        ↓
failure metadata extracted
        ↓
evidence recorded
```

And when:

``` text
NO
production database
AI
recovery engine
policy engine
execution engine
dashboard
```

has been prematurely introduced.

------------------------------------------------------------------------

## 84. Architectural Principle

The first responsibility of APRO is not to decide what to do.

It is to establish that the system can reliably observe what actually
happened.

Therefore:

``` text
OBSERVE
   ↓
AUTHENTICATE
   ↓
IDENTIFY
   ↓
VALIDATE
   ↓
EXTRACT
   ↓
PERSIST LATER
   ↓
DIAGNOSE LATER
   ↓
DECIDE LATER
   ↓
EXECUTE LATER
```

Phase 01 owns:

``` text
OBSERVE
AUTHENTICATE
IDENTIFY
VALIDATE
EXTRACT
```

Later phases own the decisions.

------------------------------------------------------------------------

## 85. Final Instruction to Antigravity

Implement **only** the Phase 01 Razorpay failure-event and webhook
validation described in this specification.

Before coding:

1.  Inspect the current APRO repository.
2.  Inspect the existing Phase 00 implementation.
3.  Inspect existing tests and configuration.
4.  Verify the existing FastAPI application boundary.
5.  Verify the current Razorpay Test Mode failure path using official
    documentation.
6.  Verify the current `payment.failed` webhook documentation.
7.  Identify any conflict with this specification.
8.  STOP if an architectural conflict exists.

Then implement the smallest reliable validation slice.

Do not proceed into Phase 02.

Do not create the production database.

Do not create the final failure taxonomy.

Do not build AI.

Do not build recovery logic.

Do not build policy.

Do not build execution.

Do not build the dashboard.

At completion, run all required tests and quality checks and produce:

``` text
PHASE_01_VALIDATION_REPORT.md
```

Then wait for Architecture Lead review.

------------------------------------------------------------------------

## 86. Specification Status

``` text
PHASE:
01 — Razorpay Failure Event & Webhook Validation

STATUS:
READY FOR IMPLEMENTATION

IMPLEMENTATION AGENT:
Antigravity

ARCHITECTURAL AUTHORITY:
Architectural Lead

PRIMARY EVENT:
payment.failed

PRIMARY ENVIRONMENT:
Razorpay Test Mode

NEXT PHASE:
Phase 02 — Event Schema & Database

NEXT GATE:
Phase 01 Validation Review
```

------------------------------------------------------------------------

## 87. Official References

The implementation must re-check current official Razorpay documentation
before execution, especially:

-   Payments Webhook Events.
-   Validate and Test Webhooks.
-   Razorpay Payment Gateway Test Mode / test payment flows.
-   Razorpay Webhook FAQ and security guidance.

The implementation report must record the documentation checked and the
date of verification.

------------------------------------------------------------------------

# END OF SPECIFICATION
