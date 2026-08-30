# APRO — Phase 4 Recovery Case Orchestration Specification

**Project:** Adaptive Payment Recovery Orchestrator (APRO)  
**Track:** Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery  
**Phase:** 4 — Recovery Case Orchestration  
**Architecture Leads:** User + GPT  
**Software Engineering / Coding Lead:** Antigravity  
**Status:** Architecture Specification — Ready for Implementation  
**Version:** 1.0  
**Prepared:** 29 August 2026

---

# 1. Purpose

Phase 4 connects the trusted payment-event pipeline established in Phase 3 to APRO's `RecoveryCase` workflow.

The phase establishes a deterministic orchestration boundary that answers:

> When a trusted payment event indicates that recovery may be required, should APRO create or reuse a recovery case, what lifecycle state should that case occupy, and how should the case remain safe when the payment state changes?

Phase 4 is the bridge between:

```text
Phase 3
Trusted PaymentEvent + current Payment state
                    ↓
             Phase 4
       Recovery Case Orchestration
                    ↓
Phase 5+ / 7+ / 8+ / 9+ / 10+ / 11+
Simulation, intelligence, decisions, policy, execution
```

The objective is to establish the **case-management spine**, not to implement recovery intelligence or external recovery actions.

---

# 2. Authority and Governance

Phase 4 remains subordinate to the established APRO authority hierarchy:

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/PRODUCT_SPECIFICATION.md`
3. `docs/TECHNICAL_ARCHITECTURE.md`
4. `docs/DOMAIN_AND_DATA_MODEL.md`
5. `docs/AI_ML_SPECIFICATION.md`
6. `docs/POLICY_AND_SAFETY_SPECIFICATION.md`
7. `docs/SIMULATION_AND_EVALUATION_SPECIFICATION.md`
8. `docs/IMPLEMENTATION_MASTER_PLAN.md`
9. This Phase 4 specification

The 19-phase Implementation Master Plan is the authoritative phase sequence. The current sequence places Phase 4 immediately after the completed Phase 3 Canonical Event Pipeline and before the Simulation Engine. The master plan defines Phase 4 as: case creation, active-case detection, case lifecycle, diagnosis/evaluation placeholders, case transitions, and audit events; it explicitly prohibits real recovery action execution in this phase.

If implementation exposes a conflict with a higher-level document, Antigravity must:

```text
STOP
→ identify the exact conflict
→ provide evidence
→ report to Architecture Leads
→ wait for a decision
```

Antigravity must not independently redesign APRO.

---

# 3. Locked Starting Point

The following phases are formally closed and must be treated as authoritative:

```text
Phase 0 — Engineering Foundation                 CLOSED
Razorpay Webhook Validation Milestone             CLOSED
Phase 1 — Core Domain & State Machines            CLOSED
Phase 2 — Persistence & Database                   CLOSED
Phase 3 — Canonical Event Pipeline                 CLOSED
```

Phase 4 MUST reuse the existing domain and persistence layers rather than create parallel models or storage systems.

---

# 4. Existing Contracts Phase 4 Must Reuse

## 4.1 RecoveryCase domain entity

The existing `RecoveryCase` domain contract is authoritative.

Its fields are:

```text
case_id: str
payment_id: str
customer_id: str
status: RecoveryCaseStatus
opened_at: datetime
updated_at: datetime
closed_at: datetime | None
recovery_amount: int | None
current_attempt_count: int
stop_reason: str | None
escalation_reason: str | None
```

Phase 4 MUST NOT add a second case representation.

## 4.2 RecoveryCase statuses

The authoritative vocabulary is:

```text
NEW
DIAGNOSING
EVALUATING
DECISION_PENDING
POLICY_CHECK
ACTION_APPROVED
EXECUTING
OBSERVING
RECOVERED
STOPPED
ESCALATED
```

The domain state machine already defines the legal lifecycle transitions. Phase 4 must call that state machine instead of duplicating transition rules.

## 4.3 Existing persistence

Phase 2 already provides:

- PostgreSQL persistence
- SQLAlchemy asynchronous ORM
- repositories
- Unit of Work transaction boundaries
- a `recovery_cases` table
- indexes on `payment_id`, `customer_id`, and `status`
- repositories for `RecoveryCase` and `AuditEvent`

Phase 4 MUST use these existing capabilities.

---

# 5. Phase 4 Objective

Phase 4 must establish this deterministic path:

```text
Trusted Canonical PaymentEvent
          ↓
Recovery Case Eligibility Check
          ↓
Active Case Lookup
          ↓
Create / Reuse / Safely Terminate Case
          ↓
RecoveryCase State
          ↓
Audit Event
```

The phase must provide a stable interface for later intelligence phases to operate on a recovery case.

---

# 6. Phase 4 Core Business Rules

## 6.1 A recovery case represents a recovery workflow, not a payment

A `Payment` remains the source of truth for current payment state.

A `RecoveryCase` represents the separate workflow state around the recovery process.

Therefore:

```text
Payment.status != RecoveryCase.status
```

and the two state machines must not be merged.

## 6.2 Only trusted canonical events can affect RecoveryCases

Phase 4 operates on `PaymentEvent` records produced by the Phase 3 canonical pipeline.

Raw unverified webhook payloads MUST NOT create recovery cases.

## 6.3 `payment.failed` is the primary case-opening trigger

A newly accepted canonical `payment.failed` event for a known payment is a qualifying case-opening event.

The resulting behavior is:

```text
payment.failed
      ↓
resolve Payment
      ↓
check active RecoveryCase
      ↓
if none → create RecoveryCase(status=NEW)
if active → reuse active case
```

## 6.4 Duplicate webhook delivery MUST NOT create a second active case

Repeated delivery of the same provider event, including concurrent delivery, must remain idempotent at the case layer.

The invariant is:

```text
For one payment:
0 or 1 active RecoveryCase
```

A terminal historical case may coexist with a newer case only when a later qualifying failure represents a distinct recovery episode and the previous case is already terminal.

## 6.5 Active case detection

For Phase 4, these statuses are considered **active**:

```text
NEW
DIAGNOSING
EVALUATING
DECISION_PENDING
POLICY_CHECK
ACTION_APPROVED
EXECUTING
OBSERVING
```

These statuses are terminal:

```text
RECOVERED
STOPPED
ESCALATED
```

The orchestrator MUST never create a second active case for the same payment.

## 6.6 Terminal cases remain historical

A terminal `RecoveryCase` is not reopened in place.

If a new qualifying failure occurs after a previous case is terminal and the payment is eligible for another recovery episode, Phase 4 may create a **new case** with a new `case_id`, preserving the historical terminal case.

This keeps each recovery episode independently auditable.

## 6.7 Attempt count semantics

`current_attempt_count` represents actual recovery attempts, not webhook deliveries and not case creation events.

Therefore Phase 4 MUST NOT increment `current_attempt_count` merely because a `payment.failed` event is received.

Execution attempts belong to later execution phases.

## 6.8 Recovery amount semantics

When a case is created from a known payment, `recovery_amount` should initially represent the payment amount that is currently at risk.

It is an informational case field at this stage and MUST NOT be interpreted as recovered revenue.

No recovered amount is recorded by Phase 4.

---

# 7. Case Creation Contract

When a qualifying `payment.failed` event is processed and no active case exists, Phase 4 must create:

```text
RecoveryCase(
    case_id = new unique identifier,
    payment_id = resolved payment.payment_id,
    customer_id = resolved payment.customer_id,
    status = NEW,
    opened_at = orchestration timestamp,
    updated_at = orchestration timestamp,
    closed_at = None,
    recovery_amount = payment.amount,
    current_attempt_count = 0,
    stop_reason = None,
    escalation_reason = None,
)
```

The creation operation must be deterministic with respect to the selected payment and active-case rule, while the generated `case_id` remains unique.

The created case must reference the existing internal `payment_id` and `customer_id` rather than provider identifiers.

---

# 8. Case Eligibility Rules

Phase 4 must evaluate case eligibility using current persisted payment state and canonical event context.

## 8.1 Eligible opening condition

A payment is eligible for case creation when all are true:

```text
canonical event is payment.failed
AND payment is known
AND current payment state is not CAPTURED
AND no active RecoveryCase exists
```

## 8.2 Captured payment safety

A `CAPTURED` payment MUST never obtain a new active recovery case.

If a failed event is received after the payment has already reached `CAPTURED`, the payment remains governed by the Phase 3 captured-payment safety rule and no recovery case may be opened for that event.

## 8.3 Unresolved payment

If the Phase 3 pipeline cannot resolve the provider payment to an internal `Payment`, Phase 4 must not invent a case.

The unresolved event remains outside the case domain until identity resolution succeeds through an approved upstream process.

---

# 9. Payment-State / Recovery-Case Synchronization

Phase 4 must account for the fact that payment state can change while a recovery case is active.

## 9.1 Captured payment closes the recovery need

When a canonical `payment.captured` event makes the payment state `CAPTURED`, any active RecoveryCase for that payment must be safely transitioned to:

```text
OBSERVING → RECOVERED
```

when the case is already in `OBSERVING`, or to a safe terminal `STOPPED` path when the current case state cannot legally transition to `RECOVERED` under the domain state machine.

The actual implementation must use only legal domain transitions and must not bypass the state machine.

The preferred semantic outcome is:

```text
payment captured
      ↓
recovery is no longer required
      ↓
case becomes terminal
      ↓
no action execution
```

The case must record the terminal reason through its appropriate terminal field and an `AuditEvent`.

## 9.2 No post-capture recovery execution

Once the payment is captured, Phase 4 must not create or approve recovery actions and must not move the case toward execution.

---

# 10. Orchestration Service Boundary

Phase 4 must introduce a dedicated application/service boundary for recovery-case orchestration.

The exact class/module name may be chosen by Antigravity as an implementation detail, but its responsibility must be equivalent to:

```text
RecoveryCaseOrchestrator
```

The orchestrator owns:

- case eligibility evaluation
- active-case lookup
- case creation
- reuse of an active case
- safe case termination when payment state makes recovery unnecessary
- case lifecycle transition requests
- audit-event creation for case lifecycle changes
- deterministic placeholder interfaces for later diagnosis/evaluation capabilities

It must NOT own:

- ML inference
- Gemini calls
- action selection
- expected recovery value calculations
- policy authorization
- external execution
- Razorpay outbound API calls
- customer outreach

---

# 11. Integration with the Phase 3 Pipeline

Phase 4 must integrate with the Phase 3 canonical event pipeline rather than create a parallel webhook path.

The intended application flow is:

```text
POST /webhooks/razorpay
        ↓
Phase 3 verification
        ↓
canonical PaymentEvent
        ↓
current Payment state
        ↓
Phase 4 RecoveryCaseOrchestrator
        ↓
RecoveryCase + AuditEvent
        ↓
transaction commit
```

For qualifying events, the canonical event/state update and case orchestration SHOULD occur inside one Unit of Work transaction so that the following are committed atomically:

```text
RawEvent
PaymentEvent
Payment state change
RecoveryCase change
AuditEvent(s)
```

The purpose is to avoid a state where the webhook is acknowledged as successfully processed while the corresponding recovery case silently fails to exist.

If the case-orchestration portion fails unexpectedly, the transaction must fail rather than silently degrade into a payment-event-only workflow.

This follows the same non-degradation principle already established at the Phase 3 application boundary.

---

# 12. Idempotency and Concurrency Requirements

Phase 4 must be safe under both duplicate and concurrent event delivery.

## 12.1 Duplicate active-case creation

If two workers concurrently process qualifying failed events for the same payment:

```text
Worker A → active-case lookup → none
Worker B → active-case lookup → none
```

the system must still end with:

```text
exactly 1 active RecoveryCase
```

The implementation must combine application-level detection with database transaction/constraint protection rather than rely on an in-memory set.

## 12.2 Required database protection

The implementation must use PostgreSQL transaction semantics and the existing repository/Unit of Work infrastructure to make case creation race-safe.

A viable implementation may use:

- row locking on the payment or case lookup path;
- a database-backed uniqueness strategy for one active case per payment;
- a transactional create-or-reuse pattern;
- or a combination of these.

Antigravity must choose the smallest implementation that satisfies the invariant and must provide evidence with a real PostgreSQL concurrency test.

## 12.3 Do not create a parallel idempotency store

Phase 4 must not introduce an in-memory active-case registry or a second database solely for orchestration idempotency.

---

# 13. RecoveryCase Lifecycle Authority

The Phase 1 domain state machine remains the only authority for legal `RecoveryCase` transitions.

Phase 4 must call the existing transition engine rather than duplicate the transition matrix in orchestration code.

The existing legal lifecycle is:

```text
NEW
  ↓
DIAGNOSING
  ↓
EVALUATING
  ↓
DECISION_PENDING
  ↓
POLICY_CHECK
  ↓
ACTION_APPROVED
  ↓
EXECUTING
  ↓
OBSERVING
  ↓
RECOVERED
```

Safe terminal branches include:

```text
NEW          → STOPPED / ESCALATED
DIAGNOSING   → STOPPED / ESCALATED
EVALUATING   → STOPPED / ESCALATED
DECISION_PENDING → STOPPED / ESCALATED
POLICY_CHECK → STOPPED / ESCALATED
ACTION_APPROVED → STOPPED / ESCALATED
EXECUTING    → STOPPED / ESCALATED
OBSERVING    → STOPPED / ESCALATED / RECOVERED
```

Terminal states:

```text
RECOVERED
STOPPED
ESCALATED
```

must remain locked after entry.

Phase 4 MUST NOT bypass the state machine to directly write an illegal lifecycle state.

---

# 14. What Phase 4 May Automatically Advance

To keep Phase 4 bounded, the automatic orchestration triggered by a failed payment is limited to case creation and safe case-state handling.

The default automatic behavior is:

```text
payment.failed
      ↓
create/reuse RecoveryCase
      ↓
RecoveryCase = NEW
```

Phase 4 may expose controlled orchestration methods for:

```text
NEW → DIAGNOSING
DIAGNOSING → EVALUATING
EVALUATING → DECISION_PENDING
```

but these methods must use placeholder providers rather than AI intelligence.

The phase must NOT automatically transition a case into:

```text
POLICY_CHECK
ACTION_APPROVED
EXECUTING
```

as a side effect of webhook ingestion.

Those states depend on later intelligence, economic decisioning, policy, and execution phases.

---

# 15. Diagnosis Placeholder Boundary

Phase 4 must define a clean placeholder boundary for future diagnosis intelligence.

Required conceptual interface:

```text
DiagnosisProvider
    ↓
Diagnosis result or explicit placeholder result
```

The Phase 4 placeholder implementation must be:

- deterministic;
- local;
- AI-free;
- side-effect bounded;
- explicitly identifiable as a placeholder;
- incapable of making an execution decision.

A placeholder MUST NOT pretend to be a trained model.

The preferred Phase 4 placeholder semantics are:

```text
category = UNKNOWN
confidence = 0.0
model_name = PHASE4_PLACEHOLDER
model_version = 1.0
```

if a persisted `Diagnosis` record is required by the orchestration flow.

If the implementation can keep the placeholder entirely behind a service interface without persisting a fake intelligence record, that is preferred. No synthetic probability should be represented as production intelligence.

---

# 16. Evaluation Placeholder Boundary

Phase 4 must similarly provide an explicit future-facing boundary for recovery-action evaluation.

Required conceptual interface:

```text
RecoveryEvaluationProvider
    ↓
Action evaluation result or explicit placeholder result
```

The placeholder implementation must not claim that an action will recover money.

It must not invoke:

- Gemini;
- an ML model;
- a policy engine;
- a Razorpay API;
- an executor.

Where an `ActionEvaluation` entity is persisted during Phase 4, the record must be unmistakably marked as a placeholder and later intelligence phases must not mistake it for a real model prediction.

---

# 17. Audit Event Requirements

Phase 4 must use the existing immutable `AuditEvent` contract.

At minimum, the following lifecycle events must be auditable:

```text
RECOVERY_CASE_CREATED
RECOVERY_CASE_REUSED
RECOVERY_CASE_TRANSITIONED
RECOVERY_CASE_STOPPED
RECOVERY_CASE_RECOVERED
RECOVERY_CASE_ESCALATED
RECOVERY_CASE_BLOCKED
```

Additional internal orchestration events may be added when useful, but the event vocabulary must remain understandable and stable.

Each Phase 4 audit event must include:

```text
case_id
case-related event type
actor = SYSTEM
UTC timestamp
structured payload
correlation_id when available
```

The audit payload should capture the minimum information needed to reconstruct why the orchestration decision occurred, for example:

```text
trigger event id
payment id
previous case status
new case status
reason
```

Phase 4 must not log secrets, credentials, raw request signatures, or unnecessary sensitive data.

---

# 18. Transaction Boundaries

Recovery Case creation and transitions are business-state mutations and must occur inside an explicit Unit of Work.

Expected transaction properties:

```text
BEGIN
  ↓
load payment/current state
  ↓
load active case
  ↓
create/reuse/transition case
  ↓
write audit event(s)
  ↓
COMMIT
```

Unexpected exceptions must roll back the transaction.

No partial case state may be committed after an orchestration failure.

The existing `UnitOfWork` implementation must remain the transaction boundary; Phase 4 must not create a second transaction manager.

---

# 19. Recovery Case Repository Requirements

The existing `RecoveryCaseRepository` must be extended only as required to support Phase 4 behavior.

At minimum, the repository layer must support these logical operations:

```text
get_by_id(case_id)

find_active_by_payment_id(payment_id)

list_by_payment_id(payment_id)

save(case)

update(case)
```

The exact method names are implementation details.

`find_active_by_payment_id` must use the authoritative active-state set rather than assuming that the latest case is always active.

The repository must not embed AI, policy, or execution logic.

---

# 20. Case Creation / Reuse Decision Table

| Situation | Required Phase 4 behavior |
|---|---|
| `payment.failed`, known payment, no active case | Create `RecoveryCase(NEW)` |
| `payment.failed`, known payment, active case exists | Reuse active case; do not create another |
| Duplicate delivery of same event | No second case; audit/reuse semantics only |
| Concurrent qualifying failures for same payment | Exactly one active case |
| Known payment is `CAPTURED` | Do not create/reopen active case |
| Provider payment cannot be resolved | Do not invent a case |
| Previous case is terminal, new qualifying failure, payment not captured | New recovery episode may create a new case |
| `payment.captured` while case is active | Safely terminate recovery need using legal case transition; no execution |
| Unsupported event | No case action |
| Invalid/malformed/unauthenticated webhook | No case action |

---

# 21. Failure Handling

Phase 4 must distinguish expected business outcomes from unexpected engineering failures.

## Expected outcomes

Examples:

```text
active case already exists
payment already captured
unresolved payment identity
unsupported event
```

These should produce deterministic, auditable outcomes and must not crash the service unnecessarily.

## Unexpected failures

Examples:

```text
database failure
transaction failure
repository failure
invalid internal state
unexpected serialization failure
```

These must not be silently swallowed.

The system should fail the transaction and surface the error through the existing application error boundary.

There must be no silent fallback to transient in-memory case state.

---

# 22. Non-Goals / Explicit Phase Boundaries

Phase 4 MUST NOT implement or activate:

### Intelligence

- Gemini SDK integration
- LLM agents
- trained diagnosis models
- recovery probability models
- action optimization models
- model calibration
- model selection

These belong to later intelligence phases.

### Economic decisioning

- expected recovery value calculation
- action ranking
- cost optimization
- automated action selection

These belong to Phase 9.

### Policy / safety engine runtime

- confidence thresholds
- retry budgets
- high-value approval rules
- model-failure policy fallback
- authorization of actions

These belong to Phase 10.

### Execution

- retry APIs
- Payment Link creation
- outreach dispatch
- Razorpay outbound payment operations
- automatic customer messaging
- external financial execution

These belong to Phases 11–12.

### Outcomes

- recovery amount realized
- execution outcome processing
- adaptive re-evaluation based on execution result

These belong to Phase 13.

### Evaluation / dashboard

- 1,000+ case benchmark generation
- benchmark scoring
- reviewer dashboard

These belong to Phases 5–6 and 15–16.

---

# 23. Security and Safety Constraints

Phase 4 is a workflow-state phase and must remain non-executing.

The following invariants are mandatory:

```text
No active RecoveryCase for a CAPTURED payment
No duplicate active RecoveryCase for one payment
No case created from unauthenticated input
No case created from malformed input
No recovery action execution
No external money movement
No direct Razorpay outbound action
No AI authority in case creation
No silent failure or in-memory degradation
```

A case is a planning/workflow object, not permission to execute a recovery action.

---

# 24. Correlation and Traceability

Where a Phase 3 event already has a correlation/event identifier, Phase 4 should propagate it into `AuditEvent.correlation_id`.

The case should remain traceable through:

```text
provider event id
      ↓
raw event
      ↓
canonical PaymentEvent
      ↓
payment_id
      ↓
case_id
      ↓
AuditEvent
```

Phase 4 must not invent a second identity chain.

---

# 25. Required Automated Test Coverage

The implementation is not complete without tests covering at least the following.

## Case creation

1. Failed payment creates exactly one `RecoveryCase`.
2. Created case has status `NEW`.
3. Case points to the correct internal `payment_id` and `customer_id`.
4. `recovery_amount` equals the payment amount at case creation.
5. `current_attempt_count` starts at `0`.

## Active-case detection

6. Existing active case is reused.
7. No second active case is created.
8. Terminal cases are not treated as active.
9. A new recovery episode can create a new case after a prior terminal case when payment remains eligible.

## Payment safety

10. Captured payment cannot create a recovery case.
11. Active recovery case is safely terminated when payment becomes captured.
12. No recovery action state is created or executed by Phase 4.

## Lifecycle

13. Legal RecoveryCase transitions use the existing domain state machine.
14. Illegal transitions are rejected.
15. Terminal states remain terminal.
16. Placeholder diagnosis boundary is deterministic and AI-free.
17. Placeholder evaluation boundary is deterministic and AI-free.

## Idempotency / concurrency

18. Sequential duplicate event delivery does not create a second active case.
19. Concurrent duplicate delivery against PostgreSQL results in exactly one active case.
20. Concurrent qualifying failures for the same payment do not corrupt case state.

## Audit

21. Case creation emits an audit event.
22. Case reuse is auditable.
23. Case transitions are auditable.
24. Captured-payment termination is auditable.

## Transaction behavior

25. Unexpected orchestration error rolls back case and audit changes.
26. No silent fallback occurs when persistence is unavailable.

All tests must be deterministic and must not rely on live money movement.

---

# 26. PostgreSQL Acceptance Requirements

At least one real PostgreSQL integration test must prove the active-case uniqueness invariant under concurrency.

The acceptance test must use:

```text
PostgreSQL 16
127.0.0.1:5432
apro_test_db
```

or the repository's approved equivalent acceptance configuration.

The concurrency test must use independent database sessions/connections and must demonstrate:

```text
multiple concurrent workers
        ↓
case lookup/create race
        ↓
exactly one active RecoveryCase
        ↓
no duplicate active case
        ↓
valid persisted state
```

A mocked repository or mocked orchestrator is insufficient proof of the database race condition.

---

# 27. Integration Acceptance Flow

The preferred end-to-end behavior after Phase 4 is:

```text
Razorpay payment.failed webhook
            ↓
Phase 3 verification
            ↓
canonical PaymentEvent
            ↓
Payment state = FAILED
            ↓
Phase 4 eligibility check
            ↓
RecoveryCase created
            ↓
RecoveryCase.status = NEW
            ↓
AuditEvent persisted
```

A second identical delivery must result in:

```text
same event
   ↓
DUPLICATE
   ↓
no second active case
```

A later valid capture must result in:

```text
payment.captured
      ↓
Payment.status = CAPTURED
      ↓
active recovery need terminated safely
      ↓
no recovery execution
```

---

# 28. Manual Acceptance Demonstration

Before Phase 4 is considered complete, the architecture leads should be able to manually demonstrate at least:

### Scenario A — Failed payment opens a case

```text
payment.failed webhook
        ↓
Payment becomes FAILED
        ↓
RecoveryCase appears
        ↓
case status = NEW
        ↓
audit event exists
```

### Scenario B — Duplicate failure does not duplicate the case

```text
same webhook again
        ↓
DUPLICATE
        ↓
active case count remains 1
```

### Scenario C — Payment capture makes recovery unnecessary

```text
payment.captured webhook
        ↓
Payment becomes CAPTURED
        ↓
active recovery case safely terminates
        ↓
no recovery action executed
```

### Scenario D — Two concurrent failures produce one active case

```text
Worker A ─┐
          ├→ same payment
Worker B ─┘
          ↓
exactly one active RecoveryCase
```

The final manual run must inspect the actual PostgreSQL state, not only HTTP responses.

---

# 29. Observability Requirements

At minimum, application logs for Phase 4 should make these events understandable:

```text
case created
case reused
case transition
case stopped/recovered/escalated
case creation blocked
unexpected orchestration failure
```

Logs should include stable identifiers where available:

```text
case_id
payment_id
event_id/correlation_id
```

Do not log secrets or raw webhook signatures.

---

# 30. Definition of Done

Phase 4 is complete only when all of the following are true:

```text
Implementation
    +
Tests
    +
Acceptance Criteria
    +
Documentation
    +
Evidence
```

Specifically:

1. `payment.failed` can create a RecoveryCase.
2. Active-case detection is database-backed and concurrency-safe.
3. Duplicate delivery does not create duplicate active cases.
4. Payment/case safety is maintained when payment becomes captured.
5. RecoveryCase transitions use the authoritative Phase 1 state machine.
6. Diagnosis/evaluation boundaries exist without introducing real AI.
7. Case lifecycle activity produces immutable audit records.
8. Unexpected persistence failures do not silently degrade.
9. PostgreSQL concurrency acceptance passes.
10. The real HTTP-to-Phase-3-to-Phase-4 path is tested.
11. No recovery action executes.
12. No Phase 5+ intelligence or execution architecture is prematurely implemented.

---

# 31. Phase 4 Acceptance Gate

Architecture Leads will evaluate the implementation against these gates:

```text
G1 — Case Creation                         PASS / FAIL
G2 — Active Case Detection                 PASS / FAIL
G3 — Idempotency                           PASS / FAIL
G4 — PostgreSQL Concurrency                PASS / FAIL
G5 — Payment/Captured Safety               PASS / FAIL
G6 — Lifecycle State-Machine Integrity     PASS / FAIL
G7 — Placeholder Boundaries                PASS / FAIL
G8 — Audit Trail                           PASS / FAIL
G9 — Transactional Integrity               PASS / FAIL
G10 — Real HTTP Integration                PASS / FAIL
G11 — Non-Execution Boundary               PASS / FAIL
G12 — Regression / Quality Gates            PASS / FAIL
```

All critical gates must pass before Phase 4 can be closed.

---

# 32. Expected Repository Impact

The exact file layout is an implementation detail, but changes are expected to remain narrowly bounded to the existing APRO architecture.

Likely areas include:

```text
src/apro/
    recovery/                  ← orchestration/application service boundary
    persistence/repositories.py
    events/pipeline.py          ← Phase 3 integration point, if required
    domain/                     ← only if a proven contract gap exists

tests/
    recovery/
    events/
    persistence/

```

A migration should be created only if Phase 4 proves that the existing Phase 2 schema cannot enforce the required active-case invariant safely.

Antigravity must not add speculative tables, frameworks, queues, services, agents, or infrastructure.

---

# 33. Explicit Architectural Decisions for Phase 4

The following decisions are locked for implementation:

### Decision 1 — One active case per payment

At most one non-terminal RecoveryCase may exist for a payment at a time.

### Decision 2 — Terminal cases are historical

Terminal cases are never reopened in place.

### Decision 3 — `payment.failed` opens/reuses the case

The primary case-opening trigger is the trusted canonical `payment.failed` event.

### Decision 4 — Captured payment is recovery-ineligible

A captured payment must not have an active recovery workflow.

### Decision 5 — Domain state machine remains authoritative

No duplicate transition matrix is allowed in orchestration code.

### Decision 6 — No fake AI authority

Placeholder diagnosis/evaluation behavior must be explicitly marked as placeholder and must not be treated as a production prediction.

### Decision 7 — No execution

Phase 4 creates and orchestrates workflow state only. It does not execute a recovery action.

### Decision 8 — Transactional case consistency

Qualifying event/state/case/audit mutations should commit atomically inside the existing Unit of Work boundary.

### Decision 9 — Database-backed concurrency safety

The one-active-case invariant must survive concurrent PostgreSQL workers.

### Decision 10 — No silent degradation

If the configured persistence layer cannot support case orchestration, APRO must fail visibly rather than switch to transient in-memory case state.

---

# 34. Implementation Boundary Summary

```text
                    PHASE 4 OWNS

PaymentEvent ────────────────┐
                             ↓
                     Case Eligibility
                             ↓
                    Active Case Lookup
                             ↓
                 Create / Reuse / Transition
                             ↓
                         AuditEvent

                    PHASE 4 DOES NOT OWN

AI Diagnosis ────────────────→ Phase 7
Recovery Prediction ─────────→ Phase 8
Economic Decision ───────────→ Phase 9
Policy Gate ─────────────────→ Phase 10
Execution ───────────────────→ Phase 11
Razorpay Outbound ───────────→ Phase 12
Outcome Loop ────────────────→ Phase 13
```

The result of Phase 4 should be a durable, concurrency-safe recovery workflow object that later intelligence can operate on without needing to understand Razorpay webhook structure.

---

# 35. Architecture Approval Gate

This document is the authoritative Phase 4 architecture specification.

It is a specification, not authorization to implement.

Before coding begins, Architecture Leads must confirm that this document is the locked Phase 4 contract.

Once approved:

```text
Architecture Leads
      ↓
Save / lock Phase 4 specification
      ↓
Issue implementation prompt to Antigravity
      ↓
Antigravity reads this specification
      ↓
Implements Phase 4
      ↓
Implementation report
      ↓
Architecture review
      ↓
Automated + PostgreSQL + manual acceptance
      ↓
Staging audit
      ↓
Commit
      ↓
Phase 4 CLOSED
```

No implementation-plan `.md` file is required or authorized for this workflow.

---

# 36. Final Phase 4 Statement

> **Phase 4 establishes the durable RecoveryCase orchestration spine that turns trusted payment failures into one auditable, concurrency-safe recovery workflow per payment—without yet deciding or executing any recovery action.**
