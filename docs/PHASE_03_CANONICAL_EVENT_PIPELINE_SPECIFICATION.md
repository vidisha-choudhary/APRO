\
# APRO — Phase 3 Canonical Event Pipeline Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Phase:** 3 — Canonical Event Pipeline  
**Architecture Leads:** User + GPT  
**Software Engineering / Coding Lead:** Antigravity  
**Status:** Architecture Specification — Draft for Architecture Review  
**Version:** 1.0  
**Prepared:** 28 August 2026

---

# 1. Purpose

Phase 3 turns APRO's already-validated Razorpay webhook boundary and already-built persistence/domain layers into one coherent, provider-to-domain event pipeline.

The phase establishes the deterministic path:

```text
Razorpay Webhook
      ↓
Webhook Gateway
      ↓
Verification
      ↓
Duplicate / Idempotency Check
      ↓
Razorpay Adapter
      ↓
Canonical PaymentEvent
      ↓
Payment State Application
      ↓
PostgreSQL Persistence
```

The objective is not to add recovery intelligence.

The objective is to ensure that a trusted external payment event becomes a trustworthy internal event and, where appropriate, a correct current payment state.

Phase 3 therefore establishes the **event boundary on which all later APRO intelligence depends**.

The phase must leave downstream components independent of Razorpay's provider-specific nested webhook structure.

---

# 2. Authority and Governance

## 2.1 Authority hierarchy

This specification operates under the existing APRO authority hierarchy:

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/PRODUCT_SPECIFICATION.md`
3. `docs/TECHNICAL_ARCHITECTURE.md`
4. `docs/DOMAIN_AND_DATA_MODEL.md`
5. `docs/AI_ML_SPECIFICATION.md`
6. `docs/POLICY_AND_SAFETY_SPECIFICATION.md`
7. `docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md`
8. `docs/IMPLEMENTATION_MASTER_PLAN.md`
9. This Phase 3 specification

A lower-level implementation decision must not contradict a higher-level document.

If an implementation conflict is discovered that cannot be resolved inside this specification, Antigravity must:

```text
STOP
→ identify the exact conflict
→ provide evidence
→ report to Architecture Leads
→ wait for a decision
```

Antigravity must not independently redesign APRO.

## 2.2 Roadmap authority

The authoritative implementation roadmap is the **19-phase master plan**.

The repository contains older documents that describe a compressed 12-phase sequence and use different phase numbering. Those documents are historical/contextual and do not redefine the current phase structure.

Under the authoritative 19-phase roadmap:

```text
Phase 1  = Core Domain & State Machines
Phase 2  = Persistence & Database
Phase 3  = Canonical Event Pipeline
Phase 4  = Recovery Case Orchestration
Phase 5  = Simulation Engine
Phase 6  = Dataset & Evaluation Foundation
Phase 7  = Diagnosis Intelligence
Phase 8  = Recovery Prediction Intelligence
Phase 9  = Economic Decision Engine
Phase 10 = Policy & Safety Engine
Phase 11 = Execution Framework
Phase 12 = Razorpay Test Mode Integration
Phase 13 = Outcome & Adaptive Recovery Loop
Phase 14 = Audit & Observability
Phase 15 = Full Benchmark & Evaluation
Phase 16 = Dashboard
Phase 17 = Adversarial Testing & Hardening
Phase 18 = Demo, Deployment & Submission Package
```

This specification follows that sequence.

---

# 3. Locked Starting Point

The following work is formally closed and must be treated as authoritative:

```text
Phase 0
Engineering Foundation
CLOSED

Razorpay Webhook Validation Milestone
CLOSED

Phase 1
Core Domain & State Machines
CLOSED

Phase 2
Persistence & Database
CLOSED
```

## 3.1 Existing Phase 1 capabilities

The existing webhook layer already provides:

- `POST /webhooks/razorpay`
- raw request-body capture
- HMAC-SHA256 signature verification
- `X-Razorpay-Signature` handling
- `X-Razorpay-Event-Id` capture
- payload envelope validation
- `payment.failed` extraction
- provider failure metadata extraction
- temporary validation-level duplicate detection
- malformed payload rejection
- unsupported-event handling
- automated webhook tests
- live Razorpay Test Mode validation evidence

The Phase 1 implementation must be reused rather than replaced without architectural reason.

## 3.2 Existing Phase 2 capabilities

Phase 2 provides:

- PostgreSQL persistence
- SQLAlchemy 2.x asynchronous infrastructure
- persistence models
- repository boundaries
- Unit of Work / transaction management
- durable raw event storage
- durable canonical `PaymentEvent` storage
- database-backed provider-event uniqueness
- durable execution idempotency
- migration management with Alembic
- persistence integration tests
- PostgreSQL concurrency protections

The canonical pipeline must use these capabilities rather than creating a parallel persistence layer.

## 3.3 Current domain authority

The Phase 1 domain model remains authoritative.

Relevant domain entities include:

```text
Customer
Payment
PaymentEvent
RecoveryCase
Diagnosis
RecoveryAction
ActionEvaluation
Decision
PolicyDecision
Execution
Outcome
AuditEvent
```

The Phase 3 pipeline may create and persist `PaymentEvent` and update `Payment`.

It must NOT create `RecoveryCase`, `Diagnosis`, `Decision`, `RecoveryAction`, or execution workflows.

---

# 4. Phase 3 Objective

Phase 3 must establish a reliable, deterministic, persistent event-processing path that converts verified Razorpay payment webhooks into provider-independent APRO `PaymentEvent` records and applies valid payment state transitions.

The phase answers:

> Can APRO reliably take a trusted Razorpay payment webhook, prevent duplicate processing, normalize it into a canonical event, and apply the correct payment state without allowing provider-specific payload structure to leak downstream?

The desired result is:

```text
trusted provider evidence
        ↓
canonical APRO event
        ↓
correct current payment state
        ↓
durable persistence
```

---

# 5. Why This Phase Exists

The external provider speaks in provider-specific terms.

Razorpay webhook payloads contain:

- provider event IDs,
- provider payment IDs,
- provider event names,
- nested provider payload objects,
- provider failure metadata,
- provider timestamps.

Downstream APRO components must not each learn how to parse these structures independently.

The canonical event boundary ensures:

```text
Razorpay-specific structure
        ↓
ONE adapter / normalization boundary
        ↓
APRO canonical event
        ↓
all downstream logic
```

This prevents:

- duplicated parsing logic,
- provider-specific assumptions leaking into diagnosis,
- inconsistent state handling,
- divergent test fixtures,
- and provider coupling throughout the system.

The technical architecture explicitly requires the rest of APRO to operate primarily on the canonical event model rather than directly on Razorpay-specific nested payloads.

---

# 6. Scope

## 6.1 In scope

Phase 3 includes:

1. Integration of the existing Razorpay webhook gateway with the application event pipeline.
2. Preservation of the existing raw-body signature-verification boundary.
3. Durable provider-event duplicate detection using Phase 2 persistence.
4. Razorpay adapter / normalizer.
5. Canonical `PaymentEvent` creation.
6. Provider payment identity resolution to APRO internal payment identity.
7. Payment creation/update required to establish a current APRO payment record where the approved identity strategy permits it.
8. Application of canonical payment state transitions through the existing Phase 1 state engine.
9. Persistence of raw event evidence, canonical event, and applicable current-state mutation.
10. Deterministic handling of stale/out-of-order events.
11. Deterministic handling of unsupported event types.
12. Deterministic handling of malformed or semantically invalid payloads.
13. Transactional event processing.
14. Test coverage for the complete pipeline.
15. Regression coverage for existing webhook verification/security behavior.

## 6.2 Out of scope

Phase 3 must NOT implement:

- RecoveryCase orchestration
- diagnosis inference
- final failure taxonomy beyond canonical provider-event representation
- ML models
- LLMs
- Gemini
- recovery probability prediction
- Expected Recovery Value
- action ranking
- policy engine
- safety engine runtime
- retry scheduling
- Payment Link creation
- customer outreach
- execution framework
- Razorpay outbound recovery APIs
- simulation engine
- benchmark evaluation
- dashboard
- human approval workflow
- autonomous financial recovery
- revenue attribution
- live-money transactions

If any of these appears necessary, STOP and report the dependency.

---

# 7. Core Architectural Principle

## 7.1 Canonical event boundary

The required boundary is:

```text
Razorpay Webhook
      ↓
Webhook Gateway
      ↓
Verification
      ↓
Deduplication
      ↓
Razorpay Adapter
      ↓
Canonical PaymentEvent
      ↓
Payment State Engine
```

Downstream logic must consume:

```text
PaymentEvent
```

rather than raw Razorpay payloads.

## 7.2 Deterministic processing

No AI may determine:

- whether the webhook is authentic;
- whether the event is a duplicate;
- what the provider event type is;
- the provider payment identity;
- the canonical payment status;
- whether a state transition is structurally legal.

These are deterministic responsibilities.

The project constitution explicitly prefers deterministic engineering for webhook verification, idempotency, and state transitions.

---

# 8. Supported Event Set

## 8.1 Phase 3 supported payment events

Phase 3 must support these payment webhook events:

```text
payment.failed
payment.authorized
payment.captured
```

Rationale:

- `payment.failed` is APRO's primary recovery trigger.
- `payment.authorized` represents an important payment-state change.
- `payment.captured` is the critical terminal-success signal that can make recovery ineligible.

Razorpay currently documents these payment webhook events and provides payment snapshots in their payloads.

## 8.2 Unsupported events

Other webhook events, including unrelated order or downtime events, are not Phase 3 canonical payment events unless explicitly added later by Architecture Leads.

For an authenticated, structurally valid but unsupported event:

```text
verify
↓
record raw evidence
↓
do not create canonical PaymentEvent
↓
do not mutate Payment state
↓
return HTTP 2xx
```

Reason:

Razorpay treats non-2xx responses as delivery failures and retries them. An authenticated event that APRO intentionally does not support should not be turned into a repeated delivery loop.

The response should identify the event as unsupported/ignored in the application response body.

---

# 9. Security and Trust Boundary

The Phase 3 pipeline inherits the existing Phase 1 security sequence.

Required order:

```text
1. Receive HTTP request.
2. Capture exact raw request body.
3. Capture signature header.
4. Verify HMAC-SHA256 signature.
5. Reject invalid signature.
6. Capture provider event ID.
7. Parse JSON.
8. Validate top-level event envelope.
9. Determine supported event type.
10. Validate target payload structure.
11. Only then create trusted canonical/persistence effects.
```

No business state may be changed based on unverified event content.

The webhook secret must never be logged or persisted as application evidence.

No authorization token, secret, or unnecessary payment-instrument data may be written to logs.

---

# 10. Provider Event Identity

Razorpay supplies the event identity in:

```text
X-Razorpay-Event-Id
```

HTTP header names are case-insensitive, but the application must normalize internally to one canonical representation.

The provider event ID is the identity used for duplicate detection.

Do NOT synthesize event identity from:

```text
payment ID + timestamp
```

when the provider event ID is available.

## 10.1 Duplicate policy

For a first-seen authenticated event:

```text
new provider event
→ normal processing
```

For a repeated authenticated provider event:

```text
same (provider, provider_event_id)
→ duplicate
→ no second canonical event
→ no second state mutation
→ preserve original raw event
→ HTTP 2xx
```

The database-backed uniqueness constraint from Phase 2 is the final consistency boundary.

The old Phase 1 in-memory duplicate set is no longer the production processing mechanism.

It may remain only if needed for historical tests, but the integrated Phase 3 path must not depend on it.

---

# 11. Provider Payment Identity Resolution

## 11.1 Problem

Razorpay identifies the payment with a provider payment ID such as:

```text
pay_...
```

APRO's internal domain `Payment` uses its own internal `payment_id`.

The current Phase 2 domain contract intentionally keeps the domain-facing identifier independent of the provider.

Therefore the pipeline must resolve:

```text
(provider, provider_payment_id)
        ↓
APRO internal payment_id
```

without exposing provider-specific identity concerns throughout the domain.

## 11.2 Required persistence-level identity mapping

If the closed Phase 2 persistence schema does not already contain a usable provider-payment identity field, Phase 3 must add the minimum persistence-level capability required to resolve it.

Preferred minimal design:

```text
payments.provider_payment_id
```

with:

```text
UNIQUE(provider, provider_payment_id)
```

or an equivalent narrowly-scoped persistence identity mapping that provides the same guarantees.

The exact ORM/schema mechanics may be chosen by Antigravity, but the architectural requirements are fixed:

- provider identity remains separate from APRO internal identity;
- duplicate provider payment identity is prevented;
- lookup by `(provider, provider_payment_id)` is supported;
- the Phase 1 Pydantic domain contract is not contaminated with SQLAlchemy/provider-specific types;
- no generic identity framework is introduced.

If adding the persistence field would require a material change to an already-approved Phase 2 invariant, STOP and report the conflict.

## 11.3 Unknown provider payment

If a trusted, well-formed event references a provider payment ID that APRO cannot resolve:

```text
raw evidence
    ↓
persist raw event
    ↓
do not fabricate internal Payment
    ↓
do not mutate unknown state
    ↓
return deterministic HTTP 2xx unresolved classification
```

Do not create a fake internal payment ID.

Do not associate the event with a different payment.

Do not guess based on amount, timestamp, customer, or other weak correlation.

---

# 12. Canonical PaymentEvent Contract

The canonical event must be provider-independent while preserving the provider facts required by downstream processing.

Canonical fields:

```text
event_id
event_type
provider
payment_id
order_id
amount
currency
method
status
failure_code
failure_source
failure_step
failure_reason
failure_description
event_timestamp
received_at
raw_payload_reference
```

## 12.1 Field mapping

### `event_id`

APRO's canonical internal event identity.

This is separate from the provider event ID.

The implementation must preserve a stable relationship to the raw provider-event record.

The existing persistence mapping may use the raw-event internal identifier as the reference where that is compatible with the approved domain model.

Do not use a synthetic hash of mutable payload content when a stable internal event ID is available.

### `event_type`

Map supported Razorpay names exactly into canonical event types:

```text
payment.failed
payment.authorized
payment.captured
```

Do not rename them into ambiguous generic labels such as `FAILED_EVENT`.

### `provider`

For Razorpay:

```text
razorpay
```

### `payment_id`

This is the APRO internal payment ID after provider identity resolution.

It is NOT the Razorpay `pay_...` identifier.

### `order_id`

Copy the provider order ID when present.

Preserve `null`/absence.

Do not invent order relationships.

### `amount`

Copy the provider amount exactly as observed.

The Phase 2 persistence representation remains integer minor units.

Do not convert to float.

Do not calculate recovery value.

### `currency`

Copy the provider currency.

Do not assume INR solely because the project is India-focused.

### `method`

Copy the observed payment method when present.

Treat provider method values as provider facts.

Do not turn them into APRO failure categories.

### `status`

Map provider payment status to the APRO domain enum:

```text
authorized → AUTHORIZED
captured   → CAPTURED
failed     → FAILED
```

No other provider value may be silently coerced.

Unsupported status values require explicit handling.

### Failure fields

For `payment.failed`, map:

```text
error_code
error_source
error_step
error_reason
error_description
```

into:

```text
failure_code
failure_source
failure_step
failure_reason
failure_description
```

Preserve `null` when absent.

Do not merge them.

Do not infer a final APRO diagnosis.

### `event_timestamp`

Use the event-level `created_at` from the Razorpay webhook envelope as the canonical event occurrence timestamp.

This represents when the provider event was created.

### `received_at`

Use APRO's actual request-receipt timestamp.

This is distinct from provider event occurrence time.

### `raw_payload_reference`

Reference the persisted raw event record.

The canonical event must not duplicate the entire raw webhook payload.

---

# 13. Event Snapshot Semantics

Razorpay documents webhook payloads as snapshots of the payment entity at the time of the event.

This means:

```text
payment.authorized snapshot
payment.captured snapshot
payment.failed snapshot
```

must be treated as observations tied to their event timestamps.

APRO must not rewrite historical `PaymentEvent` records to make them look like the latest payment state.

Historical event facts remain historical facts.

Current payment state is maintained separately.

---

# 14. State Application Rules

## 14.1 Source of truth

Payment state transitions must be performed through the existing Phase 1 state-transition logic.

Do NOT directly assign:

```text
payment.status = ...
```

inside the pipeline and treat that as the state machine.

The pipeline must:

```text
canonical event
     ↓
determine target observed state
     ↓
invoke existing transition logic
     ↓
persist legal resulting state
```

## 14.2 Event → observed state mapping

```text
payment.failed
    → FAILED

payment.authorized
    → AUTHORIZED

payment.captured
    → CAPTURED
```

## 14.3 Important captured-payment invariant

If the current payment is already `CAPTURED`, a later stale `payment.failed` event must NOT regress the current payment state.

The canonical event can remain as historical evidence, but the current payment state must remain:

```text
CAPTURED
```

The pipeline must not reopen recovery eligibility.

## 14.4 Out-of-order events

Razorpay does not guarantee webhook delivery order.

Therefore APRO must distinguish:

```text
historical event observation
```

from:

```text
current payment state
```

For a trusted canonical event that is stale relative to the current state:

```text
persist event history
↓
do not regress current state
↓
return HTTP 2xx with deterministic stale/no-state-change classification
```

Do not reject a valid stale event merely because the event arrived late.

Do not rewrite timestamps to fake ordering.

## 14.5 Same-state event

If the canonical target state equals the current state:

```text
persist event
↓
no current-state mutation required
↓
return successful 2xx
```

This is not a duplicate unless the provider event ID itself is already processed.

## 14.6 Invalid state transition

If the canonical event is trusted and structurally valid but the existing state engine rejects its transition:

```text
persist the historical canonical event if safe to do so
↓
do not mutate current payment state
↓
return HTTP 2xx
↓
record deterministic stale/conflicting-state classification
```

The event is provider evidence; it must not be allowed to corrupt current state.

A truly malformed or unauthenticated payload is different and is rejected.

---

# 15. Raw Event Persistence

The raw provider event is evidence.

For a successfully authenticated, parseable webhook:

```text
raw request
    ↓
raw_events
```

The stored raw event must retain at minimum the already-approved Phase 2 fields:

```text
raw_event_id
provider
provider_event_id
event_type
received_at
raw_payload
verification_status
```

`raw_payload` remains PostgreSQL JSONB.

Do not store:

- webhook secrets;
- authorization tokens;
- credentials.

Do not unnecessarily persist duplicate raw payload copies.

For a duplicate delivery, the first raw event record remains authoritative.

---

# 16. Transaction Boundary

The complete first-seen event processing path should be operation-scoped and short.

Conceptually:

```text
BEGIN
  ↓
claim / identify provider event
  ↓
persist raw event
  ↓
resolve provider payment identity
  ↓
construct canonical PaymentEvent
  ↓
persist canonical PaymentEvent
  ↓
apply valid current-state mutation if required
  ↓
COMMIT
```

For a duplicate:

```text
BEGIN
  ↓
detect already-processed event
  ↓
ROLLBACK / no-op transaction cleanup
  ↓
HTTP 2xx duplicate
```

The transaction must not include:

- AI inference;
- external API calls;
- human approval;
- sleep;
- retry delays;
- asynchronous waiting.

There are no outbound calls in Phase 3.

---

# 17. Failure Atomicity

If an unexpected internal failure occurs after trusted event processing has begun:

```text
ROLLBACK
```

must prevent a partial first-seen event from producing an inconsistent combination such as:

```text
raw event persisted
canonical event missing
state mutated
```

or:

```text
canonical event persisted
state mutation partially applied
```

The transaction must protect the logical processing unit.

The exact transaction implementation must use the already-approved Phase 2 Unit of Work/session architecture.

---

# 18. Processing Flow

The normative pipeline is:

```text
HTTP request
   │
   ▼
Webhook Gateway
   │
   ├── read raw bytes
   │
   ▼
Signature Verification
   │
   ├── invalid → HTTP 4xx
   │
   ▼
Event Identity Capture
   │
   ├── missing → HTTP 4xx
   │
   ▼
JSON Parse
   │
   ├── malformed → HTTP 4xx
   │
   ▼
Envelope Validation
   │
   ├── malformed → HTTP 4xx
   │
   ▼
Provider Event Type
   │
   ├── unsupported → persist raw evidence, HTTP 2xx ignored
   │
   ▼
Provider Payment Payload Validation
   │
   ├── malformed target event → HTTP 4xx
   │
   ▼
Database Duplicate Check
   │
   ├── duplicate → HTTP 2xx duplicate
   │
   ▼
Provider Payment Identity Resolution
   │
   ├── unresolved → raw evidence + HTTP 2xx unresolved
   │
   ▼
Razorpay Adapter
   │
   ▼
Canonical PaymentEvent
   │
   ▼
Persist canonical event
   │
   ▼
Apply Phase 1 state transition if valid
   │
   ├── stale/conflicting → retain event, no regression
   │
   ▼
COMMIT
   │
   ▼
HTTP 2xx
```

---

# 19. HTTP Response Policy

Razorpay currently treats non-2xx responses as delivery failures and retries webhook delivery.

Therefore Phase 3 must use this policy:

| Condition | Response |
|---|---|
| Missing/invalid signature | HTTP 4xx |
| Missing event ID | HTTP 4xx |
| Malformed JSON | HTTP 4xx |
| Invalid required target structure | HTTP 4xx |
| Authenticated supported event, processed successfully | HTTP 2xx |
| Authenticated duplicate | HTTP 2xx |
| Authenticated stale/out-of-order event | HTTP 2xx |
| Authenticated unsupported event | HTTP 2xx |
| Authenticated event with unresolved provider payment identity | HTTP 2xx |
| Unexpected internal processing failure | HTTP 5xx |

The final exact status codes for 4xx/5xx may follow existing application conventions.

The important semantic requirement is:

```text
invalid/untrusted input
→ reject

trusted event already safely consumed / intentionally unsupported
→ acknowledge

unexpected server failure
→ do not falsely acknowledge success
```

---

# 20. Response Contract

Preserve the existing simple webhook response style where practical.

The implementation should provide deterministic machine-readable fields equivalent to:

### New event

```json
{
  "status": "accepted",
  "event_id": "<provider_event_id>",
  "classification": "NEW"
}
```

### Duplicate event

```json
{
  "status": "duplicate",
  "event_id": "<provider_event_id>",
  "classification": "DUPLICATE"
}
```

### Unsupported event

```json
{
  "status": "ignored",
  "event_id": "<provider_event_id>",
  "classification": "UNSUPPORTED"
}
```

### Stale event

```json
{
  "status": "accepted",
  "event_id": "<provider_event_id>",
  "classification": "STALE"
}
```

### Unresolved payment identity

```json
{
  "status": "accepted",
  "event_id": "<provider_event_id>",
  "classification": "UNRESOLVED_PAYMENT"
}
```

The implementation may add safe fields, but it must not expose secrets or unnecessary sensitive payload data.

---

# 21. Payment Record Handling

Phase 3 must be explicit about when a `Payment` can be created or updated.

## 21.1 Existing payment

If provider identity resolves to an existing APRO payment:

```text
use existing internal payment_id
```

and apply event state according to the rules above.

Do not overwrite historical creation fields merely because a later webhook includes a snapshot.

## 21.2 New payment

If the architecture-approved provider identity mechanism allows creation of a new APRO payment from a trusted webhook, the implementation may create a new `Payment` record using trusted provider facts.

It must:

- generate an APRO internal identity;
- preserve provider payment identity separately;
- preserve integer amount;
- preserve currency;
- preserve provider method;
- preserve provider order ID when available;
- derive current status from the canonical event;
- avoid fabricating customer identity.

If customer identity cannot be safely established from the approved data, the pipeline must not invent one.

Antigravity must stop and report if the existing domain/persistence model makes safe new-payment creation impossible without an architectural decision.

---

# 22. Failure Metadata Boundary

Phase 3 normalizes provider failure facts.

Phase 3 does NOT decide:

```text
TRANSIENT
BANK_SIDE
CUSTOMER_SIDE
AUTHENTICATION
PAYMENT_METHOD
GATEWAY
TIMEOUT
UNKNOWN
```

Those later categories belong to the diagnosis/intelligence roadmap.

Therefore:

```text
error_code
error_source
error_step
error_reason
error_description
```

remain provider-derived evidence stored on `PaymentEvent`.

No probabilistic diagnosis occurs here.

---

# 23. Event Ordering Strategy

The system must never use webhook arrival order as a proxy for event occurrence order.

Use:

```text
event_timestamp
```

for historical ordering.

Use:

```text
Payment.status
```

for current known state.

These are separate concepts.

Example:

```text
t1 payment.failed
t2 payment.captured
```

If delivery arrives:

```text
captured first
failed second
```

the system should result in:

```text
history:
  captured event
  failed event

current Payment:
  CAPTURED
```

The historical `payment.failed` observation must remain accessible while it must not regress the current state.

---

# 24. Concurrency and Duplicate Processing

Phase 3 relies on the Phase 2 database consistency boundary.

The same provider event may arrive concurrently.

The design must guarantee:

```text
two workers
same (provider, provider_event_id)
        ↓
one logical provider event
one canonical PaymentEvent
at most one first-seen state mutation
```

The application must not rely solely on:

```text
if event_id in memory_set:
```

because that cannot protect multiple processes/workers.

Database uniqueness is authoritative.

The pipeline should handle expected uniqueness conflicts deterministically rather than exposing them as arbitrary server errors.

---

# 25. Canonical Event Persistence

A first-seen supported event should result in:

```text
1 raw_events record
1 canonical PaymentEvent record
0 or 1 current Payment state mutation
```

A duplicate provider event should result in:

```text
1 existing raw_events record
1 existing canonical PaymentEvent
0 additional state mutation
```

An unsupported but authenticated event should result in:

```text
1 raw event
0 canonical PaymentEvent
0 payment state mutation
```

An unresolved payment identity should result in:

```text
1 raw event
0 canonical PaymentEvent
0 payment state mutation
```

unless the implementation can safely construct a new Payment under the approved identity rules.

A malformed or unauthenticated event must not create trusted canonical state.

---

# 26. Idempotency Semantics

There are three distinct concepts:

```text
provider-event idempotency
canonical event identity
payment current-state idempotency
```

They must not be conflated.

## Provider-event idempotency

Determines whether this exact provider event has already been consumed.

Key:

```text
(provider, provider_event_id)
```

## Canonical event identity

Represents the durable APRO event record.

It must remain stable once created.

## Current-state idempotency

Determines whether applying the canonical observation would actually change current payment state.

For example:

```text
current = CAPTURED
incoming = FAILED
```

The event is new, but the state mutation is not permitted.

---

# 27. Malformed Input Policy

Reject malformed structures explicitly.

At minimum reject:

- malformed JSON;
- missing top-level event envelope;
- wrong top-level `entity`;
- missing/invalid event name where required;
- supported event missing `payload.payment.entity`;
- supported event missing provider payment ID;
- unsupported/non-mappable payment status for the selected event;
- structurally contradictory target event where the event name and payment status cannot be reconciled safely.

Do not “best effort” malformed financial data.

Do not silently supply defaults for:

```text
payment_id
amount
currency
status
method
```

unless the approved canonical contract explicitly allows the field to be absent.

---

# 28. Unsupported Event Policy

An authenticated unsupported event is not equivalent to malformed input.

Example:

```text
event = payment.downtime.updated
```

If the event is authenticated and parseable:

```text
raw evidence preserved
no canonical PaymentEvent
no state mutation
HTTP 2xx
```

This distinction prevents:

```text malformed
```

from being confused with:

```text intentionally not supported by Phase 3
```

---

# 29. Security Logging Requirements

Safe logs may include:

```text
provider
provider_event_id
event_type
internal payment_id where appropriate
classification
validation result
state transition result
received_at
```

Do NOT log:

- webhook secret;
- API keys;
- authorization headers;
- raw authorization credentials;
- full payment-instrument details;
- unnecessary personal data;
- complete raw payloads unless explicitly required for a redacted debug artifact.

Raw payload remains in the controlled persistence layer rather than being dumped into application logs.

---

# 30. Test Architecture

Phase 3 must be tested at multiple boundaries.

## 30.1 Existing security regression tests

All Phase 1 webhook tests must continue to pass or be deliberately updated only where Phase 3 changes previously unsupported behavior.

Required coverage:

- valid signature
- invalid signature
- missing signature
- body mutation
- missing event ID
- malformed JSON
- invalid envelope
- missing payment entity
- missing required payment fields

## 30.2 Adapter unit tests

Test each supported event mapping:

```text
payment.failed
payment.authorized
payment.captured
```

Verify all canonical fields.

Verify:

- provider payment ID handling;
- null/optional fields;
- timestamp mapping;
- failure metadata mapping;
- amount/currency preservation;
- status normalization.

## 30.3 Pipeline integration tests

Using real PostgreSQL persistence:

1. new `payment.failed`
2. new `payment.authorized`
3. new `payment.captured`
4. duplicate provider event
5. duplicate concurrent provider event
6. out-of-order captured → failed
7. failed → captured
8. same-state event
9. unresolved provider payment identity
10. unsupported authenticated event
11. malformed supported event
12. invalid signature
13. transactional rollback on unexpected internal failure

## 30.4 State safety tests

At minimum:

```text
FAILED → PENDING/other approved state
FAILED → CAPTURED
CAPTURED → FAILED must not happen
```

Use the existing Phase 1 state transition rules.

Do not duplicate a second state machine inside the pipeline tests.

## 30.5 Atomicity tests

Prove:

```text
raw event + canonical event + allowed state update
```

are committed as one logical operation for a first-seen event.

Prove unexpected failure causes rollback.

---

# 31. End-to-End Local Test

Phase 3 must demonstrate a full local deterministic path:

```text
synthetic HTTP webhook
      ↓
existing FastAPI gateway
      ↓
signature verification
      ↓
provider event identity
      ↓
raw event persistence
      ↓
Razorpay adapter
      ↓
canonical PaymentEvent
      ↓
database-backed idempotency
      ↓
Payment state transition
      ↓
PostgreSQL persisted state
```

This test does not need a real Razorpay credential.

Use controlled signed fixtures based on the observed Phase 1 payload contract.

---

# 32. Live Razorpay Test Mode Boundary

Real Razorpay credentials are **not required to close Phase 3**.

The previously validated live Razorpay Test Mode evidence is the external provider contract baseline.

Phase 3 implementation may use redacted observed payload fixtures for deterministic tests.

Any new claim about current Razorpay behavior must be verified against current official Razorpay documentation before being treated as authoritative.

Live end-to-end revalidation is optional for this phase unless Architecture Leads explicitly request it.

---

# 33. No Direct Provider Parsing Downstream

After normalization, downstream components must receive only the canonical representation.

Do not write:

```text
if payload["payload"]["payment"]["entity"]["error_code"] == ...
```

inside future business/application components.

Only the Razorpay adapter/normalizer may know provider-specific nested payload paths.

This boundary is mandatory.

---

# 34. No Recovery-Case Creation

Even when the canonical event indicates:

```text
payment.failed
```

Phase 3 must NOT create a `RecoveryCase`.

That belongs to Phase 4.

The Phase 3 result is:

```text
PaymentEvent persisted
Payment state = FAILED where legal
```

and then stop.

---

# 35. No AI / Diagnosis

The event:

```text
payment.failed
```

does not itself mean:

```text
TRANSIENT
BANK_SIDE
CUSTOMER_SIDE
```

The pipeline may preserve provider facts such as:

```text
error_code
error_source
error_step
error_reason
error_description
```

but must not perform diagnosis.

No LLM call is allowed in the Phase 3 event path.

---

# 36. No Recovery Execution

The pipeline must never:

```text
retry
capture
create Payment Link
send outreach
escalate
```

because of the event.

The pipeline's responsibility ends after:

```text
canonical event
+
current payment state
+
durable persistence
```

---

# 37. Acceptance Criteria

Phase 3 is complete only when all of the following are true.

## AC-01 — Existing webhook security preserved

Raw-body signature verification occurs before trust.

## AC-02 — Provider identity captured

`X-Razorpay-Event-Id` is required and preserved.

## AC-03 — Database-backed duplicate handling

Repeated provider events do not create duplicate logical events.

## AC-04 — Supported event normalization

`payment.failed`, `payment.authorized`, and `payment.captured` are converted correctly to canonical `PaymentEvent`.

## AC-05 — Provider-independent downstream boundary

Downstream application logic consumes canonical event objects rather than Razorpay payload structures.

## AC-06 — Required field preservation

Amount, currency, status, method, order ID, timestamps, and provider failure metadata are preserved correctly.

## AC-07 — Provider payment identity resolution

Razorpay payment IDs are safely mapped to APRO internal payment identities without contaminating the domain model.

## AC-08 — Payment state correctness

Supported canonical events apply legal Phase 1 payment state transitions.

## AC-09 — Captured-state protection

No stale `payment.failed` event may regress a `CAPTURED` payment.

## AC-10 — Out-of-order tolerance

Webhook delivery order is not treated as event occurrence order.

## AC-11 — Historical event preservation

Canonical `PaymentEvent` history remains accessible even when it does not mutate current state.

## AC-12 — Unsupported event handling

Authenticated unsupported events are safely acknowledged, retained as raw evidence, and excluded from canonical payment-state processing.

## AC-13 — Malformed input rejection

Malformed/unsafe payloads are rejected explicitly.

## AC-14 — Unknown payment safety

The system does not invent internal payment identities when provider identity cannot be resolved.

## AC-15 — Transactional atomicity

First-seen event persistence and applicable state mutation are protected by one operation-scoped transaction.

## AC-16 — Unexpected failure rollback

Unexpected internal failure does not leave partial trusted processing state.

## AC-17 — No recovery workflow leakage

No RecoveryCase, recovery decision, policy decision, or execution is created by Phase 3.

## AC-18 — No AI leakage

No AI/LLM/ML inference occurs in the Phase 3 event path.

## AC-19 — PostgreSQL integration

Critical pipeline behavior is verified against real PostgreSQL persistence.

## AC-20 — Regression safety

All relevant prior Phase 0, Phase 1, and Phase 2 tests remain passing, except tests intentionally updated to reflect the newly supported `payment.authorized` / `payment.captured` behavior.

## AC-21 — Quality gates

The repository quality gates pass:

```text
pytest
ruff check .
ruff format --check .
mypy src
```

---

# 38. Required Test Matrix

The implementation test suite must explicitly cover:

| Scenario | Authentication | Canonical Event | Raw Event | State Change | Expected HTTP |
|---|---|---|---|---|---|
| Valid `payment.failed` | valid | yes | yes | `→ FAILED` when legal | 2xx |
| Valid `payment.authorized` | valid | yes | yes | `→ AUTHORIZED` when legal | 2xx |
| Valid `payment.captured` | valid | yes | yes | `→ CAPTURED` when legal | 2xx |
| Duplicate supported event | valid | no new record | existing | no new mutation | 2xx |
| Stale `failed` after `captured` | valid | yes | yes | none | 2xx |
| Failed then captured | valid | yes | yes | final `CAPTURED` | 2xx |
| Same-state event | valid | yes | yes | none | 2xx |
| Unsupported event | valid | no | yes | none | 2xx |
| Unknown provider payment | valid | no | yes | none | 2xx |
| Malformed JSON | valid signature if possible | no | no trusted canonical state | none | 4xx |
| Invalid signature | invalid | no | no trusted state | none | 4xx |
| Missing event ID | valid | no | no trusted canonical state | none | 4xx |
| Concurrent duplicate delivery | valid | one logical event | one | one at most | 2xx |
| Unexpected DB failure | valid | rollback | rollback | rollback | 5xx |

---

# 39. Concurrency Acceptance

At minimum, the implementation must demonstrate:

```text
Worker A
   ┐
   ├── same provider event
   │
Worker B
   ┘
```

and:

```text
exactly one first-seen logical event
exactly one canonical PaymentEvent
at most one first-seen state mutation
```

The test must use:

- separate database sessions/connections;
- real PostgreSQL;
- database-enforced uniqueness;
- overlapping execution;
- deterministic final-state verification.

Do not replace the race test with sequential execution.

---

# 40. Observability

Phase 3 should provide enough structured logging to reconstruct a processing decision without requiring raw log dumps.

A useful correlation chain is:

```text
provider_event_id
    ↓
raw_event_id
    ↓
canonical event_id
    ↓
internal payment_id
    ↓
state transition result
```

The more extensive immutable audit subsystem is Phase 14.

Phase 3 should not build the final observability platform.

---

# 41. Performance / Response Boundary

Razorpay webhook delivery is asynchronous and retry-based.

APRO's Phase 3 handler should acknowledge successful processing quickly.

The handler must not perform:

- model inference;
- long-running analysis;
- external API calls;
- customer outreach;
- recovery execution;
- waiting for asynchronous outcomes.

The pipeline is intentionally deterministic and bounded.

---

# 42. Data Integrity Rules

The following must never be violated:

```text
internal APRO IDs ≠ provider IDs
```

```text
provider event identity is preserved
```

```text
historical event ≠ current payment state
```

```text
provider failure metadata ≠ APRO diagnosis
```

```text
event receipt time ≠ event occurrence time
```

```text
duplicate event ≠ new canonical event
```

```text
stale event ≠ permission to regress current state
```

```text
authenticated event ≠ automatically supported event
```

---

# 43. Required Code Organization

Antigravity may choose equivalent module names, but responsibilities should remain clearly separated.

A preferred structure is:

```text
src/apro/
├── webhooks/
│   ├── razorpay.py
│   └── verification.py
│
├── events/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── canonical.py
│   ├── razorpay_adapter.py
│   └── exceptions.py
│
├── domain/
│   └── ...
│
└── persistence/
    └── ...
```

Alternative structures are acceptable if they preserve the same boundaries.

Do not create a generic “event framework” with unused plugin machinery.

Do not create a second persistence abstraction unrelated to Phase 2.

---

# 44. Migration Boundary

If provider payment identity resolution requires a new persistence column or constraint because Phase 2 does not already expose one:

- create the smallest required Alembic migration;
- preserve all existing Phase 2 tables/constraints;
- do not rewrite historical migrations;
- do not redesign the database.

The migration must be reversible where practical.

The schema extension must be documented as a Phase 3 persistence support change.

---

# 45. Phase 3 Definition of Done

Phase 3 is formally complete when:

```text
Phase 3 Specification
        ↓
IMPLEMENTATION
        ↓
Webhook verification integrated
        ↓
Database-backed deduplication integrated
        ↓
Razorpay adapter complete
        ↓
Canonical PaymentEvent complete
        ↓
Provider identity resolution complete
        ↓
Payment state application complete
        ↓
Out-of-order behavior verified
        ↓
Raw event evidence preserved
        ↓
Atomic transaction behavior verified
        ↓
PostgreSQL integration tests passing
        ↓
Phase 0/1/2 regressions passing
        ↓
Ruff passing
        ↓
Mypy passing
        ↓
Architecture review PASS
        ↓
Approved Git commit
        ↓
PHASE 3 CLOSED
```

---

# 46. Architecture Stop Conditions

Antigravity must STOP and report if:

1. A provider payment cannot be safely mapped to an APRO internal payment identity.
2. The existing Phase 2 persistence schema cannot support required identity resolution without a material architectural change.
3. The Phase 1 state machine cannot represent a required event-state relationship safely.
4. A legitimate Razorpay event requires a provider behavior not established by current official documentation.
5. Provider payload structure materially conflicts with the locked canonical contract.
6. A requested event cannot be safely classified as supported/unsupported.
7. Event processing would require AI/ML/LLM inference.
8. Event processing would require recovery orchestration.
9. Event processing would require outbound Razorpay financial execution.
10. A transaction cannot maintain the required atomicity without changing the Phase 2 transaction architecture.
11. A new dependency outside the approved stack becomes necessary.
12. A later-phase component appears necessary to satisfy a Phase 3 requirement.

Correct response:

```text
STOP
→ identify conflict
→ provide evidence
→ explain impact
→ wait for Architecture Leads
```

---

# 47. Implementation Rules for Antigravity

Antigravity must:

- read the complete Phase 3 specification before coding;
- inspect the existing Phase 0–2 implementation before changing it;
- reuse existing verification, repositories, Unit of Work, domain state machines, and database infrastructure;
- keep provider-specific parsing inside the adapter boundary;
- keep canonical processing deterministic;
- add tests for every acceptance criterion;
- run the complete quality gates;
- report deviations honestly;
- report all files changed;
- report any migration added;
- report any architecture conflicts.

Antigravity must NOT:

- redesign the domain;
- create a second event model that competes with `PaymentEvent`;
- create a second database abstraction;
- create RecoveryCase workflows;
- add AI;
- add recovery actions;
- add outbound Razorpay APIs;
- create a dashboard;
- install unnecessary infrastructure;
- modify the specification;
- commit without explicit Architecture Lead approval.

---

# 48. Verification Basis

This specification was prepared against the current repository architecture and the following authoritative materials.

## Internal project sources

```text
docs/PROJECT_CONSTITUTION.md
docs/PRODUCT_SPECIFICATION.md
docs/TECHNICAL_ARCHITECTURE.md
docs/DOMAIN_AND_DATA_MODEL.md
docs/AI_ML_SPECIFICATION.md
docs/POLICY_AND_SAFETY_SPECIFICATION.md
docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md
docs/IMPLEMENTATION_MASTER_PLAN.md
docs/PHASE_02_PERSISTENCE_AND_DATABASE_SPECIFICATION.md
PHASE_01_VALIDATION_REPORT.md
```

## Current official Razorpay documentation verified on 28 August 2026

Payments webhook events:
https://razorpay.com/docs/webhooks/payments/

Webhook validation and testing:
https://razorpay.com/docs/webhooks/validate-test/

Webhook best practices:
https://razorpay.com/docs/webhooks/best-practices/

Webhook FAQs:
https://razorpay.com/docs/webhooks/faqs/

Orders webhook events:
https://razorpay.com/docs/webhooks/orders/

These current official sources establish, among other things:

- payment webhook events include `payment.authorized`, `payment.captured`, and `payment.failed`;
- webhook payloads represent payment state snapshots associated with event occurrence;
- duplicate webhook delivery is possible and `x-razorpay-event-id` is the provider event identity used for duplicate detection;
- webhook delivery is at-least-once;
- webhook order is not guaranteed;
- HMAC signature verification must use the raw webhook body;
- successful consumption should return 2xx;
- non-2xx responses are treated as delivery failure;
- webhook handling is asynchronous and should be designed accordingly.

Phase 3 design decisions above are based on those verified behaviors and on the existing APRO architecture.

---

# 49. Architecture Decision Register

The following decisions are proposed for Architecture Lead approval.

| Decision | Phase 3 Direction |
|---|---|
| Phase authority | 19-phase master plan |
| Canonical event | Existing APRO `PaymentEvent` |
| Supported payment events | `payment.failed`, `payment.authorized`, `payment.captured` |
| Signature boundary | Existing Phase 1 raw-body HMAC verification |
| Provider event identity | `X-Razorpay-Event-Id` |
| Duplicate authority | Phase 2 PostgreSQL uniqueness |
| Raw event storage | Existing Phase 2 `raw_events` |
| Provider adapter | Single Razorpay-specific normalization boundary |
| Canonical timestamp | Provider event `created_at` |
| Receipt timestamp | APRO receipt time |
| Provider payment ID | Separate from internal APRO payment identity |
| Identity resolution | Narrow persistence-level mapping/query |
| Current payment state | Existing Phase 1 state engine |
| Event ordering | Delivery order not trusted |
| Stale event | Preserve history, prevent unsafe current-state regression |
| Unsupported authenticated event | Persist raw evidence, 2xx, no canonical/state mutation |
| Unknown provider payment | Do not fabricate identity; 2xx unresolved classification |
| Malformed/untrusted input | Reject 4xx |
| Transaction scope | One short operation-scoped transaction |
| AI in pipeline | Prohibited |
| Recovery workflow | Prohibited |
| Outbound money movement | Prohibited |
| Live credentials | Not required for Phase 3 closure |
| Database | Existing PostgreSQL Phase 2 infrastructure |
| Migration changes | Only minimum required for provider payment identity resolution |

---

# 50. Architecture Lead Review Questions

Before this specification is locked, the Architecture Leads should confirm:

1. Is the supported Phase 3 event set exactly:
   ```text
   payment.failed
   payment.authorized
   payment.captured
   ```
2. Is the stale-event policy correct:
   ```text
   preserve historical event
   +
   never regress current state
   +
   acknowledge valid stale events with 2xx
   ```
3. Is the preferred provider payment identity mechanism acceptable:
   ```text
   persistence-level provider_payment_id
   +
   UNIQUE(provider, provider_payment_id)
   ```
4. Is authenticated-but-unsupported event handling acceptable:
   ```text
   raw evidence
   +
   no canonical event
   +
   no state mutation
   +
   HTTP 2xx
   ```
5. Is unknown provider payment handling acceptable:
   ```text
   do not fabricate
   +
   retain raw evidence
   +
   HTTP 2xx unresolved
   ```
6. Is `event_timestamp = top-level webhook created_at` approved?
7. Is the proposed canonical response classification contract acceptable?

The implementation must not begin until the Architecture Leads resolve any open questions that materially affect these behaviors.

---

# 51. Final Phase Boundary

At the end of Phase 3, APRO should be able to prove:

```text
Razorpay webhook
      ↓
authentic?
      ↓
yes
      ↓
new event?
      ↓
yes
      ↓
supported payment event?
      ↓
yes
      ↓
normalize
      ↓
canonical PaymentEvent
      ↓
resolve internal Payment
      ↓
apply safe state transition
      ↓
persist
      ↓
acknowledge
```

And for the critical success race:

```text
payment.failed
      ↓
customer retries externally
      ↓
payment.captured
      ↓
APRO receives captured event
      ↓
current payment becomes CAPTURED
      ↓
a late failed event cannot regress it
```

That is the complete Phase 3 capability.

Everything after that belongs to later phases.

---

# 52. Final Instruction

This document is the **Phase 3 architecture contract**.

It defines:

```text
WHAT Phase 3 must be
WHAT Phase 3 must guarantee
WHAT Phase 3 must not become
```

Once locked by the Architecture Leads, it becomes the sole Phase 3 implementation authority within the broader APRO authority hierarchy.

The next artifact after Architecture Lead approval is **one implementation prompt** instructing Antigravity to read this file, implement the entire Phase 3, test it, report it, and stop.

No separate implementation-plan document is required.
